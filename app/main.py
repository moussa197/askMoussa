"""Application FastAPI d'Ask Moussa.

Lancement en local : uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, field_validator

from app.claude_client import ClientClaude
from app.config import Config, charger_config
from app.documents import charger_documents
from app.prompt import construire_prompt_systeme
from app.rate_limit import LimiteurRequetes, obtenir_ip_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Exécuté une seule fois au démarrage du serveur.

    Si la clé ou un document manque, le démarrage échoue avec un message clair :
    mieux vaut un crash visible qu'un chatbot qui ne marche pas.
    """
    config = charger_config()
    app.state.config = config
    # Le prompt système est construit une fois, pas à chaque question.
    app.state.prompt_systeme = construire_prompt_systeme(charger_documents())
    app.state.client_claude = ClientClaude(config)
    # Un seul limiteur pour tout le serveur (d'où un seul worker uvicorn).
    app.state.limiteur = LimiteurRequetes(
        par_minute=config.rate_limit_par_minute,
        par_jour=config.rate_limit_par_jour,
        plafond_global=config.plafond_global_jour,
    )
    yield  # le serveur tourne ; rien à nettoyer à l'arrêt


# Objet application que lance uvicorn ("app.main:app").
app = FastAPI(title="Ask Moussa", lifespan=lifespan)


# --- Schémas de données (validés automatiquement par pydantic) ---


class ChatRequest(BaseModel):
    """Corps attendu pour POST /chat."""

    question: str

    @field_validator("question")
    @classmethod
    def retirer_espaces_et_refuser_vide(cls, valeur: str) -> str:
        """Retire les espaces autour ; une question vide ou faite d'espaces → 422.

        La longueur max, elle, dépend de la config : elle est vérifiée dans la route.
        """
        valeur = valeur.strip()
        if valeur == "":
            raise ValueError("La question ne doit pas être vide.")
        return valeur


class ChatResponse(BaseModel):
    """Corps renvoyé par POST /chat."""

    answer: str


# --- Dépendances : remplacées par des faux dans les tests (app.dependency_overrides) ---


def obtenir_config(request: Request) -> Config:
    """Renvoie la configuration chargée au démarrage."""
    return request.app.state.config


def obtenir_client_claude(request: Request) -> ClientClaude:
    """Renvoie le client Claude créé au démarrage."""
    return request.app.state.client_claude


def obtenir_prompt_systeme(request: Request) -> str:
    """Renvoie le prompt système construit au démarrage."""
    return request.app.state.prompt_systeme


def obtenir_limiteur(request: Request) -> LimiteurRequetes:
    """Renvoie le limiteur de requêtes créé au démarrage."""
    return request.app.state.limiteur


# --- Routes ---


@app.get("/health")
def health():
    """Route de santé appelée par Render pour vérifier que le service est vivant.

    Elle ne fait volontairement rien d'autre : pas d'appel à Claude (coûteux),
    pas de lecture de fichiers, pas de rate limit (Render doit toujours y accéder).
    """
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(
    demande: ChatRequest,
    request: Request,
    config: Config = Depends(obtenir_config),
    client_claude: ClientClaude = Depends(obtenir_client_claude),
    prompt_systeme: str = Depends(obtenir_prompt_systeme),
    limiteur: LimiteurRequetes = Depends(obtenir_limiteur),
):
    """Répond à une question sur Moussa à partir des documents de data/.

    "def" et non "async def" : le client Claude est synchrone (il attend la réponse).
    Avec "def", FastAPI l'exécute dans un thread à part, et le serveur continue
    de répondre aux autres visiteurs pendant ce temps.
    """
    # Vérifiée AVANT l'appel à Claude : une question trop longue ne coûte rien.
    # (La question a déjà été débarrassée de ses espaces autour par ChatRequest.)
    if len(demande.question) > config.max_question_length:
        raise HTTPException(
            status_code=422,
            detail=f"La question ne doit pas dépasser {config.max_question_length} caractères.",
        )

    # Rate limit juste avant Claude : seules les questions valides consomment du quota.
    # Message neutre : on ne dit pas laquelle des 3 limites est atteinte.
    ip = obtenir_ip_client(request, config.xff_position)
    if not limiteur.autoriser(ip):
        raise HTTPException(
            status_code=429,
            detail="Trop de questions. Réessayez un peu plus tard.",
        )

    reponse = client_claude.demander(prompt_systeme, demande.question)
    return ChatResponse(answer=reponse)
