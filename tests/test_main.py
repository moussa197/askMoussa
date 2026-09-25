"""Tests de app/main.py avec le TestClient de FastAPI (aucun serveur, aucun réseau)."""

from dataclasses import replace
from unittest.mock import MagicMock

import anthropic
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import lire_origines_cors
from app.main import ajouter_cors, app, obtenir_config, obtenir_limiteur
from app.rate_limit import LimiteurRequetes
from tests.conftest import CONFIG_TEST, PROMPT_TEST

# Sans "with", le lifespan n'est pas lancé : pas besoin de clé ni de documents.
client = TestClient(app)


# --- /health ---


def test_health_repond_ok():
    reponse = client.get("/health")
    assert reponse.status_code == 200
    assert reponse.json() == {"status": "ok"}


def test_health_refuse_post():
    # Seule la méthode GET est déclarée : FastAPI renvoie 405 (méthode non autorisée).
    reponse = client.post("/health")
    assert reponse.status_code == 405


# --- /chat (faux client Claude, aucun appel à l'API) ---


def test_chat_renvoie_la_reponse(faux_client_claude):
    reponse = client.post("/chat", json={"question": "Quels projets ?"})
    assert reponse.status_code == 200
    assert reponse.json() == {"answer": "Réponse de test"}


def test_chat_transmet_la_question_et_le_prompt(faux_client_claude):
    client.post("/chat", json={"question": "Où étudie Moussa ?"})
    assert faux_client_claude.appels == [
        {"system": PROMPT_TEST, "question": "Où étudie Moussa ?"}
    ]


def test_chat_sans_question_refuse(faux_client_claude):
    reponse = client.post("/chat", json={})
    assert reponse.status_code == 422
    assert faux_client_claude.appels == []  # Claude n'a pas été appelé


# --- Longueur max et question vide (étape 8) ---


def test_question_trop_longue_refusee(faux_client_claude):
    reponse = client.post("/chat", json={"question": "a" * 501})
    assert reponse.status_code == 422
    assert faux_client_claude.appels == []  # Claude n'a pas été appelé


def test_question_de_500_caracteres_acceptee(faux_client_claude):
    reponse = client.post("/chat", json={"question": "a" * 500})
    assert reponse.status_code == 200


@pytest.mark.parametrize("question", ["", "   ", "\n\t "])
def test_question_vide_refusee(faux_client_claude, question):
    reponse = client.post("/chat", json={"question": question})
    assert reponse.status_code == 422
    assert faux_client_claude.appels == []


def test_espaces_autour_retires_avant_envoi(faux_client_claude):
    reponse = client.post("/chat", json={"question": "  Où étudie Moussa ?  "})
    assert reponse.status_code == 200
    assert faux_client_claude.appels[0]["question"] == "Où étudie Moussa ?"


def test_espaces_autour_non_comptes_dans_la_longueur(faux_client_claude):
    reponse = client.post("/chat", json={"question": "   " + "a" * 500 + "   "})
    assert reponse.status_code == 200


def test_limite_lue_dans_la_config(faux_client_claude):
    # Avec une limite de 10, 11 caractères sont refusés : la valeur vient bien de la config.
    app.dependency_overrides[obtenir_config] = lambda: replace(CONFIG_TEST, max_question_length=10)
    assert client.post("/chat", json={"question": "a" * 10}).status_code == 200
    assert client.post("/chat", json={"question": "a" * 11}).status_code == 422


# --- Rate limiting (étape 9) ---


def installer_limiteur(par_minute):
    """Remplace le limiteur de la fixture par un limiteur plus strict."""
    limiteur = LimiteurRequetes(par_minute=par_minute, par_jour=30, plafond_global=300)
    app.dependency_overrides[obtenir_limiteur] = lambda: limiteur


def test_trop_de_questions_renvoie_429(faux_client_claude):
    installer_limiteur(par_minute=2)
    assert client.post("/chat", json={"question": "Q1"}).status_code == 200
    assert client.post("/chat", json={"question": "Q2"}).status_code == 200

    reponse = client.post("/chat", json={"question": "Q3"})
    assert reponse.status_code == 429
    assert reponse.json() == {"detail": "Trop de questions. Réessayez un peu plus tard."}
    assert len(faux_client_claude.appels) == 2  # Claude n'a pas été appelé pour Q3


def test_question_invalide_ne_consomme_pas_de_quota(faux_client_claude):
    installer_limiteur(par_minute=1)
    assert client.post("/chat", json={"question": "   "}).status_code == 422
    assert client.post("/chat", json={"question": "a" * 501}).status_code == 422
    # Le seul quota disponible est encore là.
    assert client.post("/chat", json={"question": "Q1"}).status_code == 200


def test_health_jamais_limitee(faux_client_claude):
    installer_limiteur(par_minute=1)
    client.post("/chat", json={"question": "Q1"})
    for _ in range(20):
        assert client.get("/health").status_code == 200


# --- CORS (étape 10) ---

PORTFOLIO = "https://moussa197.github.io"


def pre_vol(client_test, origine):
    """Imite la requête OPTIONS qu'envoie le navigateur avant un POST JSON."""
    return client_test.options(
        "/chat",
        headers={
            "Origin": origine,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )


def test_pre_vol_depuis_le_portfolio_autorise():
    reponse = pre_vol(client, PORTFOLIO)
    assert reponse.status_code == 200
    assert reponse.headers["access-control-allow-origin"] == PORTFOLIO


def test_pre_vol_depuis_un_autre_site_refuse():
    reponse = pre_vol(client, "https://exemple.com")
    assert reponse.status_code == 400
    assert "access-control-allow-origin" not in reponse.headers


def test_post_depuis_un_autre_site_sans_autorisation(faux_client_claude):
    reponse = client.post(
        "/chat", json={"question": "Q1"}, headers={"Origin": "https://exemple.com"}
    )
    # Le navigateur empêcherait le site de lire cette réponse.
    assert "access-control-allow-origin" not in reponse.headers


def test_post_depuis_le_portfolio_autorise(faux_client_claude):
    reponse = client.post("/chat", json={"question": "Q1"}, headers={"Origin": PORTFOLIO})
    assert reponse.status_code == 200
    assert reponse.headers["access-control-allow-origin"] == PORTFOLIO  # jamais "*"


def test_origine_de_dev_configuree_autorisee(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINES_DEV", "http://localhost:5500")
    # Mini-application avec la même fonction ajouter_cors, sans recharger main.py.
    mini_app = FastAPI()

    @mini_app.post("/chat")
    def chat_factice():
        return {}

    ajouter_cors(mini_app, lire_origines_cors())
    mini_client = TestClient(mini_app)

    reponse = pre_vol(mini_client, "http://localhost:5500")
    assert reponse.status_code == 200
    assert reponse.headers["access-control-allow-origin"] == "http://localhost:5500"
    # Le portfolio reste autorisé, un autre site reste refusé.
    assert pre_vol(mini_client, PORTFOLIO).status_code == 200
    assert pre_vol(mini_client, "https://exemple.com").status_code == 400


def test_sans_origine_tout_fonctionne(faux_client_claude):
    # Appel sans en-tête Origin (curl, /docs) : le CORS n'intervient pas.
    assert client.get("/health").status_code == 200
    assert client.post("/chat", json={"question": "Q1"}).status_code == 200


# --- Démarrage (lifespan) ---


def test_demarrage_prepare_prompt_et_client(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    # Faux SDK : le démarrage crée un "client" sans rien envoyer.
    monkeypatch.setattr(anthropic, "Anthropic", MagicMock())

    with TestClient(app):
        # Le prompt contient les vrais documents de data/.
        assert '<document source="cv.md">' in app.state.prompt_systeme
        assert '<document source="projets.md">' in app.state.prompt_systeme
        assert app.state.client_claude is not None
        assert app.state.config.anthropic_api_key == "test-key"
        assert isinstance(app.state.limiteur, LimiteurRequetes)


def test_demarrage_echoue_sans_cle(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        with TestClient(app):
            pass
