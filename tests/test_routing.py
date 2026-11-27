import pytest

from src.routing import find_service, load_services, resolve_service


@pytest.fixture
def services(tmp_path):
    services = tmp_path / "routing.yaml"
    services.write_text(
        """
entreprise: "Test SARL"
services:
  ventes:
    display_name: "Service commercial"
    contact_name: "L'équipe commerciale"
    contact_email: "commercial@test.fr"
    keywords: [devis, prix, achat]
  support:
    display_name: "Support technique"
    contact_name: "L'équipe support"
    contact_email: "support@test.fr"
    keywords: [panne, réparation, bug]
""",
        encoding="utf-8",
    )
    return load_services(services)


def test_load_services(services):
    company, all_services = services
    assert company == "Test SARL"
    assert set(all_services) == {"ventes", "support"}
    assert all_services["ventes"].contact_email == "commercial@test.fr"


def test_resolve_by_keyword(services):
    _, all_services = services
    assert resolve_service("Je voudrais un devis pour trois licences", all_services) is all_services["ventes"]
    assert resolve_service("Mon imprimante est en panne", all_services) is all_services["support"]


def test_resolve_accent_insensitive(services):
    _, all_services = services
    assert resolve_service("probleme de reparation", all_services) is all_services["support"]


def test_resolve_unknown_returns_none(services):
    _, all_services = services
    assert resolve_service("bonjour", all_services) is None


def test_longest_keyword_wins(services):
    _, all_services = services
    all_services["support"].keywords.append("prix du devis")
    assert resolve_service("j'aurais besoin du prix du devis ajouté", all_services) is all_services["support"]


def test_find_service_by_key_or_name(services):
    _, all_services = services
    assert find_service("ventes", all_services) is all_services["ventes"]
    assert find_service("commerciale", all_services) is all_services["ventes"]
    assert find_service("inexistant", all_services) is None
