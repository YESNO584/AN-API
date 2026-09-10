#!/usr/bin/env python3
"""Assemble `socle/descriptions.json` à partir des descriptions écrites en lots.

Deuxième moitié de la chaîne des descriptions :

    faits_pour_descriptions.py   récolte le texte réel des articles
    (une IA, ou une personne)    écrit accroche + points, par lots
    assembler_descriptions.py    contrôle, complète et range le tout

Ce programme ne rédige rien. Il vérifie, ajoute ce que la rédaction ne peut
pas savoir — l'origine, la date, le modèle — et refuse une entrée qui ne
tient pas la forme, plutôt que de publier une description à moitié écrite.

    ./assembler_descriptions.py --lots /tmp/desc/lot*.json --origine ia \
        [--modele <identifiant>] [--date 2026-09-10]

Le modèle est **facultatif et jamais deviné** : il est écrit par qui lance le
programme. Une description rédigée par une personne n'en a pas.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

RACINE = pathlib.Path(__file__).resolve().parents[2]
CIBLE = RACINE / "socle" / "descriptions.json"

# Une accroche plus courte ne dit rien ; plus longue, ce n'est plus une
# accroche mais un paragraphe, et la liste en dessous perd son intérêt.
ACCROCHE_MIN, ACCROCHE_MAX = 40, 320
POINT_MIN, POINT_MAX = 15, 260
POINTS_MAX = 8

LISEZMOI = (
    "La description d'un texte, telle qu'elle s'affiche en haut de sa fiche : "
    "une accroche d'une phrase, puis une puce par mesure concrète. C'est la "
    "SEULE donnée du projet qui ne vienne pas d'une source publique, et la "
    "seule exception à la règle « rien n'est écrit par une IA » — d'où le "
    "champ `origine`, affiché à l'écran. Voir docs/CE-QUE-L-ON-ECRIT.md. "
    "Une entrée peut être écrite par une personne : mettre alors `origine` à "
    "« humain ». `modele` nomme le modèle qui a écrit, quand on le connaît ; "
    "il reste vide sinon, et la fiche se tait alors plutôt que d'annoncer un "
    "vide. Un texte absent de ce fichier n'affiche aucune description, plutôt "
    "qu'un cadre vide. Régénérer : .claude/scripts/faits_pour_descriptions.py "
    "puis .claude/scripts/assembler_descriptions.py."
)


def reproches(entree: dict) -> list[str]:
    """Ce qui empêche de publier cette entrée. Liste vide : elle est bonne."""
    ennuis = []
    accroche = (entree.get("accroche") or "").strip()
    if not ACCROCHE_MIN <= len(accroche) <= ACCROCHE_MAX:
        ennuis.append(f"accroche de {len(accroche)} caractères")
    for depart in ("Ce texte", "Cette loi", "La loi ", "Le texte"):
        if accroche.startswith(depart):
            ennuis.append(f"accroche qui commence par « {depart.strip()} »")
    points = entree.get("points") or []
    if len(points) > POINTS_MAX:
        ennuis.append(f"{len(points)} points")
    for point in points:
        if not POINT_MIN <= len((point or "").strip()) <= POINT_MAX:
            ennuis.append(f"point de {len((point or '').strip())} caractères")
    return ennuis


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lots", nargs="+", type=pathlib.Path, required=True,
                    help="fichiers JSON, chacun un tableau d'objets"
                         " {uid, accroche, points}")
    ap.add_argument("--origine", choices=("ia", "humain"), required=True)
    ap.add_argument("--modele", help="identifiant du modèle qui a écrit."
                                     " Facultatif, jamais deviné")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--cible", type=pathlib.Path, default=CIBLE)
    args = ap.parse_args()

    entrees: dict[str, dict] = {}
    refusees: list[tuple[str, list[str]]] = []
    for lot in args.lots:
        for entree in json.loads(lot.read_text(encoding="utf-8")):
            uid = entree.get("uid")
            if not uid:
                refusees.append((f"({lot.name}, sans uid)", ["pas d'uid"]))
                continue
            if uid in entrees:
                refusees.append((uid, ["écrite deux fois"]))
                continue
            ennuis = reproches(entree)
            if ennuis:
                refusees.append((uid, ennuis))
                continue
            entrees[uid] = {
                "accroche": entree["accroche"].strip(),
                "points": [p.strip() for p in (entree.get("points") or []) if p.strip()],
                "origine": args.origine,
                "le": args.date,
                **({"modele": args.modele} if args.modele else {}),
            }

    args.cible.write_text(json.dumps({
        "_lisezmoi": LISEZMOI,
        "_origines": {"ia": "écrite par une intelligence artificielle",
                      "humain": "écrite par une personne"},
        "descriptions": entrees,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    sans_points = sum(1 for e in entrees.values() if not e["points"])
    total_points = sum(len(e["points"]) for e in entrees.values())
    print(f"{len(entrees)} descriptions écrites dans {args.cible}")
    print(f"  {total_points} points, {sans_points} description(s) sans point")
    print(f"  modèle : {args.modele or 'non renseigné'}")
    for uid, ennuis in refusees:
        print(f"  REFUSÉE {uid} : {', '.join(ennuis)}", file=sys.stderr)
    return 1 if refusees else 0


if __name__ == "__main__":
    sys.exit(main())
