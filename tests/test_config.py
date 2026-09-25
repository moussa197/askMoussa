"""Tests de app/config.py. Aucune vraie clé : uniquement des valeurs factices via monkeypatch."""

import pytest

from app.config import ORIGINE_PORTFOLIO, charger_config, est_sur_render

# Toutes les variables lues par config.py.
VARIABLES = [
    "ANTHROPIC_API_KEY",
    "CLAUDE_MODEL",
    "CLAUDE_MAX_TOKENS",
    "MAX_QUESTION_LENGTH",
    "RATE_LIMIT_PAR_MINUTE",
    "RATE_LIMIT_PAR_JOUR",
    "PLAFOND_GLOBAL_JOUR",
    "CORS_ORIGINES_DEV",
    "XFF_POSITION",
    "RENDER",
]


@pytest.fixture(autouse=True)
def environnement_propre(monkeypatch):
    """Efface les variables (y compris celles venues du vrai .env) puis met une fausse clé."""
    for nom in VARIABLES:
        monkeypatch.delenv(nom, raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")


def test_valeurs_par_defaut():
    config = charger_config()
    assert config.anthropic_api_key == "test-key"
    assert config.claude_model == "claude-haiku-4-5"
    assert config.claude_max_tokens == 400
    assert config.max_question_length == 500
    assert config.rate_limit_par_minute == 10
    assert config.rate_limit_par_jour == 30
    assert config.plafond_global_jour == 300
    assert config.cors_origines == (ORIGINE_PORTFOLIO,)
    assert config.xff_position is None


def test_valeurs_personnalisees(monkeypatch):
    monkeypatch.setenv("CLAUDE_MODEL", "autre-modele")
    monkeypatch.setenv("CLAUDE_MAX_TOKENS", "200")
    monkeypatch.setenv("MAX_QUESTION_LENGTH", "300")
    monkeypatch.setenv("RATE_LIMIT_PAR_MINUTE", "5")
    monkeypatch.setenv("RATE_LIMIT_PAR_JOUR", "20")
    monkeypatch.setenv("PLAFOND_GLOBAL_JOUR", "100")
    config = charger_config()
    assert config.claude_model == "autre-modele"
    assert config.claude_max_tokens == 200
    assert config.max_question_length == 300
    assert config.rate_limit_par_minute == 5
    assert config.rate_limit_par_jour == 20
    assert config.plafond_global_jour == 100


def test_cle_absente(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        charger_config()


@pytest.mark.parametrize("valeur", ["", "   "])
def test_cle_vide(monkeypatch, valeur):
    monkeypatch.setenv("ANTHROPIC_API_KEY", valeur)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        charger_config()


@pytest.mark.parametrize("valeur", ["abc", "0", "-5", "1.5"])
def test_entier_invalide(monkeypatch, valeur):
    monkeypatch.setenv("RATE_LIMIT_PAR_JOUR", valeur)
    with pytest.raises(ValueError, match="RATE_LIMIT_PAR_JOUR"):
        charger_config()


def test_origines_de_dev(monkeypatch):
    # Espaces et éléments vides ignorés.
    monkeypatch.setenv("CORS_ORIGINES_DEV", " http://localhost:5500 ,, http://127.0.0.1:5500,")
    config = charger_config()
    assert config.cors_origines == (
        ORIGINE_PORTFOLIO,
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    )


@pytest.mark.parametrize("valeur", ["*", "http://localhost:5500,*", "https://*.github.io"])
def test_etoile_refusee(monkeypatch, valeur):
    monkeypatch.setenv("CORS_ORIGINES_DEV", valeur)
    with pytest.raises(ValueError, match=r"\*"):
        charger_config()


@pytest.mark.parametrize("valeur, attendu", [("", None), ("0", 0), ("-1", -1), ("-2", -2)])
def test_xff_position(monkeypatch, valeur, attendu):
    monkeypatch.setenv("XFF_POSITION", valeur)
    assert charger_config().xff_position == attendu


def test_xff_position_invalide(monkeypatch):
    monkeypatch.setenv("XFF_POSITION", "abc")
    with pytest.raises(ValueError, match="XFF_POSITION"):
        charger_config()


def test_detection_de_render(monkeypatch):
    assert est_sur_render() is False  # RENDER effacée par la fixture
    monkeypatch.setenv("RENDER", "true")
    assert est_sur_render() is True


def test_xff_position_obligatoire_sur_render(monkeypatch):
    # Render définit la variable RENDER : sans position, tous les visiteurs
    # partageraient l'IP du répartiteur de charge.
    monkeypatch.setenv("RENDER", "true")
    with pytest.raises(ValueError, match="XFF_POSITION doit être définie sur Render"):
        charger_config()


def test_xff_position_definie_sur_render(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("XFF_POSITION", "-1")
    assert charger_config().xff_position == -1


def test_cle_masquee_dans_repr(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "cle-secrete-123")
    assert "cle-secrete-123" not in repr(charger_config())
