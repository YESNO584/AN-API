"""Ce que tous les morceaux de la publication partagent : les chemins, l'écriture d'un fichier, le classement des noms.
"""
from __future__ import annotations

import json
import pathlib
import unicodedata


# `socle/`, et non ce sous-dossier : les bases et les fichiers publiés y
# vivent. Calculé depuis ce fichier, un déménagement le décalerait d'un
# cran sans erreur — c'est arrivé le jour du découpage.
RACINE = pathlib.Path(__file__).resolve().parents[1]


BASE = RACINE / "parlement.db"


BASE_LEGI = RACINE / "legi.db"


SORTIE = RACINE / "public"


DESCRIPTIONS = RACINE / "descriptions.json"


RESUMES_DEBATS = RACINE / "resumes_debats.json"


MAQUETTE = RACINE.parent / "maquette" / "feed.html"


def ecrire(chemin: pathlib.Path, contenu, brut: bytes | None = None) -> int:
    """Écrit du JSON, ou des octets tels quels si `brut` est fourni."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if brut is None:
        brut = json.dumps(contenu, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    chemin.write_bytes(brut)
    return len(brut)


def sans_accent(mot: str | None) -> str:
    """Pour classer des noms, pas pour les afficher : l'affiché reste intact."""
    decompose = unicodedata.normalize("NFD", mot or "")
    return "".join(c for c in decompose if not unicodedata.combining(c)).casefold()


BASE_SENAT = RACINE / "senat.db"
