#!/usr/bin/env python3
"""Assemble `socle/resumes_debats.json` à partir des résumés écrits en lots.

Deuxième moitié de la chaîne des résumés de débats :

    faits_pour_resumes.py        récolte les paroles, groupe par groupe
    (une IA, ou une personne)    écrit au plus 4 arguments par groupe
    assembler_resumes.py         contrôle, ajoute les positions de vote, range

Ce programme ne rédige rien. Il vérifie, ajoute ce que la rédaction ne doit pas
décider, et refuse une entrée qui ne tient pas la forme.

    ./assembler_resumes.py --lots /tmp/debats/lot*.json --origine ia \
        [--modele <identifiant>] [--date 2026-09-19]

**La position de vote de chaque groupe est relevée ici, dans les fichiers
publiés — jamais reprise du lot.** C'est la garantie mécanique de la règle du
projet : une phrase d'orateur ne décide pas d'un vote affiché. Un lot qui
prétendrait qu'un groupe a voté pour n'a aucun effet ; seul le scrutin compte.

Forme attendue d'un lot :

    {"DLR5L17N51349": {"EPR": ["premier argument", "deuxième"],
                       "RN":  ["…"]}}

Un groupe qui a parlé sans voter garde ses arguments, sans position. Un groupe
qui a voté sans parler n'apparaît pas : le résumé dit ce qui a été dit.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import pathlib
import sys

RACINE = pathlib.Path(__file__).resolve().parents[2]
CIBLE = RACINE / "socle" / "resumes_debats.json"
PUBLIE = RACINE / "socle" / "public"

# Quatre arguments par groupe au plus : au-delà, ce n'est plus un résumé.
ARGUMENTS_MAX = 4
# Un argument est une phrase, pas un paragraphe.
CARACTERES_MAX = 240
# Les quatre positions que le socle calcule sur le décompte d'un groupe, plus
# « aucun_vote » pour un groupe présent au scrutin dont personne n'a voté. Un
# groupe absent du scrutin garde une position vide : ce n'est pas la même
# chose, et l'écran ne doit pas les confondre.
POSITIONS = ("pour", "contre", "abstention", "partagé")

LISEZMOI = (
    "Le résumé des débats d'un texte, tel qu'il s'affiche en tête de l'onglet "
    "« Débats » : les groupes rangés par ce qu'ils ont voté, et au plus quatre "
    "arguments par groupe, tirés de ses prises de parole. C'est la SECONDE "
    "rubrique écrite par une IA — l'autre étant la description d'un texte — et "
    "l'exception est décidée dans docs/CE-QUE-L-ON-ECRIT.md. D'où le champ "
    "`origine`, affiché à l'écran. **La position de vote n'est jamais écrite "
    "par la rédaction** : elle est relevée dans le scrutin publié par "
    "assembler_resumes.py. Les débats complets restent affichés en dessous, "
    "mot pour mot. Un texte absent de ce fichier n'affiche aucun résumé, "
    "plutôt qu'un cadre vide. Régénérer : .claude/scripts/faits_pour_resumes.py "
    "puis .claude/scripts/assembler_resumes.py.")


def vote_decisif(uid: str) -> dict | None:
    """Le scrutin sur l'ensemble le plus récent, lu dans le fichier publié."""
    fichier = PUBLIE / "textes" / f"{uid}.json"
    if not fichier.exists():
        return None
    texte = json.loads(fichier.read_text(encoding="utf-8"))
    sur_ensemble = [v for v in (texte.get("votes") or [])
                    if v.get("portee") == "ensemble"]
    if not sur_ensemble:
        return None
    return sorted(sur_ensemble, key=lambda v: v.get("date") or "")[-1]


def paroles_publiees(uid: str) -> dict[str, int]:
    """Combien de prises de parole par groupe — pour refuser un groupe muet.

    L'ordre du fichier est celui de l'hémicycle : il sert de rang de secours
    quand le texte n'a pas de scrutin sur l'ensemble.
    """
    fichier = PUBLIE / "paroles" / f"{uid}.json"
    if not fichier.exists():
        return {}
    d = json.loads(fichier.read_text(encoding="utf-8"))
    return {g["sigle"]: g.get("paroles", 0) for g in (d.get("groupes") or [])}


def controler(uid: str, ecrit: dict, refus: list[str]) -> dict | None:
    vote = vote_decisif(uid)
    # Présent au scrutin et sans position : personne n'y a voté dans ce groupe.
    positions = {g["sigle"]: (g.get("position")
                              if g.get("position") in POSITIONS else "aucun_vote")
                 for g in (vote or {}).get("groupes", [])}
    dit = paroles_publiees(uid)

    groupes = []
    for sigle, arguments in ecrit.items():
        if sigle not in dit:
            refus.append(f"{uid} / {sigle} : ce groupe n'a pas parlé sur ce texte")
            continue
        propres = [a.strip() for a in (arguments or []) if a and a.strip()]
        if not propres:
            refus.append(f"{uid} / {sigle} : aucun argument")
            continue
        if len(propres) > ARGUMENTS_MAX:
            refus.append(f"{uid} / {sigle} : {len(propres)} arguments, "
                         f"{ARGUMENTS_MAX} au plus")
            continue
        trop_long = [a for a in propres if len(a) > CARACTERES_MAX]
        if trop_long:
            refus.append(f"{uid} / {sigle} : un argument dépasse "
                         f"{CARACTERES_MAX} caractères")
            continue
        groupes.append({"sigle": sigle,
                        # Relevée dans le scrutin, jamais dans le lot.
                        "position": positions.get(sigle),
                        "arguments": propres})

    if not groupes:
        refus.append(f"{uid} : aucun groupe retenu")
        return None
    # L'ordre de l'hémicycle : celui du scrutin quand il existe, sinon celui
    # du fichier des paroles, qui est déjà rangé de la gauche à la droite. Sans
    # ce secours, un texte sans scrutin affichait ses groupes par ordre
    # alphabétique — « DR, Dem, EPR », qui ne veut rien dire.
    rangs = {g["sigle"]: g.get("rang", 99) for g in (vote or {}).get("groupes", [])}
    if not rangs:
        rangs = {sigle: i for i, sigle in enumerate(dit)}
    groupes.sort(key=lambda g: (rangs.get(g["sigle"], 99), g["sigle"]))
    return {
        "vote": ({"date": vote.get("date"), "sort": vote.get("sort"),
                  "objet": vote.get("objet")} if vote else None),
        "groupes": groupes,
    }


def main(argv: list[str] | None = None) -> int:
    a = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--lots", nargs="+", required=True,
                   help="fichiers de résumés écrits (motifs acceptés)")
    a.add_argument("--origine", choices=("ia", "humain"), required=True)
    a.add_argument("--modele", help="le modèle qui a écrit, quand on le connaît")
    a.add_argument("--date", default=dt.date.today().isoformat())
    o = a.parse_args(argv)

    chemins = [pathlib.Path(x) for motif in o.lots for x in sorted(glob.glob(motif))]
    if not chemins:
        sys.exit("aucun lot trouvé")

    ancien = {}
    if CIBLE.exists():
        ancien = json.loads(CIBLE.read_text(encoding="utf-8")).get("resumes") or {}

    refus: list[str] = []
    retenus = dict(ancien)
    for chemin in chemins:
        lot = json.loads(chemin.read_text(encoding="utf-8"))
        for uid, ecrit in lot.items():
            if uid.startswith("_"):
                continue
            corps = controler(uid, ecrit, refus)
            if corps:
                retenus[uid] = {**corps, "origine": o.origine, "le": o.date,
                                "modele": o.modele or None}

    CIBLE.write_text(json.dumps(
        {"_lisezmoi": LISEZMOI,
         "_origines": {"ia": "écrite par une intelligence artificielle",
                       "humain": "écrite par une personne"},
         "resumes": retenus}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")

    for r in refus:
        print(f"  refusé : {r}", file=sys.stderr)
    nouveaux = len(retenus) - len(ancien)
    print(f"{len(retenus)} résumés dans {CIBLE.relative_to(RACINE)} "
          f"({nouveaux} de plus), {len(refus)} refus", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
