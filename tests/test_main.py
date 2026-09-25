"""Tests de app/main.py avec le TestClient de FastAPI (aucun serveur, aucun réseau)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_repond_ok():
    reponse = client.get("/health")
    assert reponse.status_code == 200
    assert reponse.json() == {"status": "ok"}


def test_health_refuse_post():
    # Seule la méthode GET est déclarée : FastAPI renvoie 405 (méthode non autorisée).
    reponse = client.post("/health")
    assert reponse.status_code == 405
