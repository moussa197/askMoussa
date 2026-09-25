"""Limitation du nombre de questions (rate limiting), en mémoire, sans dépendance.

Trois limites : par IP et par minute, par IP et par jour, et un plafond global par jour.
Algorithme de la « fenêtre glissante » : on garde les heures des questions acceptées
et on compte celles des 60 dernières secondes (ou des 24 dernières heures).

Limite connue : les compteurs repartent à zéro à chaque redémarrage du serveur
(voir PLAN.md §4.3). Il faut un seul worker uvicorn pour qu'ils soient partagés.
"""

import threading
import time
from collections import deque

UNE_MINUTE = 60
UN_JOUR = 24 * 60 * 60


class LimiteurRequetes:
    """Décide si une question venant d'une IP peut être acceptée."""

    def __init__(self, par_minute: int, par_jour: int, plafond_global: int, horloge=time.monotonic):
        """`horloge` : fonction qui renvoie l'heure en secondes. time.monotonic ne recule
        jamais (même si l'heure du système change) ; les tests passent une fausse horloge.
        """
        self.par_minute = par_minute
        self.par_jour = par_jour
        self.plafond_global = plafond_global
        self._horloge = horloge
        # Pour chaque IP : heures de ses questions acceptées sur les dernières 24 h.
        self._par_ip: dict[str, deque[float]] = {}
        # Heures de toutes les questions acceptées sur les dernières 24 h.
        self._global: deque[float] = deque()
        # La route /chat tourne dans plusieurs threads : sans verrou, deux questions
        # simultanées pourraient lire le même compteur et dépasser la limite.
        self._verrou = threading.Lock()

    def autoriser(self, ip: str) -> bool:
        """Renvoie True et enregistre la question si les 3 limites le permettent.

        Une question refusée n'est PAS enregistrée : un visiteur bloqué qui insiste
        ne prolonge pas son blocage.
        """
        with self._verrou:
            maintenant = self._horloge()
            self._oublier_avant(maintenant - UN_JOUR)

            historique = self._par_ip.get(ip, deque())
            dans_la_minute = sum(1 for heure in historique if heure > maintenant - UNE_MINUTE)

            if (
                len(self._global) >= self.plafond_global
                or len(historique) >= self.par_jour
                or dans_la_minute >= self.par_minute
            ):
                return False

            historique.append(maintenant)
            self._par_ip[ip] = historique
            self._global.append(maintenant)
            return True

    @property
    def nombre_ip_suivies(self) -> int:
        """Nombre d'IP encore gardées en mémoire (utile pour vérifier le nettoyage)."""
        return len(self._par_ip)

    def _oublier_avant(self, limite: float) -> None:
        """Retire les heures plus anciennes que `limite`, et les IP qui n'ont plus rien.

        Comme seules les questions acceptées sont gardées (300 max sur 24 h),
        ce parcours reste très court et la mémoire reste bornée.
        """
        while self._global and self._global[0] <= limite:
            self._global.popleft()
        for ip in list(self._par_ip):
            historique = self._par_ip[ip]
            while historique and historique[0] <= limite:
                historique.popleft()
            if not historique:
                del self._par_ip[ip]


def obtenir_ip_client(request, xff_position: int | None) -> str:
    """Renvoie l'IP du visiteur.

    - xff_position vide (None) ou en-tête X-Forwarded-For absent → IP de la connexion
      (cas du développement local, et de Render tant que la position n'est pas mesurée).
    - Sinon → l'élément de X-Forwarded-For à cette position (0 = premier, -1 = dernier...).
    - Position hors limites (en-tête plus court que prévu) → IP de la connexion.
    """
    ip_connexion = request.client.host if request.client else "inconnue"
    if xff_position is None:
        return ip_connexion

    # getlist : si un proxy a ajouté une DEUXIÈME ligne X-Forwarded-For au lieu de
    # compléter la première, get() ne lirait que la première, celle du visiteur
    # (donc falsifiable). On recolle toutes les lignes dans l'ordre.
    entete = ", ".join(request.headers.getlist("x-forwarded-for"))
    if not entete:
        return ip_connexion

    ips = [morceau.strip() for morceau in entete.split(",") if morceau.strip()]
    try:
        return ips[xff_position]
    except IndexError:
        return ip_connexion
