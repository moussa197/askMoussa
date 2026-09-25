"""Application FastAPI d'Ask Moussa.

Lancement en local : uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel

from app.claude_client import ClientClaude
from app.config import charger_config
from app.documents import charger_documents
from app.prompt import construire_prompt_systeme


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Exécuté une seule fois au démarrage du serveur.

    Si la clé ou un document manque, le démarrage échoue avec un message clair :
    mieux vaut un crash visible qu'un chatbot qui ne marche pas.
    """
    config = charger_config()
    # Le prompt système est construit une fois, pas à chaque question.
    app.state.prompt_systeme = construire_prompt_systeme(charger_documents())
    app.state.client_claude = ClientClaude(config)
    yield  # le serveur tourne ; rien à nettoyer à l'arrêt


# Objet application que lance uvicorn ("app.main:app").
app = FastAPI(title="Ask Moussa", lifespan=lifespan)


# --- Schémas de données (validés automatiquement par pydantic) ---


class ChatRequest(BaseModel):
    """Corps attendu pour POST /chat."""

    question: str


class ChatResponse(BaseModel):
    """Corps renvoyé par POST /chat."""

    answer: str


# --- Dépendances : remplacées par des faux dans les tests (app.dependency_overrides) ---


def obtenir_client_claude(request: Request) -> ClientClaude:
    """Renvoie le client Claude créé au démarrage."""
    return request.app.state.client_claude


def obtenir_prompt_systeme(request: Request) -> str:
    """Renvoie le prompt système construit au démarrage."""
    return request.app.state.prompt_systeme


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
    client_claude: ClientClaude = Depends(obtenir_client_claude),
    prompt_systeme: str = Depends(obtenir_prompt_systeme),
):
    """Répond à une question sur Moussa à partir des documents de data/.

    "def" et non "async def" : le client Claude est synchrone (il attend la réponse).
    Avec "def", FastAPI l'exécute dans un thread à part, et le serveur continue
    de répondre aux autres visiteurs pendant ce temps.
    """
    reponse = client_claude.demander(prompt_systeme, demande.question)
    return ChatResponse(answer=reponse)
