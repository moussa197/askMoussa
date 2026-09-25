"""Tests de app/limite_corps.py : appels ASGI directs, sans serveur ni réseau."""

import asyncio

from app.limite_corps import MESSAGE_TROP_VOLUMINEUX, TAILLE_MAX_CORPS, LimiteTailleCorps


class FausseApp:
    """Application ASGI minimale : lit tout le corps reçu et répond 200."""

    def __init__(self):
        self.appelee = False
        self.corps_recu = None

    async def __call__(self, scope, receive, send):
        self.appelee = True
        corps = b""
        encore = True
        while encore:
            message = await receive()
            corps += message.get("body", b"")
            encore = message.get("more_body", False)
        self.corps_recu = corps
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})


def appeler(morceaux, content_length=None, methode="POST"):
    """Envoie une requête au middleware, le corps découpé en `morceaux`.

    Renvoie (fausse app, statut de la réponse, corps de la réponse, nombre de morceaux lus).
    """
    app = FausseApp()
    middleware = LimiteTailleCorps(app)

    headers = []
    if content_length is not None:
        headers.append((b"content-length", str(content_length).encode()))
    scope = {"type": "http", "method": methode, "path": "/chat", "headers": headers}

    messages = [
        {"type": "http.request", "body": morceau, "more_body": i < len(morceaux) - 1}
        for i, morceau in enumerate(morceaux)
    ] or [{"type": "http.request", "body": b"", "more_body": False}]
    lus = []

    async def receive():
        if messages:
            lus.append(1)
            return messages.pop(0)
        return {"type": "http.disconnect"}

    envoyes = []

    async def send(message):
        envoyes.append(message)

    asyncio.run(middleware(scope, receive, send))

    statut = next(m["status"] for m in envoyes if m["type"] == "http.response.start")
    corps = b"".join(m.get("body", b"") for m in envoyes if m["type"] == "http.response.body")
    return app, statut, corps, len(lus)


def test_petit_corps_transmis_intact():
    corps = '{"question": "Où étudie Moussa ?"}'.encode()
    app, statut, _, _ = appeler([corps], content_length=len(corps))
    assert statut == 200
    assert app.corps_recu == corps


def test_corps_en_plusieurs_morceaux_reassemble():
    app, statut, _, _ = appeler([b'{"question": ', b'"Bonjour"}'])
    assert statut == 200
    assert app.corps_recu == b'{"question": "Bonjour"}'


def test_corps_trop_gros_refuse():
    app, statut, corps, _ = appeler([b"a" * (TAILLE_MAX_CORPS + 1)])
    assert statut == 413
    assert MESSAGE_TROP_VOLUMINEUX in corps.decode()
    assert not app.appelee  # FastAPI n'est jamais appelé


def test_corps_exactement_a_la_limite_accepte():
    app, statut, _, _ = appeler([b"a" * TAILLE_MAX_CORPS])
    assert statut == 200
    assert app.appelee


def test_content_length_trop_grand_refuse_sans_lire():
    # L'en-tête annonce 100 Mo : refus immédiat, aucun morceau du corps n'est lu.
    app, statut, _, nombre_lus = appeler([b"a" * 10], content_length=100 * 1024 * 1024)
    assert statut == 413
    assert nombre_lus == 0
    assert not app.appelee


def test_envoi_par_morceaux_sans_content_length_coupe_a_la_limite():
    # 20 morceaux de 1 Ko sans Content-Length : on s'arrête dès que 8 Ko sont dépassés.
    morceaux = [b"a" * 1024] * 20
    app, statut, _, nombre_lus = appeler(morceaux)
    assert statut == 413
    assert nombre_lus == TAILLE_MAX_CORPS // 1024 + 1  # la suite n'est jamais lue
    assert not app.appelee


def test_get_sans_corps_passe():
    app, statut, _, _ = appeler([], methode="GET")
    assert statut == 200
    assert app.appelee
