"""Fixtures communes à tous les tests (chargées automatiquement par pytest)."""

import pytest

from app.main import app, obtenir_client_claude, obtenir_prompt_systeme

PROMPT_TEST = "PROMPT SYSTÈME DE TEST"


class FauxClientClaude:
    """Remplace ClientClaude : enregistre les appels et renvoie une réponse fixe."""

    def __init__(self, reponse="Réponse de test"):
        self.reponse = reponse
        self.appels = []

    def demander(self, system, question):
        self.appels.append({"system": system, "question": question})
        return self.reponse


@pytest.fixture
def faux_client_claude():
    """Installe le faux client et un faux prompt dans l'app, puis nettoie après le test.

    Note : TestClient(app) utilisé SANS "with" ne lance pas le lifespan,
    donc ni vraie clé ni vrai client ne sont nécessaires.
    """
    faux = FauxClientClaude()
    app.dependency_overrides[obtenir_client_claude] = lambda: faux
    app.dependency_overrides[obtenir_prompt_systeme] = lambda: PROMPT_TEST
    yield faux
    app.dependency_overrides.clear()
