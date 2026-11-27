"""Agent téléphonique vocal : pipeline Mistral Voice Agents (STT -> LLM -> TTS)
avec outils d'orientation vers les services et de prise de coordonnées."""

import logging
import os

from mistralai.client import Mistral
from mistralai.extra.voice_agents import StaticToolFiller, function_tool

from .config import ROUTING_FILE, SMTPConfig
from .emailer import send_contact_email
from .routing import find_service, load_services, resolve_service

logger = logging.getLogger(__name__)


def build_instructions(company: str, services: dict) -> str:
    listing = "\n".join(f"- {s.display_name} (mot-clé : {s.key})" for s in services.values())
    return f"""Tu es l'agent téléphonique de {company}. Tu réponds aux appels des clients.

Ton rôle :
1. Salue brièvement l'appelant et demande le motif de son appel.
2. Si le motif correspond clairement à un service ci-dessous, annonce que tu le mets en relation et appelle l'outil transfer_call avec le service concerné.
3. Si le demandeur est absent ou indisponible, ou si l'appelant préfère être rappelé, propose de prendre ses coordonnées : demande UNE information à la fois (nom, puis téléphone, puis e-mail, puis motif), répète et fais confirmer chaque information, puis appelle save_contact_details.

Services disponibles :
{listing}

Règles :
- Réponds toujours en français, avec des phrases courtes (1 à 2 phrases maximum).
- N'appelle transfer_call que lorsque l'appelant a confirmé son motif.
- N'utilise jamais d'information que l'appelant n'a pas donnée.
- Si l'appelant souhaite parler à quelqu'un maintenant et que ce n'est pas possible, excuse-toi et propose la prise de coordonnées pour un rappel."""


def build_tools(cfg: SMTPConfig, services: dict):
    """Construit les outils côté client, avec le routage et la config e-mail liés."""

    @function_tool(filler=StaticToolFiller(text="Un instant, je vous mets en relation…"))
    async def transfer_call(service_key: str, motif: str) -> dict:
        """Met l'appelant en relation avec le service demandé.

        Args:
            service_key: clé ou nom du service (ex: ventes, support, facturation, rh, accueil).
            motif: résumé en une phrase du motif de l'appel.
        """
        service = find_service(service_key, services) or resolve_service(motif, services)
        if service is None:
            logger.info("Transfert refusé : service inconnu (%s)", service_key)
            return {
                "status": "unknown_service",
                "detail": "Service inconnu : propose plutôt de prendre les coordonnées de l'appelant.",
            }
        logger.info(
            "Transfert demandé vers %s (%s) — motif : %s",
            service.display_name,
            service.contact_email,
            motif,
        )
        return {
            "status": "transferred",
            "service": service.display_name,
            "responsable": service.contact_name,
            "detail": "La demande a été enregistrée et transmise au service. "
            "Annonce à l'appelant qu'il sera recontacté, et propose de prendre ses coordonnées si besoin.",
        }

    @function_tool(filler=StaticToolFiller(text="Je transmets vos coordonnées…"))
    async def save_contact_details(
        nom: str, telephone: str, service: str, motif: str, email: str = ""
    ) -> dict:
        """Enregistre les coordonnées de l'appelant et les envoie par e-mail au responsable du service.

        Args:
            nom: nom et prénom de l'appelant.
            telephone: numéro de téléphone pour le rappeler.
            service: service concerné (ex: ventes, support, facturation, rh).
            motif: raison de l'appel, en une ou deux phrases.
            email: adresse e-mail de l'appelant, s'il en donne une.
        """
        target = find_service(service, services) or resolve_service(f"{service} {motif}", services)
        if target is None:
            logger.info("Prise de coordonnées refusée : service inconnu (%s)", service)
            return {
                "status": "unknown_service",
                "detail": "Service inconnu : demande à l'appelant une précision sur sa demande.",
            }
        result = await send_contact_email(
            cfg,
            target.contact_email,
            target,
            {"nom": nom, "telephone": telephone, "email": email, "motif": motif},
        )
        logger.info("Coordonnées transmises à %s : %s", target.display_name, result)
        return {"status": result["status"], "detail": result["detail"]}

    @function_tool()
    def list_services() -> dict:
        """Liste les services disponibles pour orienter l'appelant."""
        return {"services": [f"{s.display_name} ({s.key})" for s in services.values()]}

    return [transfer_call, save_contact_details, list_services]


async def run_voice_agent() -> None:
    from mistralai.extra.voice_agents import DefaultAudioInterface

    company, services = load_services(ROUTING_FILE)
    cfg = SMTPConfig()
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    session = await client.audio.sessions.init(
        llm={"model": "mistral-small-latest"},
        stt={
            "model": "voxtral-mini-transcribe-realtime-3",
            "language": "fr",
            "context_bias": [s.display_name for s in services.values()],
        },
        tts={"voice_id": "fr_marie_neutral"},
        instructions=build_instructions(company, services),
        welcome_message=f"Bonjour, vous êtes à l'accueil de {company}. Comment puis-je vous aider ?",
        turn={"allow_interruptions": True},
        tools=build_tools(cfg, services),
    )

    session.on("transcript", lambda event: print(f"{event.role} : {event.content}"))
    session.on("unhandled_tool", lambda e: logger.warning("Outil non géré : %s", e.name))

    async with session:
        print("Agent prêt — parlez au micro (Ctrl+C pour arrêter).")
        await session.wait()
