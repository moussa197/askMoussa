"""Tests de app/main.py avec le TestClient de FastAPI (aucun serveur, aucun réseau)."""

import logging
from dataclasses import replace
from unittest.mock import MagicMock

import anthropic
import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.main as main_module
from app.claude_client import ReponseClaudeVide
from app.config import lire_origines_cors
from app.main import (
    MESSAGE_INDISPONIBLE,
    MESSAGE_REQUETE_INVALIDE,
    ajouter_cors,
    app,
    obtenir_config,
    obtenir_limiteur,
    options_docs,
)
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


# --- Erreurs de Claude → 503 (étape 11) ---

# Fausse requête/réponse HTTP pour construire les VRAIES classes d'erreur du SDK.
# httpx2 est la bibliothèque HTTP du SDK anthropic 1.x (déjà installée avec lui).
REQUETE_HTTP = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


def erreur_statut(classe, statut, message):
    """Erreur où l'API a répondu (APIStatusError), avec un request_id reconnaissable."""
    reponse = httpx2.Response(statut, request=REQUETE_HTTP, headers={"request-id": "req_test_123"})
    return classe(message, response=reponse, body=None)


ERREURS_CLAUDE = {
    # Le bug observé à l'étape 7 : crédit épuisé.
    "credit_epuise": lambda: erreur_statut(
        anthropic.BadRequestError, 400, "Your credit balance is too low to access the Anthropic API."
    ),
    "cle_invalide": lambda: erreur_statut(anthropic.AuthenticationError, 401, "invalid x-api-key"),
    "limite_anthropic": lambda: erreur_statut(anthropic.RateLimitError, 429, "rate limited"),
    "erreur_serveur": lambda: erreur_statut(anthropic.InternalServerError, 500, "internal error"),
    "timeout": lambda: anthropic.APITimeoutError(request=REQUETE_HTTP),
    "reseau": lambda: anthropic.APIConnectionError(request=REQUETE_HTTP),
    "reponse_vide": lambda: ReponseClaudeVide("La réponse de Claude ne contient aucun texte."),
}


@pytest.mark.parametrize("nom", list(ERREURS_CLAUDE))
def test_erreur_claude_renvoie_503_neutre(faux_client_claude, nom):
    faux_client_claude.erreur = ERREURS_CLAUDE[nom]()
    reponse = client.post("/chat", json={"question": "Quels projets a réalisés Moussa ?"})
    assert reponse.status_code == 503
    assert reponse.json() == {"detail": MESSAGE_INDISPONIBLE}


def test_journal_utile_mais_sans_la_question(faux_client_claude, caplog):
    faux_client_claude.erreur = ERREURS_CLAUDE["credit_epuise"]()
    with caplog.at_level(logging.ERROR):
        client.post("/chat", json={"question": "QUESTION-SECRETE-123"})

    assert "BadRequestError" in caplog.text
    assert "req_test_123" in caplog.text
    assert "credit balance is too low" in caplog.text
    assert "QUESTION-SECRETE-123" not in caplog.text
    assert "test-key" not in caplog.text


def test_bug_de_notre_code_reste_une_erreur_500(faux_client_claude):
    # Un bug n'est pas une panne de Claude : il ne doit pas être masqué en 503.
    faux_client_claude.erreur = RuntimeError("bug inattendu")
    client_sans_exception = TestClient(app, raise_server_exceptions=False)
    reponse = client_sans_exception.post("/chat", json={"question": "Q1"})
    assert reponse.status_code == 500


def test_reponses_413_429_et_503_documentees():
    # Elles doivent apparaître dans /docs (schéma OpenAPI), et non en "Undocumented".
    reponses = client.get("/openapi.json").json()["paths"]["/chat"]["post"]["responses"]
    assert "413" in reponses
    assert "429" in reponses
    assert "503" in reponses


# --- 422 neutre (revue de sécurité, n°8) ---


@pytest.mark.parametrize(
    "corps",
    [
        {},  # question absente
        {"question": "   "},  # question vide
        {"question": ["ENTREE-RENVOYEE"] * 50},  # mauvais type
        {"question": 12345},  # mauvais type
    ],
)
def test_422_message_fixe_sans_renvoyer_l_entree(faux_client_claude, corps):
    reponse = client.post("/chat", json=corps)
    assert reponse.status_code == 422
    assert reponse.json() == {"detail": MESSAGE_REQUETE_INVALIDE}
    assert "ENTREE-RENVOYEE" not in reponse.text
    assert faux_client_claude.appels == []


def test_json_mal_forme_refuse(faux_client_claude):
    reponse = client.post(
        "/chat", content=b'{"question": ', headers={"Content-Type": "application/json"}
    )
    assert reponse.status_code == 422
    assert reponse.json() == {"detail": MESSAGE_REQUETE_INVALIDE}


def test_422_documente_avec_le_bon_format():
    reponses = client.get("/openapi.json").json()["paths"]["/chat"]["post"]["responses"]
    assert reponses["422"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/MessageErreur"
    )


# --- Taille du corps (revue de sécurité, n°1) ---


def test_corps_trop_gros_refuse_avant_claude(faux_client_claude):
    reponse = client.post("/chat", json={"question": "a" * 10_000})  # environ 10 Ko
    assert reponse.status_code == 413
    assert reponse.json() == {"detail": "La requête est trop volumineuse."}
    assert faux_client_claude.appels == []


def test_413_garde_les_entetes_cors(faux_client_claude):
    # Le CORS enveloppe la limite de taille : le widget peut lire ce code d'erreur.
    reponse = client.post(
        "/chat",
        json={"question": "a" * 10_000},
        headers={"Origin": "https://moussa197.github.io"},
    )
    assert reponse.status_code == 413
    assert reponse.headers["access-control-allow-origin"] == "https://moussa197.github.io"


# --- Déploiement : /docs coupé en production, diagnostic IP (étape 13) ---


def test_docs_coupees_en_production():
    # Mini-application construite avec les options de production.
    mini_app = FastAPI(**options_docs(en_production=True))
    mini_client = TestClient(mini_app)
    for chemin in ["/docs", "/redoc", "/openapi.json"]:
        assert mini_client.get(chemin).status_code == 404


def test_docs_disponibles_en_local():
    assert options_docs(en_production=False) == {}
    assert client.get("/docs").status_code == 200


def test_diagnostic_ip_active(monkeypatch, caplog):
    monkeypatch.setattr(main_module, "DIAGNOSTIC_IP", True)
    with caplog.at_level(logging.WARNING):
        client.get("/health", headers={"X-Forwarded-For": "1.2.3.4"})
    assert "Diagnostic IP" in caplog.text
    assert "1.2.3.4" in caplog.text


def test_diagnostic_ip_inactif_par_defaut(caplog):
    with caplog.at_level(logging.WARNING):
        client.get("/health", headers={"X-Forwarded-For": "1.2.3.4"})
    assert "Diagnostic IP" not in caplog.text


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
