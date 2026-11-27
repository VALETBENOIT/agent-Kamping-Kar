"""Point d'entrée : `python run.py voice` pour parler à l'agent au micro."""

import argparse
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import ROUTING_FILE, SMTPConfig, load_dotenv
from src.routing import load_services


def check() -> int:
    company, services = load_services(ROUTING_FILE)
    print(f"Entreprise : {company}")
    print("Services configurés :")
    for service in services.values():
        print(f"  - {service.display_name} -> {service.contact_email}")
    cfg = SMTPConfig()
    if cfg.configured:
        print(f"SMTP : actif ({cfg.host}:{cfg.port})")
    else:
        print("SMTP : non configuré -> les messages seront enregistrés dans outbox/")
    if not os.environ.get("MISTRAL_API_KEY"):
        print("ATTENTION : MISTRAL_API_KEY n'est pas défini.")
        return 1
    print("MISTRAL_API_KEY : OK")
    return 0


def voice() -> int:
    from src.phone_agent import run_voice_agent

    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    asyncio.run(run_voice_agent())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent téléphonique vocal")
    parser.add_argument("command", choices=["voice", "check"], help="voice : démarrer l'agent ; check : vérifier la configuration")
    args = parser.parse_args()
    return check() if args.command == "check" else voice()


if __name__ == "__main__":
    raise SystemExit(main())
