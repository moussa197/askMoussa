"""Seul module qui appelle l'API Claude (SDK officiel anthropic)."""

import anthropic

from app.config import Config
from app.prompt import baliser_question

# Délai max d'un appel (en secondes) et nombre de nouvelles tentatives.
# Le SDK retente aussi après un timeout : pire cas ≈ 20 s × 2 essais = 40 s,
# largement assez pour une réponse de 400 tokens avec Haiku (quelques secondes).
TIMEOUT_SECONDES = 20.0
NOUVELLES_TENTATIVES = 1


class ReponseClaudeVide(Exception):
    """Claude a répondu sans aucun bloc de texte (cas rare, par exemple un refus)."""


class ClientClaude:
    """Envoie une question à Claude et renvoie le texte de la réponse."""

    def __init__(self, config: Config, client_anthropic=None):
        """`client_anthropic` : laissé vide en production (le vrai client est créé ici),
        remplacé par un faux client dans les tests pour qu'aucun appel réseau n'ait lieu.
        """
        self.config = config
        if client_anthropic is None:
            # Clé passée explicitement : on utilise celle vérifiée par config.py,
            # sans laisser le SDK chercher d'autres identifiants sur la machine.
            client_anthropic = anthropic.Anthropic(
                api_key=config.anthropic_api_key,
                timeout=TIMEOUT_SECONDES,
                max_retries=NOUVELLES_TENTATIVES,
            )
        self.client = client_anthropic

    def demander(self, system: str, question: str) -> str:
        """Pose la question avec le prompt système donné et renvoie la réponse en texte.

        La question est balisée ici, pour qu'aucun appel ne puisse partir sans balise.
        Les erreurs du SDK (clé invalide, timeout, réseau...) remontent telles quelles :
        elles seront traduites en réponse HTTP par main.py (étape 11).
        """
        reponse = self.client.messages.create(
            model=self.config.claude_model,
            max_tokens=self.config.claude_max_tokens,
            system=system,
            messages=[{"role": "user", "content": baliser_question(question)}],
        )

        # response.content est une liste de blocs : on ne garde que les blocs de texte.
        # Si la réponse a été coupée par max_tokens, on la renvoie telle quelle.
        texte = "".join(bloc.text for bloc in reponse.content if bloc.type == "text").strip()
        if texte == "":
            raise ReponseClaudeVide("La réponse de Claude ne contient aucun texte.")
        return texte
