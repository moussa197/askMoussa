"""Tests de app/rate_limit.py avec une fausse horloge (aucun sleep, tests instantanés)."""

from types import SimpleNamespace

import pytest
from starlette.datastructures import Headers

from app.rate_limit import UN_JOUR, LimiteurRequetes, obtenir_ip_client


class FausseHorloge:
    """Horloge qu'on avance à la main : horloge.avancer(61) = « 61 secondes plus tard »."""

    def __init__(self):
        self.maintenant = 1000.0

    def __call__(self):
        return self.maintenant

    def avancer(self, secondes):
        self.maintenant += secondes


@pytest.fixture
def horloge():
    return FausseHorloge()


def creer_limiteur(horloge, par_minute=10, par_jour=30, plafond_global=300):
    return LimiteurRequetes(par_minute, par_jour, plafond_global, horloge=horloge)


# --- Limite par minute ---


def test_onzieme_question_de_la_minute_refusee(horloge):
    limiteur = creer_limiteur(horloge)
    for _ in range(10):
        assert limiteur.autoriser("1.1.1.1")
    assert not limiteur.autoriser("1.1.1.1")


def test_de_nouveau_accepte_apres_une_minute(horloge):
    limiteur = creer_limiteur(horloge)
    for _ in range(10):
        limiteur.autoriser("1.1.1.1")
    horloge.avancer(61)
    assert limiteur.autoriser("1.1.1.1")


# --- Limite par jour ---


def test_trente_et_unieme_question_du_jour_refusee(horloge):
    limiteur = creer_limiteur(horloge)
    for _ in range(30):
        assert limiteur.autoriser("1.1.1.1")
        horloge.avancer(61)  # espacées pour ne pas atteindre la limite par minute
    assert not limiteur.autoriser("1.1.1.1")


def test_de_nouveau_accepte_apres_24_heures(horloge):
    limiteur = creer_limiteur(horloge)
    for _ in range(30):
        limiteur.autoriser("1.1.1.1")
        horloge.avancer(61)
    horloge.avancer(UN_JOUR)
    assert limiteur.autoriser("1.1.1.1")


# --- Plafond global ---


def test_trois_cent_unieme_question_refusee_meme_nouvelle_ip(horloge):
    limiteur = creer_limiteur(horloge)
    for numero in range(300):
        assert limiteur.autoriser(f"10.0.0.{numero}")  # 300 IP différentes
    assert not limiteur.autoriser("99.99.99.99")  # IP jamais vue


# --- Comportements généraux ---


def test_ip_independantes(horloge):
    limiteur = creer_limiteur(horloge)
    for _ in range(10):
        limiteur.autoriser("1.1.1.1")
    assert not limiteur.autoriser("1.1.1.1")
    assert limiteur.autoriser("2.2.2.2")  # l'autre IP n'est pas bloquée


def test_question_refusee_non_comptee(horloge):
    limiteur = creer_limiteur(horloge, par_minute=2, par_jour=3)
    limiteur.autoriser("1.1.1.1")
    limiteur.autoriser("1.1.1.1")
    for _ in range(5):
        assert not limiteur.autoriser("1.1.1.1")  # refusées : ne doivent pas compter
    horloge.avancer(61)
    # Si les refus avaient compté, la limite par jour (3) serait déjà atteinte.
    assert limiteur.autoriser("1.1.1.1")


def test_ip_expirees_oubliees(horloge):
    limiteur = creer_limiteur(horloge)
    limiteur.autoriser("1.1.1.1")
    limiteur.autoriser("2.2.2.2")
    assert limiteur.nombre_ip_suivies == 2
    horloge.avancer(UN_JOUR + 1)
    limiteur.autoriser("3.3.3.3")
    assert limiteur.nombre_ip_suivies == 1  # seules les IP récentes restent en mémoire


# --- obtenir_ip_client ---


def fausse_requete(xff=None, ip_connexion="5.5.5.5"):
    """Imite une requête Starlette : request.client.host et request.headers.

    `xff` : une chaîne (une ligne d'en-tête) ou une liste (plusieurs lignes séparées).
    On utilise les vrais Headers de Starlette, qui gèrent les en-têtes répétés.
    """
    lignes = [] if xff is None else ([xff] if isinstance(xff, str) else xff)
    brut = [(b"x-forwarded-for", ligne.encode()) for ligne in lignes]
    return SimpleNamespace(client=SimpleNamespace(host=ip_connexion), headers=Headers(raw=brut))


def test_ip_sans_position_configuree():
    requete = fausse_requete(xff="1.2.3.4, 6.6.6.6")
    assert obtenir_ip_client(requete, None) == "5.5.5.5"


def test_ip_sans_entete():
    assert obtenir_ip_client(fausse_requete(), -1) == "5.5.5.5"


@pytest.mark.parametrize(
    "position, attendu",
    [(0, "1.2.3.4"), (-1, "8.8.8.8"), (-2, "6.6.6.6")],
)
def test_ip_selon_la_position(position, attendu):
    requete = fausse_requete(xff="1.2.3.4,  6.6.6.6 ,8.8.8.8")  # espaces irréguliers
    assert obtenir_ip_client(requete, position) == attendu


def test_ip_position_hors_limites():
    requete = fausse_requete(xff="1.2.3.4")
    assert obtenir_ip_client(requete, -3) == "5.5.5.5"


def test_ip_plusieurs_lignes_x_forwarded_for():
    # Le visiteur envoie sa propre ligne, le proxy en ajoute une seconde :
    # -1 doit désigner l'IP ajoutée par le proxy, pas celle du visiteur.
    requete = fausse_requete(xff=["1.2.3.4", "8.8.8.8"])
    assert obtenir_ip_client(requete, -1) == "8.8.8.8"
    assert obtenir_ip_client(requete, 0) == "1.2.3.4"
