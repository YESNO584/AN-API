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

Forme attendue d'une entrée :

    {"uid": "DLR5L17N53980",
     "contexte": "un seul paragraphe, ce qui se passait avant le texte",
     "accroche": "la phrase qui dit ce que le texte décide",
     "points": ["une mesure", "une autre"],
     "nomUsage": "Ripost"}

**Le nom d'usage n'est pas cru sur parole.** Un texte que tout le monde appelle
« la loi Ripost » ne porte ce nom nulle part dans la source : il est dans la
bouche des orateurs. Le programme le cherche donc lui-même dans les prises de
parole publiées, et **refuse un nom qu'il n'y trouve pas** au moins trois fois
— ou, à défaut de débats publiés, dans le titre ou la formule du texte. La
rédaction propose, la source tranche : c'est la même règle que pour les
positions de vote des résumés de débats.

**Ce contrôle a une limite, et elle est grande : il prouve que le mot a été
prononcé, pas qu'il nomme CE texte.** Un débat cite les lois d'avant. Mesuré le
2026-09-19 sur les 172 textes qui ont des débats publiés : 26 candidats du type
« loi X » prononcés au moins trois fois, dont **3 seulement** nomment le texte
en discussion — « Ripost », « Duplomb » et « Ddadue ». Les 23 autres sont des
lois citées : « la loi PLM a été imaginée par Gaston Defferre », « la loi
Letchimy, que nous connaissons depuis 2018 en outre-mer », « la loi Aper de
2023 ». Seule la phrase qui entoure le mot tranche, et c'est à la rédaction de
la lire.

**Les lots s'ajoutent à ce qui existe déjà**, ils ne le remplacent pas. Une
entrée réécrite écrase la sienne, les autres restent. Sans cela, ajouter un
contexte à dix textes effacerait les quatre-vingt-dix-sept autres.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys
import unicodedata

RACINE = pathlib.Path(__file__).resolve().parents[2]
CIBLE = RACINE / "socle" / "descriptions.json"

RACINE_PUBLIE = RACINE / "socle" / "public"

# Une accroche plus courte ne dit rien ; plus longue, ce n'est plus une
# accroche mais un paragraphe, et la liste en dessous perd son intérêt.
ACCROCHE_MIN, ACCROCHE_MAX = 40, 320
POINT_MIN, POINT_MAX = 15, 260
POINTS_MAX = 8
# Le contexte est **un paragraphe, au plus** : ce qui se passait avant le
# texte, et rien de plus. Plus court, il ne pose rien ; plus long, il devient
# un article et repousse sous le pli ce que le texte décide. Un saut de ligne
# y est refusé — c'est la marque d'un second paragraphe.
CONTEXTE_MIN, CONTEXTE_MAX = 80, 420
# Combien de fois un nom d'usage doit être prononcé en séance pour qu'on le
# tienne pour un usage, et non pour un mot lâché une fois.
CITATIONS_MIN = 3

LISEZMOI = (
    "La description d'un texte, telle qu'elle s'affiche en haut de sa fiche : "
    "un contexte d'un paragraphe au plus, une accroche d'une phrase, puis une "
    "puce par mesure concrète — et le nom d'usage du texte quand il en a un. "
    "`nomUsage.citations` dit combien de fois ce nom est prononcé dans les "
    "débats publiés ; il est compté par assembler_descriptions.py, jamais "
    "écrit par la rédaction, et un nom introuvable est refusé. C'est la "
    "PREMIÈRE des deux rubriques écrites par une IA — l'autre étant le résumé "
    "des débats — et l'une des deux seules données du projet qui ne viennent "
    "pas d'une source publique. D'où le champ `origine`, affiché à l'écran. "
    "L'exception est décidée dans docs/CE-QUE-L-ON-ECRIT.md. "
    "Une entrée peut être écrite par une personne : mettre alors `origine` à "
    "« humain ». `modele` nomme le modèle qui a écrit, quand on le connaît ; "
    "il reste vide sinon, et la fiche se tait alors plutôt que d'annoncer un "
    "vide. Un texte absent de ce fichier n'affiche aucune description, plutôt "
    "qu'un cadre vide. Régénérer : .claude/scripts/faits_pour_descriptions.py "
    "puis .claude/scripts/assembler_descriptions.py."
)


def sans_accent(mot: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", mot.lower())
                   if unicodedata.category(c) != "Mn")


def citations(uid: str, nom: str) -> int | None:
    """Combien de fois ce nom est prononcé en séance, d'après les publiés.

    None quand rien n'est publié pour ce texte : on ne peut alors ni confirmer
    ni infirmer, et l'entrée est refusée plutôt que crue.
    """
    # « la loi Ripost » se cherche sur « Ripost » : c'est le mot qui identifie.
    distinctif = sans_accent(nom)
    for mot in ("la loi ", "le projet de loi ", "la proposition de loi ",
                "loi ", "texte "):
        if distinctif.startswith(mot):
            distinctif = distinctif[len(mot):]
    distinctif = distinctif.strip(" «»\"'")
    if len(distinctif) < 3:
        return 0

    trouve = None
    paroles = RACINE_PUBLIE / "paroles" / f"{uid}.json"
    if paroles.exists():
        d = json.loads(paroles.read_text(encoding="utf-8"))
        tout = sans_accent(" ".join(p.get("texte") or "" for p in (d.get("paroles") or [])))
        # Mot entier : sans cela « Ripost » se compterait dans « riposte », et
        # le contrôle dirait oui pour un nom que personne n'a prononcé.
        trouve = len(re.findall(rf"\b{re.escape(distinctif)}\b", tout))
    # Pas de débats publiés : le titre ou la formule du texte peuvent porter le
    # nom. Un texte qui s'appelle « loi Egalim » le dit dans son intitulé.
    texte = RACINE_PUBLIE / "textes" / f"{uid}.json"
    if texte.exists():
        d = json.loads(texte.read_text(encoding="utf-8"))
        entete = sans_accent((d.get("titre") or "") + " " + (d.get("formule") or ""))
        if re.search(rf"\b{re.escape(distinctif)}\b", entete):
            return max(trouve or 0, CITATIONS_MIN)
    return trouve


def reproches(uid: str, entree: dict) -> list[str]:
    """Ce qui empêche de publier cette entrée. Liste vide : elle est bonne."""
    ennuis = []
    contexte = (entree.get("contexte") or "").strip()
    if contexte:
        if not CONTEXTE_MIN <= len(contexte) <= CONTEXTE_MAX:
            ennuis.append(f"contexte de {len(contexte)} caractères")
        if "\n" in contexte:
            ennuis.append("contexte en plusieurs paragraphes")
    nom = (entree.get("nomUsage") or "").strip()
    if nom:
        combien = citations(uid, nom)
        if combien is None or combien < CITATIONS_MIN:
            ennuis.append(f"nom d'usage « {nom} » introuvable dans les publiés"
                          f" ({combien if combien is not None else 0} fois,"
                          f" {CITATIONS_MIN} au moins)")
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

    # Les lots s'ajoutent à ce qui existe : voir le docstring.
    entrees: dict[str, dict] = {}
    if args.cible.exists():
        entrees = json.loads(args.cible.read_text(encoding="utf-8")).get("descriptions") or {}
    avant = len(entrees)
    ecrites: set[str] = set()
    refusees: list[tuple[str, list[str]]] = []
    for lot in args.lots:
        for entree in json.loads(lot.read_text(encoding="utf-8")):
            uid = entree.get("uid")
            if not uid:
                refusees.append((f"({lot.name}, sans uid)", ["pas d'uid"]))
                continue
            if uid in ecrites:
                refusees.append((uid, ["écrite deux fois"]))
                continue
            ennuis = reproches(uid, entree)
            if ennuis:
                refusees.append((uid, ennuis))
                continue
            nom = (entree.get("nomUsage") or "").strip()
            entrees[uid] = {
                **({"contexte": entree["contexte"].strip()}
                   if (entree.get("contexte") or "").strip() else {}),
                "accroche": entree["accroche"].strip(),
                "points": [p.strip() for p in (entree.get("points") or []) if p.strip()],
                # Le compte est relevé ici, jamais écrit par la rédaction.
                **({"nomUsage": {"nom": nom, "citations": citations(uid, nom)}}
                   if nom else {}),
                "origine": args.origine,
                "le": args.date,
                **({"modele": args.modele} if args.modele else {}),
            }
            ecrites.add(uid)

    args.cible.write_text(json.dumps({
        "_lisezmoi": LISEZMOI,
        "_origines": {"ia": "écrite par une intelligence artificielle",
                      "humain": "écrite par une personne"},
        "descriptions": entrees,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    sans_points = sum(1 for e in entrees.values() if not e["points"])
    total_points = sum(len(e["points"]) for e in entrees.values())
    avec_contexte = sum(1 for e in entrees.values() if e.get("contexte"))
    avec_nom = sum(1 for e in entrees.values() if e.get("nomUsage"))
    print(f"{len(entrees)} descriptions dans {args.cible} "
          f"({len(entrees) - avant} de plus, {len(ecrites)} réécrites)")
    print(f"  {total_points} points, {sans_points} description(s) sans point")
    print(f"  {avec_contexte} avec un contexte, {avec_nom} avec un nom d'usage")
    print(f"  modèle : {args.modele or 'non renseigné'}")
    for uid, ennuis in refusees:
        print(f"  REFUSÉE {uid} : {', '.join(ennuis)}", file=sys.stderr)
    return 1 if refusees else 0


if __name__ == "__main__":
    sys.exit(main())
