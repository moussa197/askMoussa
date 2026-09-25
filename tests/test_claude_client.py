"""Tests de app/claude_client.py. Faux client uniquement : AUCUN appel réseau."""

import os
from types import SimpleNamespace
from unittest.mock import MagicMock

import anthropic
import pytest

from app.claude_client import (
    NOUVELLES_TENTATIVES,
    TIMEOUT_SECONDES,
    ClientClaude,
    ReponseClaudeVide,
)
from app.prompt import baliser_question
from tests.conftest import CONFIG_TEST


def faux_client(*blocs):
    """Faux client du SDK dont messages.create renvoie une réponse avec ces blocs."""
    client = MagicMock()
    client.messages.create.return_value = SimpleNamespace(content=list(blocs))
    return client


def bloc_texte(texte):
    return SimpleNamespace(type="text", text=texte)


def test_parametres_envoyes_a_claude():
    client = faux_client(bloc_texte("Réponse"))
    ClientClaude(CONFIG_TEST, client).demander("PROMPT SYSTÈME", "Quels projets ?")

    client.messages.create.assert_called_once_with(
        model="claude-haiku-4-5",
        max_tokens=400,
        system="PROMPT SYSTÈME",
        messages=[{"role": "user", "content": baliser_question("Quels projets ?")}],
    )


def test_texte_de_la_reponse_extrait():
    client = faux_client(bloc_texte("  Moussa a réalisé Letterix.  "))
    reponse = ClientClaude(CONFIG_TEST, client).demander("system", "question")
    assert reponse == "Moussa a réalisé Letterix."


def test_blocs_assembles_et_autres_types_ignores():
    client = faux_client(
        bloc_texte("Première partie. "),
        SimpleNamespace(type="autre_type"),  # bloc sans texte : doit être ignoré
        bloc_texte("Seconde partie."),
    )
    reponse = ClientClaude(CONFIG_TEST, client).demander("system", "question")
    assert reponse == "Première partie. Seconde partie."


@pytest.mark.parametrize("blocs", [[], [bloc_texte("   ")], [SimpleNamespace(type="autre_type")]])
def test_reponse_sans_texte_refusee(blocs):
    client = faux_client(*blocs)
    with pytest.raises(ReponseClaudeVide):
        ClientClaude(CONFIG_TEST, client).demander("system", "question")


def test_tests_isoles_de_la_vraie_api():
    # Garanti par la fixture automatique de conftest.py : jamais la vraie clé,
    # et un appel oublié partirait vers une adresse locale fermée (donc échouerait).
    assert os.environ["ANTHROPIC_API_KEY"] == "test-key"
    assert os.environ["ANTHROPIC_BASE_URL"] == "http://127.0.0.1:9"


def test_vrai_client_cree_avec_la_config(monkeypatch):
    # On remplace la classe du SDK par un faux : rien n'est envoyé.
    fausse_classe = MagicMock()
    monkeypatch.setattr(anthropic, "Anthropic", fausse_classe)

    client_claude = ClientClaude(CONFIG_TEST)

    fausse_classe.assert_called_once_with(
        api_key="test-key",
        timeout=TIMEOUT_SECONDES,
        max_retries=NOUVELLES_TENTATIVES,
    )
    assert client_claude.client is fausse_classe.return_value
