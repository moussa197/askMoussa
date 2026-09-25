"""Middleware qui refuse (413) les corps de requête trop gros, AVANT FastAPI.

Sans lui, FastAPI lit tout le corps en mémoire avant de le valider : quelques requêtes
de plusieurs dizaines de Mo suffiraient à dépasser les 512 Mo de Render, et chaque
redémarrage remettrait les quotas du rate limit à zéro.
"""

from starlette.responses import JSONResponse

# Une question fait au plus 500 caractères ; même écrite sous forme échappée
# (\uXXXX, jusqu'à 12 octets par emoji), elle tient largement dans 8 Ko.
TAILLE_MAX_CORPS = 8 * 1024  # en octets

MESSAGE_TROP_VOLUMINEUX = "La requête est trop volumineuse."


class LimiteTailleCorps:
    """Middleware ASGI : lit le corps en comptant les octets, puis le transmet intact.

    - Content-Length annonce déjà trop → 413 immédiat, sans rien lire.
    - Sinon on lit morceau par morceau ; dès que la limite est dépassée → 413,
      sans lire la suite (couvre aussi les envois "par morceaux" sans Content-Length).
    - Si tout va bien, FastAPI reçoit le corps déjà lu, comme s'il n'avait pas été touché.
    """

    def __init__(self, app, taille_max: int = TAILLE_MAX_CORPS):
        self.app = app
        self.taille_max = taille_max

    async def __call__(self, scope, receive, send):
        # On ne filtre que les requêtes HTTP (pas le démarrage "lifespan").
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 1. L'en-tête Content-Length annonce-t-il déjà trop ?
        annonce = dict(scope["headers"]).get(b"content-length")
        if annonce is not None and annonce.isdigit() and int(annonce) > self.taille_max:
            await self._refuser(scope, receive, send)
            return

        # 2. Lecture du corps en comptant les octets (la mémoire ne dépasse jamais la limite).
        corps = b""
        encore = True
        while encore:
            message = await receive()
            if message["type"] == "http.disconnect":
                return  # le client est parti : rien à répondre
            corps += message.get("body", b"")
            if len(corps) > self.taille_max:
                await self._refuser(scope, receive, send)
                return
            encore = message.get("more_body", False)

        # 3. On rejoue le corps déjà lu pour FastAPI, puis on laisse passer
        #    les messages suivants (par exemple une déconnexion du client).
        deja_transmis = False

        async def receive_rejoue():
            nonlocal deja_transmis
            if not deja_transmis:
                deja_transmis = True
                return {"type": "http.request", "body": corps, "more_body": False}
            return await receive()

        await self.app(scope, receive_rejoue, send)

    async def _refuser(self, scope, receive, send):
        """Répond 413 au format habituel de l'API : {"detail": "..."}."""
        reponse = JSONResponse({"detail": MESSAGE_TROP_VOLUMINEUX}, status_code=413)
        await reponse(scope, receive, send)
