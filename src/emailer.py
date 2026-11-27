"""Envoi des coordonnées de l'appelant au responsable du bon service, par e-mail."""

import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate

from .config import OUTBOX_DIR, SMTPConfig

logger = logging.getLogger(__name__)


def build_message(cfg: SMTPConfig, recipient_email: str, service, contact: dict) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = cfg.sender or cfg.user or "agent-telephonique@local"
    msg["To"] = recipient_email
    msg["Date"] = formatdate(localtime=True)
    it = iter("\r\n ")
    msg["Subject"] = f"[{service.display_name}] Demande de {contact.get('nom', 'appelant inconnu')}"
    lines = [
        "Nouvel appel pris en charge par l'agent téléphonique.",
        "",
        f"Service concerné : {service.display_name}",
        f"Nom : {contact.get('nom', 'non communiqué')}",
        f"Téléphone : {contact.get('telephone', 'non communiqué')}",
        f"E-mail : {contact.get('email', 'non communiqué')}",
        "",
        "Motif de l'appel :",
        contact.get("motif", "non communiqué"),
        "",
        "Répondre directement à l'appelant.",
    ]
    msg.set_content("\n".join(lines))
    return msg


def _smtp_send(cfg: SMTPConfig, msg: EmailMessage) -> None:
    if cfg.port == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(cfg.host, cfg.port, context=context) as server:
            if cfg.user:
                server.login(cfg.user, cfg.password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(cfg.host, cfg.port, timeout=20) as server:
            server.starttls(context=ssl.create_default_context())
            if cfg.user:
                server.login(cfg.user, cfg.password)
            server.send_message(msg)


def _save_to_outbox(outbox_dir, msg: EmailMessage) -> str:
    outbox_dir.mkdir(parents=True, exist_ok=True)
    stamp = msg["Date"].replace(" ", "_").replace(":", "-").replace(",", "")
    recipient = msg["To"].replace("@", "_at_")
    path = outbox_dir / f"{stamp}_{recipient}.eml"
    path.write_bytes(bytes(msg))
    return str(path)


async def send_contact_email(cfg: SMTPConfig, recipient_email: str, service, contact: dict) -> dict:
    if not recipient_email:
        return {"status": "error", "detail": "Aucune adresse e-mail configurée pour ce service."}

    msg = build_message(cfg, recipient_email, service, contact)

    if not cfg.configured:
        path = _save_to_outbox(OUTBOX_DIR, msg)
        logger.info("SMTP non configuré : message enregistré dans %s", path)
        return {
            "status": "queued",
            "detail": f"SMTP non configuré, le message a été enregistré localement ({path}).",
        }

    try:
        await asyncio.to_thread(_smtp_send, cfg, msg)
    except Exception as exc:
        logger.exception("Échec de l'envoi SMTP")
        path = _save_to_outbox(OUTBOX_DIR, msg)
        return {"status": "error", "detail": f"Envoi impossible ({exc}) ; message conservé dans {path}."}

    return {"status": "sent", "detail": f"E-mail envoyé à {recipient_email}."}
