"""Tests de app/main.py avec le TestClient de FastAPI (aucun serveur, aucun réseau)."""

from dataclasses import replace
from unittest.mock import MagicMock

import anthropic
import pytest
from fastapi.testclient import TestClient

from app.main import app, obtenir_config
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


def test_demarrage_echoue_sans_cle(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        with TestClient(app):
            pass
