#!/usr/bin/env python3
"""Écrit les données de la base en fichiers tout prêts, à publier tels quels.

Pourquoi des fichiers plutôt qu'un serveur : les données ne changent qu'une
fois par jour et personne ne les modifie. Il n'y a donc rien à calculer en
direct. Des fichiers publiés quelque part suffisent — pas de machine à louer,
à surveiller ni à mettre à jour, et l'application démarre plus vite parce
qu'elle lit un fichier au lieu d'interroger un serveur.

Ce que ça produit (environ 2,5 Mo au total, 120 Ko pour la liste une fois
compressée) :

    public/etat.json              d'où viennent les données et de quand
    public/etapes.json            les six étapes du parcours, et leurs comptes
    public/textes.json            les textes en cours — le fichier principal
    public/promulgues.json        les lois déjà promulguées
    public/textes/<uid>.json      un fichier par texte, avec tout son parcours

Usage :
    ./publier.py                  # écrit dans public/
    ./publier.py --vers dossier
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import shutil
import sqlite3
import sys
import affichage
import extraction
import senat as senat_mod
from publication.amendements import AMENDEMENTS_MAX, amendements_adoptes_en_entier, amendements_du_texte, debats_par_amendement, votes_par_amendement
from publication.calendrier import calendrier
from publication.debats import lire_descriptions, lire_resumes_debats, paroles_du_texte, vu_le
from publication.listes import ARRETES, CHAMPS_LISTE, TRAVAUX, procedure_acceleree, resume_votes, signataires, votes_du_texte
from publication.loi import article_compare, articles_de_la_loi, changements_par_loi, ouvrir_legi
from publication.senat import calendrier_du_senat, composition_du_senat, ouvrir_senat, themes_par_texte, votes_du_senat
from publication.versions import articles_de_pure_forme, comparaison_des_versions, ouvrir_textes, versions_du_texte


from publication.calendrier import ecrire_calendrier
from publication.commun import BASE, MAQUETTE, SORTIE, ecrire
from publication.preparation import preparer
from publication.etat import ecrire_etapes, ecrire_etat, ecrire_groupes
from publication.fiches import ecrire_fiches
from publication.listes import ecrire_listes, ecrire_travaux
from publication.loi import ecrire_changements
from publication.senat import ecrire_senat


def publier(cx: sqlite3.Connection, sortie: pathlib.Path) -> dict[str, int]:
    """Enchaîne les étapes. **L'ordre compte à un endroit** : les listes
    s'écrivent après les fiches, parce qu'elles portent ce que seule la boucle
    des fiches sait — quelle lecture a voté quel amendement."""
    # On repart d'un dossier vide : un texte promulgué hier ne doit pas rester
    # dans la liste des textes en cours d'avant-hier.
    if sortie.exists():
        shutil.rmtree(sortie)
    sortie.mkdir(parents=True)

    p = preparer(cx, sortie)
    ecrire_etat(p)
    ecrire_groupes(p)
    ecrire_senat(p)
    ecrire_etapes(p)
    ecrire_fiches(p)
    ecrire_listes(p)
    ecrire_calendrier(p)
    ecrire_travaux(p)
    ecrire_changements(p)

    # La maquette devient la page d'accueil. Publiée à côté des données, elle
    # les lit par une adresse relative — et l'adresse racine sert enfin à
    # quelque chose au lieu de renvoyer une erreur.
    if MAQUETTE.exists():
        p.tailles["index.html"] = ecrire(p.sortie / "index.html", None,
                                       MAQUETTE.read_bytes())
        # Et ce qu'elle charge : son style et ses scripts, un fichier par
        # responsabilité, servis tels quels à côté d'elle. Pas d'étape de
        # construction — la page les demande par leur chemin relatif.
        p.tailles["style.css + js/*.js"] = sum(
            ecrire(p.sortie / f.relative_to(MAQUETTE.parent), None, f.read_bytes())
            for f in [MAQUETTE.parent / "style.css"]
                     + sorted((MAQUETTE.parent / "js").glob("*.js")))
    else:
        print(f"Maquette introuvable ({MAQUETTE}) : pas de page d'accueil.",
              file=sys.stderr)

    # Refermer la base du droit consolidé : une connexion laissée ouverte
    # garde un verrou, et la récupération en cours se cassait dessus.
    if p.legi_cx is not None:
        p.legi_cx.close()

    # GitHub Pages ne sert pas les dossiers dont le nom commence par un
    # tiret bas, et ajoute sa propre mise en page aux fichiers Markdown.
    # `.nojekyll` désactive tout ça : on veut nos fichiers, tels quels.
    (p.sortie / ".nojekyll").write_text("", encoding="utf-8")
    return p.tailles


def main() -> int:
    analyseur = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analyseur.add_argument("--base", type=pathlib.Path, default=BASE)
    analyseur.add_argument("--vers", type=pathlib.Path, default=SORTIE)
    options = analyseur.parse_args()

    if not options.base.exists():
        print(f"Base introuvable : {options.base}\nLancer d'abord ./recuperer.py",
              file=sys.stderr)
        return 1

    cx = sqlite3.connect(f"file:{options.base}?mode=ro", uri=True)
    cx.row_factory = sqlite3.Row
    tailles = publier(cx, options.vers)
    cx.close()

    fichiers = sum(1 for _ in options.vers.rglob("*") if _.is_file())
    print(f"Écrit dans {options.vers} — {fichiers} fichiers", file=sys.stderr)
    for nom, octets in tailles.items():
        print(f"   {octets:>10,} o   {nom}", file=sys.stderr)
    print(f"   {sum(tailles.values()):>10,} o   au total", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

