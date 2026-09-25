"""Tests de app/main.py avec le TestClient de FastAPI (aucun serveur, aucun réseau)."""

from unittest.mock import MagicMock

import anthropic
import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import PROMPT_TEST

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


def test_demarrage_echoue_sans_cle(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        with TestClient(app):
            pass
