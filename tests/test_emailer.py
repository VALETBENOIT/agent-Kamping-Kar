import asyncio
import email
import email.parser

import pytest

from src.config import SMTPConfig
from src.emailer import send_contact_email
from src.routing import Service

SERVICE = Service(
    key="ventes",
    display_name="Service commercial",
    contact_name="L'équipe commerciale",
    contact_email="commercial@test.fr",
    keywords=[],
)

CONTACT = {
    "nom": "Jean Dupont",
    "telephone": "06 12 34 56 78",
    "email": "jean@exemple.fr",
    "motif": "Demande de devis pour trois licences.",
}


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    for name in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr("src.emailer.OUTBOX_DIR", tmp_path / "outbox")
    return SMTPConfig()


def parsed(tmp_path):
    messages = sorted((tmp_path / "outbox").glob("*.eml"))
    assert len(messages) == 1
    return email.parser.BytesParser().parsebytes(messages[0].read_bytes())


def test_no_smtp_queues_eml(cfg, tmp_path):
    result = asyncio.run(send_contact_email(cfg, SERVICE.contact_email, SERVICE, CONTACT))
    assert result["status"] == "queued"
    msg = parsed(tmp_path)
    assert msg["To"] == "commercial@test.fr"
    assert "[Service commercial]" in msg["Subject"]
    body = msg.get_payload(decode=True).decode()
    assert "Jean Dupont" in body
    assert "06 12 34 56 78" in body
    assert "Demande de devis" in body


def test_smtp_send(cfg, monkeypatch):
    cfg.host = "smtp.test.fr"
    cfg.port = 587
    cfg.user = "agent@test.fr"
    cfg.password = "secret"
    calls = {}

    def fake_send(config, msg):
        calls["to"] = msg["To"]
        calls["from"] = msg["From"]

    monkeypatch.setattr("src.emailer._smtp_send", fake_send)
    result = asyncio.run(send_contact_email(cfg, SERVICE.contact_email, SERVICE, CONTACT))
    assert result["status"] == "sent"
    assert calls["to"] == "commercial@test.fr"
    assert calls["from"] == "agent@test.fr"


def test_smtp_failure_keeps_message(cfg, tmp_path, monkeypatch):
    cfg.host = "smtp.test.fr"

    def broken_send(config, msg):
        raise ConnectionError("refusé")

    monkeypatch.setattr("src.emailer._smtp_send", broken_send)
    result = asyncio.run(send_contact_email(cfg, SERVICE.contact_email, SERVICE, CONTACT))
    assert result["status"] == "error"
    assert parsed(tmp_path)
