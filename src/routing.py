"""Résolution du service de destination à partir de la demande de l'appelant."""

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Service:
    key: str
    display_name: str
    contact_name: str
    contact_email: str
    keywords: list[str]


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in text if not unicodedata.combining(char))


def load_services(path: Path) -> tuple[str, dict[str, Service]]:
    """Retourne (nom de l'entreprise, {clé: Service}) depuis routing.yaml."""
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    services = {}
    for key, raw in (data.get("services") or {}).items():
        services[key] = Service(
            key=key,
            display_name=raw.get("display_name", key),
            contact_name=raw.get("contact_name", "Le responsable"),
            contact_email=raw.get("contact_email", ""),
            keywords=[str(k) for k in raw.get("keywords", [])],
        )
    return data.get("entreprise", "Notre entreprise"), services


def resolve_service(text: str, services: dict[str, Service]) -> Service | None:
    """Trouve le service dont un mot-clé apparaît dans la demande de l'appelant.
    Le mot-clé le plus long l'emporte, pour départager les cas ambigus."""
    normalized = _normalize(text)
    best: tuple[int, Service | None] = (0, None)
    for service in services.values():
        for keyword in [*service.keywords, service.key, service.display_name]:
            word = _normalize(keyword)
            if not word or not re.search(rf"(^|\W){re.escape(word)}(\W|$)", normalized):
                continue
            if len(word) > best[0] or (len(word) == best[0] and best[1] is None):
                best = (len(word), service)
    return best[1]


def find_service(key_or_name: str, services: dict[str, Service]) -> Service | None:
    """Retrouve un service par sa clé ou une partie de son nom affiché,
    au mot près (de sorte que « commercial » retrouve « Service commercial »)."""
    needle = _normalize(key_or_name)
    if not needle:
        return None
    for service in services.values():
        words = _normalize(service.key).split() + _normalize(service.display_name).split()
        if needle in _normalize(service.key) or any(
            needle in word
            or (len(word) >= 4 and needle.startswith(word))
            or word.startswith(needle)
            for word in words
        ):
            return service
    return None
