"""Application FastAPI d'Ask Moussa.

Lancement en local : uvicorn app.main:app --reload
"""

from fastapi import FastAPI

# Objet application que lance uvicorn ("app.main:app").
app = FastAPI(title="Ask Moussa")


@app.get("/health")
def health():
    """Route de santé appelée par Render pour vérifier que le service est vivant.

    Elle ne fait volontairement rien d'autre : pas d'appel à Claude (coûteux),
    pas de lecture de fichiers, pas de rate limit (Render doit toujours y accéder).
    """
    return {"status": "ok"}
