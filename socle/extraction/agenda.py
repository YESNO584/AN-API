"""L'agenda de l'Assemblée : les moments de séance que seul l'agenda publie — questions au Gouvernement, débats — et les votes solennels qu'il annonce.
"""
from __future__ import annotations

import pathlib
from typing import Iterator
from extraction.archives import _lire


# Les points d'ordre du jour retenus, par leur type tel que la source l'écrit,
# et le genre sous lequel le calendrier les range. Les trois premiers ne sont
# portés par aucun dossier. Le **vote solennel**, lui, porte souvent le lien
# vers le dossier du texte voté — 42 sur 48 le 2026-10-08 — mais **jamais
# quand il est encore à venir** : l'agenda l'annonce par son seul intitulé.
# Une discussion de texte n'est pas retenue : le parcours de son dossier la
# porte déjà. Les questions orales sans débat et les ouvertures de session non
# plus — choix d'affichage du 2026-10-08, pas une limite de la source.
GENRES_DE_L_AGENDA = {
    "Questions au Gouvernement": "questions",
    "Débat d'initiative parlementaire": "debat",
    "Déclaration du Gouvernement suivie d'un débat": "debat",
    "Vote solennel": "vote_solennel",
}

# **L'archive porte aussi les séances du Sénat** : 148 sur 1 111 le
# 2026-10-08. Elles n'y portent aujourd'hui que des discussions de textes, mais
# rien ne garantit qu'il en sera toujours ainsi. Une séance de
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


def _dossier(point: dict) -> str | None:
    """Le dossier que le point désigne lui-même — le premier s'il en désigne
    plusieurs. Rien n'est cherché par l'intitulé."""
    refs = _liste((point.get("dossiersLegislatifsRefs") or {}).get("dossierRef"))
    return refs[0] if refs else None


def points_de_seance(reunion: dict) -> list[dict]:
    """Les questions, les débats et les votes solennels d'une réunion, s'ils
    ont bien lieu.

    Une séance « Supprimée » n'a pas eu lieu, et un point « Supprimé » d'une
    séance tenue a été retiré ou reporté : ni l'un ni l'autre n'entre. Rien
    n'est rédigé ici — `objet` est l'intitulé de la source, mot pour mot, et
    `dossier` le lien qu'elle publie, quand elle en publie un.
    """
    uid = reunion.get("uid") or ""
    if (reunion.get("@xsi:type") != "seance_type"
            or not uid.startswith(PREFIXE_SEANCE_AN)
            or (reunion.get("cycleDeVie") or {}).get("etat") != CONFIRME):
        return []
    debut = reunion.get("timeStampDebut") or ""
    points = []
    for p in _liste(((reunion.get("ODJ") or {}).get("pointsODJ") or {}).get("pointODJ")):
        genre = GENRES_DE_L_AGENDA.get(p.get("typePointODJ"))
        if not genre or (p.get("cycleDeVie") or {}).get("etat") != CONFIRME:
            continue
        points.append({
            "seance": uid, "point": p.get("uid"), "date": debut[:10],
            "heure": _heure(debut), "genre": genre,
            "type": p.get("typePointODJ"), "objet": (p.get("objet") or "").strip(),
            "dossier": _dossier(p),
        })
    return points


def lire_points_de_seance(archive: pathlib.Path) -> Iterator[dict]:
    """Tous les points de séance retenus, dans l'archive."""
    for brut in _lire(archive, "reunion"):
        yield from points_de_seance(brut.get("reunion") or {})
