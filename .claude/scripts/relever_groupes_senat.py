#!/usr/bin/env python3
"""Régénère `socle/groupes_senat.json` — le secours des couleurs du Sénat.

**Ce fichier est un filet, pas la source.** La publication lit chaque jour la
page des groupes politiques du Sénat ; ce fichier ne sert que les jours où elle
ne se lit pas. Le 2026-10-05, le Sénat en a retiré l'élément qui portait les
couleurs, et sans le filet l'hémicycle du Sénat s'affichait tout gris.

À relancer **quand la page redonne l'information** — après un renouvellement,
ou quand un groupe change de couleur :

    ./relever_groupes_senat.py                        # depuis la page, en ligne
    ./relever_groupes_senat.py page.html --le 2026-10-04   # d'une copie prise ce jour-là

`--le` dit **quand la page a été prise**, pas quand on la relit : relever
aujourd'hui une copie d'hier doit porter la date d'hier, sans quoi le fichier
se donne pour plus frais qu'il n'est.

Il refuse d'écrire un fichier plus pauvre que celui qu'il remplace : une page
à moitié lue ne doit pas effacer un relevé complet.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

RACINE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "socle"))

import senat                                                   # noqa: E402
import recuperer_senat                                         # noqa: E402

SORTIE = RACINE / "socle" / "groupes_senat.json"

POURQUOI = (
    "Les couleurs et les noms complets des groupes du Sénat, relevés sur sa "
    "page des groupes politiques par senat.groupes_de_la_page. Ce fichier est "
    "un SECOURS : la page reste la source, et la publication la relit chaque "
    "jour. Le 2026-10-05, le Sénat a retiré de cette page l'élément qui les "
    "portait — sans ce filet, l'hémicycle du Sénat s'affichait tout gris. Rien "
    "ici n'est écrit à la main : le fichier se régénère avec "
    ".claude/scripts/relever_groupes_senat.py.")


def main() -> int:
    args = sys.argv[1:]
    le = dt.date.today().isoformat()
    if "--le" in args:
        i = args.index("--le")
        le = args[i + 1]
        dt.date.fromisoformat(le)                # refuse une date mal écrite
        del args[i:i + 2]

    if args:
        page = pathlib.Path(args[0]).read_text(encoding="utf-8", errors="replace")
        d_ou = args[0]
    else:
        page = recuperer_senat.lire_url(senat.URL_GROUPES)
        d_ou = senat.URL_GROUPES

    groupes = senat.groupes_de_la_page(page)
    souci = senat.groupes_lisibles(groupes)
    if souci:
        print(f"Rien écrit — {souci}", file=sys.stderr)
        print(f"  lu sur : {d_ou}", file=sys.stderr)
        return 1

    # Un relevé ne doit jamais appauvrir celui qu'il remplace.
    if SORTIE.exists():
        avant = json.loads(SORTIE.read_text(encoding="utf-8")).get("groupes", {})
        if len(groupes) < len(avant):
            print(f"Rien écrit — {len(groupes)} groupes lus, contre "
                  f"{len(avant)} dans le fichier actuel.", file=sys.stderr)
            return 1

    SORTIE.write_text(json.dumps({
        "_lu_le": le,
        "_source": senat.URL_GROUPES,
        "_pourquoi": POURQUOI,
        "groupes": {c: groupes[c] for c in sorted(groupes)},
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(groupes)} groupes écrits dans {SORTIE.relative_to(RACINE)}")
    for sigle in sorted(groupes):
        print(f"  {sigle:6} {groupes[sigle]['couleur']}  {groupes[sigle]['nom']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
