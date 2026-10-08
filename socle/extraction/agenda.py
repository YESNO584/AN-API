"""L'agenda de l'Assemblée : les moments de séance qui ne portent sur aucun texte — questions au Gouvernement, débats — et que seul l'agenda publie.
"""
from __future__ import annotations

import pathlib
from typing import Iterator
from extraction.archives import _lire


# Les points d'ordre du jour retenus, par leur type tel que la source l'écrit,
# et le genre sous lequel le calendrier les range. **Ce sont les seuls points
# qu'aucun dossier ne porte** : une discussion de texte est déjà dans le
# parcours de son dossier, et la reprendre ici la doublerait. Les questions
# orales sans débat, les votes solennels, les ouvertures de session ne sont
# pas retenus — choix d'affichage du 2026-10-08, pas une limite de la source.
GENRES_HORS_TEXTE = {
    "Questions au Gouvernement": "questions",
    "Débat d'initiative parlementaire": "debat",
    "Déclaration du Gouvernement suivie d'un débat": "debat",
}

# **L'archive porte aussi les séances du Sénat** : 148 sur 1 111 le
# 2026-10-08, avec leurs propres questions au Gouvernement. Une séance de
# l'Assemblée se reconnaît à la structure de son identifiant (`RUAN…`), pas à
# l'organe qui la tient, dont le numéro change à chaque législature.
PREFIXE_SEANCE_AN = "RUAN"
CONFIRME = "Confirmé"


def _liste(x) -> list:
    return [] if x is None else (x if isinstance(x, list) else [x])


def _heure(horodatage: str) -> str | None:
    """« 15 h 00 », comme la précision d'une étape du parcours."""
    h = (horodatage or "")[11:16]
    return f"{h[:2]} h {h[3:]}" if len(h) == 5 else None


def points_hors_texte(reunion: dict) -> list[dict]:
    """Les questions et les débats d'une réunion, s'ils ont bien lieu.

    Une séance « Supprimée » n'a pas eu lieu, et un point « Supprimé » d'une
    séance tenue a été retiré ou reporté : ni l'un ni l'autre n'entre. Rien
    n'est rédigé ici — `objet` est l'intitulé de la source, mot pour mot.
    """
    uid = reunion.get("uid") or ""
    if (reunion.get("@xsi:type") != "seance_type"
            or not uid.startswith(PREFIXE_SEANCE_AN)
            or (reunion.get("cycleDeVie") or {}).get("etat") != CONFIRME):
        return []
    debut = reunion.get("timeStampDebut") or ""
    points = []
    for p in _liste(((reunion.get("ODJ") or {}).get("pointsODJ") or {}).get("pointODJ")):
        genre = GENRES_HORS_TEXTE.get(p.get("typePointODJ"))
        if not genre or (p.get("cycleDeVie") or {}).get("etat") != CONFIRME:
            continue
        points.append({
            "seance": uid, "point": p.get("uid"), "date": debut[:10],
            "heure": _heure(debut), "genre": genre,
            "type": p.get("typePointODJ"), "objet": (p.get("objet") or "").strip(),
        })
    return points


def lire_points_hors_texte(archive: pathlib.Path) -> Iterator[dict]:
    """Tous les points de séance qui ne portent sur aucun texte, dans l'archive."""
    for brut in _lire(archive, "reunion"):
        yield from points_hors_texte(brut.get("reunion") or {})
