"""Tests de app/documents.py. Les cas particuliers utilisent un dossier temporaire (tmp_path)."""

import os

import pytest

from app.documents import DOSSIER_DATA, NOMS_FICHIERS, charger_documents


def creer_fichiers(dossier, contenus):
    """Crée les 3 fichiers attendus dans `dossier`, avec un contenu par défaut sauf indication."""
    for nom in NOMS_FICHIERS:
        texte = contenus.get(nom, f"# Contenu de {nom}")
        (dossier / nom).write_text(texte, encoding="utf-8")


# --- Vrais fichiers de data/ ---


def test_charge_les_trois_vrais_documents():
    documents = charger_documents()
    assert [doc["source"] for doc in documents] == ["cv.md", "faq.md", "projets.md"]
    for doc in documents:
        assert doc["contenu"] != ""


def test_noms_de_fichiers_casse_exacte():
    # Windows ignore la casse (Cv.md == cv.md) mais pas Linux (Render).
    # os.listdir renvoie les vrais noms, ce qui permet de détecter l'erreur dès maintenant.
    noms_reels = os.listdir(DOSSIER_DATA)
    for nom in NOMS_FICHIERS:
        assert nom in noms_reels


# --- Commentaires HTML ---


def test_commentaire_une_ligne_retire(tmp_path):
    creer_fichiers(tmp_path, {"cv.md": "Avant <!-- note privée --> après"})
    cv = charger_documents(tmp_path)[0]["contenu"]
    assert cv == "Avant  après"


def test_commentaire_multiligne_retire(tmp_path):
    creer_fichiers(tmp_path, {"cv.md": "Début\n<!--\nligne 1\nligne 2\n-->\nFin"})
    cv = charger_documents(tmp_path)[0]["contenu"]
    assert "ligne 1" not in cv
    assert "Début" in cv and "Fin" in cv


def test_texte_entre_deux_commentaires_conserve(tmp_path):
    # Vérifie le ".*?" non gourmand : le texte entre les deux commentaires doit rester.
    creer_fichiers(tmp_path, {"cv.md": "<!-- a --> Texte important <!-- b -->"})
    cv = charger_documents(tmp_path)[0]["contenu"]
    assert cv == "Texte important"


def test_commentaire_non_ferme_refuse(tmp_path):
    creer_fichiers(tmp_path, {"faq.md": "Texte <!-- jamais fermé"})
    with pytest.raises(ValueError, match="faq.md"):
        charger_documents(tmp_path)


# --- Encodage, fichiers manquants ou vides ---


def test_accents_preserves(tmp_path):
    creer_fichiers(tmp_path, {"projets.md": "Projet réalisé à Nîmes : ça marche, où ? maïs"})
    projets = charger_documents(tmp_path)[2]["contenu"]
    assert projets == "Projet réalisé à Nîmes : ça marche, où ? maïs"


def test_fichier_manquant(tmp_path):
    creer_fichiers(tmp_path, {})
    (tmp_path / "faq.md").unlink()
    with pytest.raises(FileNotFoundError, match="faq.md"):
        charger_documents(tmp_path)


@pytest.mark.parametrize("texte", ["", "   \n\n", "<!-- seulement un commentaire -->"])
def test_fichier_vide_refuse(tmp_path, texte):
    creer_fichiers(tmp_path, {"projets.md": texte})
    with pytest.raises(ValueError, match="projets.md"):
        charger_documents(tmp_path)
