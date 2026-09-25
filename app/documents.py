"""Chargement des documents Markdown de data/ (la base de connaissances du chatbot)."""

import re
from pathlib import Path

# Dossier data/ calculé depuis l'emplacement de ce fichier (app/documents.py),
# pour que le chemin soit juste quel que soit le dossier d'où l'on lance le serveur.
DOSSIER_DATA = Path(__file__).resolve().parent.parent / "data"

# Noms exacts, en minuscules : Render tourne sous Linux, sensible à la casse.
# Liste fixe (pas de "*.md") pour qu'aucun fichier ajouté par erreur n'entre dans le prompt.
NOMS_FICHIERS = ("cv.md", "faq.md", "projets.md")

# Commentaire HTML <!-- ... -->. ".*?" s'arrête au PREMIER "-->" (non gourmand),
# re.DOTALL permet au "." de couvrir aussi les retours à la ligne (commentaires multilignes).
COMMENTAIRE_HTML = re.compile(r"<!--.*?-->", re.DOTALL)


def retirer_commentaires_html(texte: str, source: str) -> str:
    """Retire les commentaires HTML. Lève ValueError si un "<!--" n'est jamais fermé."""
    nettoye = COMMENTAIRE_HTML.sub("", texte)
    # S'il reste un "<!--", c'est qu'il n'avait pas de "-->" : on refuse plutôt que
    # d'envoyer à Claude une note peut-être privée.
    if "<!--" in nettoye:
        raise ValueError(f'{source} contient un commentaire "<!--" non fermé.')
    return nettoye


def charger_documents(dossier: Path = DOSSIER_DATA) -> list[dict]:
    """Lit les fichiers de NOMS_FICHIERS et renvoie [{"source": ..., "contenu": ...}, ...].

    Lève FileNotFoundError si un fichier manque, ValueError s'il est vide
    ou contient un commentaire non fermé : mieux vaut un crash visible au
    démarrage qu'un chatbot sans connaissances.
    """
    documents = []
    for nom in NOMS_FICHIERS:
        chemin = dossier / nom
        if not chemin.is_file():
            raise FileNotFoundError(f"Document introuvable : {nom} (cherché ici : {chemin})")

        # encoding="utf-8" obligatoire : sous Windows, Python utiliserait sinon
        # l'encodage du système et abîmerait les accents.
        texte = chemin.read_text(encoding="utf-8")
        contenu = retirer_commentaires_html(texte, nom).strip()
        if contenu == "":
            raise ValueError(f"Le document {nom} est vide.")

        documents.append({"source": nom, "contenu": contenu})
    return documents
