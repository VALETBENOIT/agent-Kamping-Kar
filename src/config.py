"""Chargement de la configuration : variables d'environnement et fichier de routage."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ROUTING_FILE = Path(os.environ.get("ROUTING_FILE", PROJECT_ROOT / "config" / "routing.yaml"))
OUTBOX_DIR = Path(os.environ.get("OUTBOX_DIR", PROJECT_ROOT / "outbox"))


def load_dotenv(path: Path = PROJECT_ROOT / ".env") -> None:
    """Charge un fichier .env simple (CLÉ=VALEUR) sans dépendance externe."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


class SMTPConfig:
    """Paramètres d'envoi e-mail. Tous les champs sont optionnels : si le serveur
    n'est pas configuré, l'agent enregistre les messages dans outbox/."""

    def __init__(self) -> None:
        self.host = os.environ.get("SMTP_HOST", "")
        self.port = int(os.environ.get("SMTP_PORT", "587"))
        self.user = os.environ.get("SMTP_USER", "")
        self.password = os.environ.get("SMTP_PASSWORD", "")
        self.sender = os.environ.get("SMTP_FROM", self.user)

    @property
    def configured(self) -> bool:
        return bool(self.host)
