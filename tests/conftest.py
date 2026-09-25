"""Fixtures communes à tous les tests (chargées automatiquement par pytest)."""

import pytest

from app.config import Config
from app.main import (
    app,
    obtenir_client_claude,
    obtenir_config,
    obtenir_limiteur,
    obtenir_prompt_systeme,
)
from app.rate_limit import LimiteurRequetes

PROMPT_TEST = "PROMPT SYSTÈME DE TEST"

# Configuration de test : mêmes valeurs que les défauts, avec une fausse clé.
CONFIG_TEST = Config(
    anthropic_api_key="test-key",
    claude_model="claude-haiku-4-5",
    claude_max_tokens=400,
    max_question_length=500,
    rate_limit_par_minute=10,
    rate_limit_par_jour=30,
    plafond_global_jour=300,
    cors_origines=("https://moussa197.github.io",),
    xff_position=None,
)


class FauxClientClaude:
    """Remplace ClientClaude : enregistre les appels et renvoie une réponse fixe.

    Si `erreur` est renseignée, demander() lève cette erreur (simule une panne).
    """

    def __init__(self, reponse="Réponse de test"):
        self.reponse = reponse
        self.erreur = None
        self.appels = []

    def demander(self, system, question):
        self.appels.append({"system": system, "question": question})
        if self.erreur is not None:
            raise self.erreur
        return self.reponse


@pytest.fixture
def faux_client_claude():
    """Installe le faux client, un faux prompt, la config de test et un limiteur
    NEUF (compteurs à zéro) dans l'app, puis nettoie après le test.

    Note : TestClient(app) utilisé SANS "with" ne lance pas le lifespan,
    donc ni vraie clé ni vrai client ne sont nécessaires.
    """
    faux = FauxClientClaude()
    app.dependency_overrides[obtenir_client_claude] = lambda: faux
    app.dependency_overrides[obtenir_prompt_systeme] = lambda: PROMPT_TEST
    app.dependency_overrides[obtenir_config] = lambda: CONFIG_TEST
    limiteur = LimiteurRequetes(
        par_minute=CONFIG_TEST.rate_limit_par_minute,
        par_jour=CONFIG_TEST.rate_limit_par_jour,
        plafond_global=CONFIG_TEST.plafond_global_jour,
    )
    app.dependency_overrides[obtenir_limiteur] = lambda: limiteur
    yield faux
    app.dependency_overrides.clear()
