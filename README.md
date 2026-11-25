# Agent téléphonique conversationnel

Agent vocal qui répond aux appels en français, oriente l'appelant vers le bon
service et, si personne n'est disponible, prend ses coordonnées et les envoie
par e-mail au responsable concerné.

Construit sur le [Voice Agents SDK de Mistral](https://docs.mistral.ai/studio/audio/voice-agents/)
(transcription temps réel → LLM → synthèse vocale, avec interruption et détection de tour de parole).

## Fonctionnement

1. L'appelant parle au micro ; sa voix est transcrite en temps réel (Voxtral).
2. Le modèle (`mistral-small-latest`) identifie le motif de l'appel.
3. Si le motif correspond à un service (`config/routing.yaml`), l'agent appelle
   `transfer_call` : la demande est enregistrée et transmise au service.
4. Sinon (ou si l'appelant préfère être rappelé), il recueille nom, téléphone,
   e-mail et motif, puis appelle `save_contact_details` : un e-mail récapitulatif
   est envoyé au responsable du service via SMTP.
5. Sans serveur SMTP configuré, les e-mails sont conservés dans `outbox/`
   (format `.eml`) — pratique pour tester sans compte e-mail.

## Structure

```
config/routing.yaml   services, mots-clés et e-mails des responsables
src/phone_agent.py    agent vocal : instructions, outils, session
src/routing.py        résolution du service à partir de la demande
src/emailer.py        envoi SMTP (avec repli local outbox/)
src/config.py         fichier .env et configuration SMTP
run.py                point d'entrée
```

## Installation

```bash
# PortAudio est nécessaire pour le micro (PyAudio)
sudo apt install libportaudio2 libportaudiocpp0 portaudio19-dev -y   # Debian/Ubuntu
# ou : brew install portaudio                                        # macOS

pip install "mistralai[voice-agents]" PyYAML
```

Puis copiez `.env.example` en `.env` et renseignez au minimum `MISTRAL_API_KEY`.
Ajoutez les variables SMTP (par exemple celles de Gmail avec un mot de passe
d'application : `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=465`) pour l'envoi réel des e-mails.

## Utilisation

```bash
python run.py check    # vérifie services, routing, SMTP et clé API
python run.py voice    # démarre une conversation vocale au micro
```

## Personnalisation

- **Services** : modifiez `config/routing.yaml` (clé, nom affiché, e-mail du
  responsable, mots-clés de détection). Redémarrez l'agent ensuite.
- **Voix** : changez `tts.voice_id` dans `src/phone_agent.py`
  (ex. `fr_marie_neutral`, `voice_592`…).
- **Instructions** : la formulation des questions et du protocole de prise de
  coordonnées se règle dans `build_instructions`.

## Vers la téléphonie réelle

Ce prototype tourne au micro et avec des outils côté client. Pour raccorder un
vrai numéro de téléphone :

- **Téléphonie SIP de Mistral** (clients entreprise) : l'agent enregistré via
  `client.audio.agents.create` répond directement au numéro ; les outils doivent
  alors être [côté serveur](https://docs.mistral.ai/studio/audio/voice-agents/telephony)
  (connecteurs et bibliothèques de documents du workspace).
- **Opérateur tiers (Twilio, Vonage…)** : ceux-ci transmettent l'audio de l'appel
  à votre application, qui alimente une session d'agent via
  [l'interface audio personnalisée](https://docs.mistral.ai/studio/audio/voice-agents/custom-audio)
  ou un pipeline STT/LLM/TTS assemblé à la main.

## Tests

```bash
python -m pytest tests/
```
