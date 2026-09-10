#!/usr/bin/env python3
"""Ce que chaque loi décide, tiré du texte réel de ses articles.

Écrire la description d'une loi à partir de son titre donne une phrase creuse :
« Projet de loi portant diverses dispositions d'adaptation au droit de l'Union
européenne » ne dit rien. La matière est un niveau plus bas — dans le texte des
articles — et les fichiers publiés la portent :

    changements/<uid>.json          la liste des articles, sans texte
    changements/<uid>/<id>.json     un article, avec son texte découpé en
                                    morceaux « égal », « retiré », « ajouté »

**Les morceaux « ajouté » sont l'or de ce fichier** : ce sont, mot pour mot,
les phrases que la loi écrit dans le droit. Un article que la loi a écrit pour
elle-même n'a pas d'avant : tout son texte est nouveau.

Ce programme rassemble ces extraits, une loi par fichier, pour qu'une
description soit écrite à partir de ce que la loi dit et non de son intitulé.
Il ne rédige rien : il récolte.

    ./faits_pour_descriptions.py --sortie /tmp/faits [--lois 2026-813,2025-127]

Comment il échantillonne une grande loi — la loi de finances pour 2025 touche
1 053 articles, qu'on ne lit pas :
  — d'abord les articles que la loi a écrits elle-même, les plus longs en tête,
    parce qu'ils portent son droit propre ;
  — puis les articles de code les plus réécrits (part commune la plus faible),
    parce qu'un article changé à 80 % dit un vrai changement, là où un article
    changé à 2 % est souvent une référence corrigée.
Le fichier de sortie dit toujours combien d'articles ont été lus sur combien.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.error
import urllib.request

SOCLE = "https://yesno584.github.io/AN-API"
# Assez d'articles pour reconnaître ce que fait une loi, assez peu pour qu'une
# loi de finances ne noie pas les autres.
ARTICLES_MAX = 10
# De quoi lire une disposition entière sans recopier un tableau de recettes.
EXTRAIT_MAX = 1200


def lire(url: str):
    with urllib.request.urlopen(url, timeout=60) as reponse:
        return json.load(reponse)


def a_retenir(liste: dict) -> list[dict]:
    """Les articles à lire, les plus porteurs de sens d'abord."""
    ajouts = sorted(liste.get("articlesAjoutes") or [],
                    key=lambda a: -(a.get("mots") or 0))
    changes = [a for g in (liste.get("groupes") or []) for a in g["articles"]]
    # `commun` est la part de texte inchangée : plus elle est basse, plus la
    # loi a réécrit. None veut dire « pas de rédaction d'avant » — donc neuf.
    changes.sort(key=lambda a: (a.get("commun") if a.get("commun") is not None else -1,
                                -(a.get("mots") or 0)))
    # Moitié-moitié, et chaque moitié rend ce qu'elle n'utilise pas. Prendre
    # tous les articles propres d'abord paraissait juste, mais la loi 2026-813
    # l'a démenti : ses deux articles propres ne disent que « entre en vigueur
    # à la rentrée » et « déclaré non conforme », pendant que la vraie mesure
    # est dans un article du code de l'éducation réécrit à 19 %.
    moitie = ARTICLES_MAX // 2
    pris_ajouts = ajouts[:max(moitie, ARTICLES_MAX - len(changes))]
    pris_changes = changes[:ARTICLES_MAX - len(pris_ajouts)]
    retenus, vus = [], set()
    for a in pris_ajouts + pris_changes:
        if a["id"] in vus:
            continue
        vus.add(a["id"])
        retenus.append(a)
    return retenus


def extrait(article: dict) -> dict:
    """Ce qu'un article apporte, en clair : le texte neuf, et ce qu'il retire."""
    morceaux = article.get("morceaux") or []
    fond = [m for m in morceaux if not m.get("forme")]
    ajoute = " ".join(m["texte"] for m in fond if m["role"] == "ajoute")
    retire = " ".join(m["texte"] for m in fond if m["role"] == "retire")
    entier = " ".join(m["texte"] for m in morceaux if m["role"] != "retire")
    return {
        "ou": article.get("ou"),
        "numero": article.get("numero"),
        "action": article.get("action"),
        "effet": article.get("effet"),
        "partChangee": (100 - article["commun"]) if article.get("commun") is not None else None,
        # Un article neuf n'a pas de « texte ajouté » distinct de lui-même.
        "ajoute": (ajoute or entier)[:EXTRAIT_MAX],
        "retire": retire[:EXTRAIT_MAX] or None,
        "nota": (article.get("nota") or None),
    }


def faits_d_une_loi(uid: str, entete: dict) -> dict:
    liste = lire(f"{SOCLE}/changements/{uid}.json")
    retenus = a_retenir(liste)
    articles = []
    for a in retenus:
        try:
            articles.append(extrait(lire(f"{SOCLE}/changements/{uid}/{a['id']}.json")))
        except (urllib.error.URLError, json.JSONDecodeError) as erreur:
            print(f"  {uid}/{a['id']} illisible : {erreur}", file=sys.stderr)
    total = len(liste.get("articlesAjoutes") or []) + sum(
        len(g["articles"]) for g in (liste.get("groupes") or []))
    return {
        **entete,
        "loi": liste.get("loi"),
        "articlesEnTout": total,
        "articlesLus": len(articles),
        "codesTouches": [{"ou": g["ou"], "articles": len(g["articles"])}
                         for g in (liste.get("groupes") or [])],
        "articles": articles,
    }


def main() -> int:
    global SOCLE
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sortie", required=True, type=pathlib.Path)
    ap.add_argument("--lois", help="numéros de loi, séparés par des virgules ;"
                                   " par défaut, toutes les lois promulguées")
    ap.add_argument("--socle", default=SOCLE)
    args = ap.parse_args()

    SOCLE = args.socle.rstrip("/")
    args.sortie.mkdir(parents=True, exist_ok=True)

    voulues = set((args.lois or "").split(",")) if args.lois else None
    promulguees = lire(f"{SOCLE}/promulgues.json")["textes"]
    ecrits = 0
    for t in promulguees:
        if voulues and t.get("loiNumero") not in voulues:
            continue
        entete = {"uid": t["uid"], "titre": t["titre"], "type": t["type"],
                  "loiDate": t.get("loiDate")}
        try:
            faits = faits_d_une_loi(t["uid"], entete)
        except (urllib.error.URLError, KeyError, json.JSONDecodeError) as erreur:
            print(f"{t['uid']} sans changements lisibles : {erreur}", file=sys.stderr)
            faits = {**entete, "loi": t.get("loiNumero"), "articlesEnTout": 0,
                     "articlesLus": 0, "codesTouches": [], "articles": []}
        (args.sortie / f"{t['uid']}.json").write_text(
            json.dumps(faits, ensure_ascii=False, indent=1), encoding="utf-8")
        ecrits += 1
        print(f"  {faits['loi']:>10}  {faits['articlesLus']:>2}/{faits['articlesEnTout']:<5}"
              f"  {t['titre'][:60]}")
    print(f"{ecrits} lois écrites dans {args.sortie}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
