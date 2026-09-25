"""Lecture et vérification de la configuration (variables d'environnement).

C'est le seul module qui lit os.environ. Les autres modules reçoivent un objet
Config déjà vérifié, créé par charger_config() au démarrage du serveur.
"""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Charge le fichier .env une seule fois, au chargement du module.
# - En local : remplit les variables absentes à partir de .env.
# - Sur Render : il n'y a pas de .env, cet appel ne fait rien.
# On ne le rappelle pas dans charger_config(), sinon un test qui retire la clé
# (monkeypatch.delenv) verrait la vraie clé du .env revenir.
load_dotenv()

# Seule origine de production autorisée pour le CORS (toujours présente).
ORIGINE_PORTFOLIO = "https://moussa197.github.io"


@dataclass(frozen=True)
class Config:
    """Réglages de l'application. frozen=True : impossible de les modifier par erreur."""

    # repr=False : la clé n'apparaît jamais dans un print(config) ou un message d'erreur.
    anthropic_api_key: str = field(repr=False)
    claude_model: str
    claude_max_tokens: int
    max_question_length: int
    rate_limit_par_minute: int
    rate_limit_par_jour: int
    plafond_global_jour: int
    cors_origines: tuple[str, ...]
    # None = position pas encore mesurée (voir PLAN.md §4.3).
    xff_position: int | None


def _lire_texte(nom: str, defaut: str = "") -> str:
    """Renvoie la variable sans espaces autour, ou la valeur par défaut si elle est absente."""
    return os.environ.get(nom, defaut).strip()


def _lire_entier_positif(nom: str, defaut: int) -> int:
    """Lit un entier strictement positif. Variable absente ou vide → valeur par défaut."""
    texte = _lire_texte(nom)
    if texte == "":
        return defaut
    try:
        valeur = int(texte)
    except ValueError:
        raise ValueError(f'{nom} doit être un entier positif, reçu : "{texte}"') from None
    if valeur <= 0:
        raise ValueError(f'{nom} doit être un entier positif, reçu : "{texte}"')
    return valeur


def _lire_cle_api() -> str:
    """Lit la clé API (obligatoire). Le message d'erreur n'affiche jamais sa valeur."""
    cle = _lire_texte("ANTHROPIC_API_KEY")
    if cle == "":
        raise ValueError(
            "ANTHROPIC_API_KEY est absente : ajoute-la dans le fichier .env "
            "(en local) ou dans le tableau de bord Render."
        )
    return cle


def lire_origines_cors() -> tuple[str, ...]:
    """Portfolio + origines de dev de CORS_ORIGINES_DEV (séparées par des virgules).

    Toute origine contenant "*" est refusée : on ne veut jamais ouvrir l'API à tous.
    Publique (sans "_") car main.py l'appelle à l'import pour configurer le CORS :
    le middleware doit être ajouté avant le démarrage, et cette lecture n'exige pas la clé.
    """
    origines = [ORIGINE_PORTFOLIO]
    for morceau in _lire_texte("CORS_ORIGINES_DEV").split(","):
        origine = morceau.strip()
        if origine == "":
            continue  # ignore les éléments vides (ex. "a,,b" ou virgule finale)
        if "*" in origine:
            raise ValueError(f'CORS_ORIGINES_DEV ne doit pas contenir "*", reçu : "{origine}"')
        if origine not in origines:
            origines.append(origine)
    return tuple(origines)


def _lire_xff_position() -> int | None:
    """Position de l'IP réelle dans X-Forwarded-For. Vide → None (pas encore mesurée)."""
    texte = _lire_texte("XFF_POSITION")
    if texte == "":
        return None
    try:
        return int(texte)
    except ValueError:
        raise ValueError(
            f'XFF_POSITION doit être un entier (ex. 0, -1, -2), reçu : "{texte}"'
        ) from None


def charger_config() -> Config:
    """Lit toutes les variables, les vérifie et renvoie un objet Config.

    Lève ValueError avec un message clair si une valeur est absente ou invalide.
    """
    return Config(
        anthropic_api_key=_lire_cle_api(),
        claude_model=_lire_texte("CLAUDE_MODEL") or "claude-haiku-4-5",
        claude_max_tokens=_lire_entier_positif("CLAUDE_MAX_TOKENS", 400),
        max_question_length=_lire_entier_positif("MAX_QUESTION_LENGTH", 500),
        rate_limit_par_minute=_lire_entier_positif("RATE_LIMIT_PAR_MINUTE", 10),
        rate_limit_par_jour=_lire_entier_positif("RATE_LIMIT_PAR_JOUR", 30),
        plafond_global_jour=_lire_entier_positif("PLAFOND_GLOBAL_JOUR", 300),
        cors_origines=lire_origines_cors(),
        xff_position=_lire_xff_position(),
    )
