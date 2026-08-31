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

import extraction

RACINE = pathlib.Path(__file__).resolve().parent
BASE = RACINE / "parlement.db"
SORTIE = RACINE / "public"

# Ce que la liste embarque pour chaque texte. Volontairement court : elle est
# chargée en entier par l'application, qui filtre et cherche ensuite toute
# seule, hors connexion. Le reste est dans le fichier de détail.
CHAMPS_LISTE = ("uid", "titre", "type", "chambre_initiale", "etape",
                "date_dernier_mouvement", "url_an", "url_senat")


def ecrire(chemin: pathlib.Path, contenu) -> int:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    brut = json.dumps(contenu, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    chemin.write_bytes(brut)
    return len(brut)


def chambre_actuelle(cx: sqlite3.Connection, uid: str) -> str | None:
    """La chambre où le texte se trouve : celle de son dernier acte passé."""
    ligne = cx.execute(
        "SELECT chambre FROM etape WHERE dossier_uid = ? AND future = 0"
        " ORDER BY date DESC, numero DESC, rang DESC LIMIT 1", (uid,)).fetchone()
    return ligne["chambre"] if ligne else None


def publier(cx: sqlite3.Connection, sortie: pathlib.Path) -> dict[str, int]:
    # On repart d'un dossier vide : un texte promulgué hier ne doit pas rester
    # dans la liste des textes en cours d'avant-hier.
    if sortie.exists():
        shutil.rmtree(sortie)
    sortie.mkdir(parents=True)

    tailles: dict[str, int] = {}
    genere_le = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    comptes = {l["statut"]: l["n"] for l in cx.execute(
        "SELECT statut, COUNT(*) n FROM dossier WHERE est_loi = 1 GROUP BY statut")}
    par_etape = {l["etape"]: l["n"] for l in cx.execute(
        "SELECT etape, COUNT(*) n FROM dossier"
        " WHERE statut='en_cours' AND est_loi=1 AND etape IS NOT NULL GROUP BY etape")}

    chargement = cx.execute(
        "SELECT * FROM journal WHERE statut = 'succes' ORDER BY id DESC LIMIT 1").fetchone()

    tailles["etat.json"] = ecrire(sortie / "etat.json", {
        "genereLe": genere_le,
        "source": extraction.URL_ARCHIVE,
        "licence": "Licence Ouverte (Etalab)",
        "legislature": extraction.LEGISLATURE,
        "dernierChargement": dict(chargement) if chargement else None,
        "dossiers": cx.execute("SELECT COUNT(*) n FROM dossier").fetchone()["n"],
        "etapesEnregistrees": cx.execute("SELECT COUNT(*) n FROM etape").fetchone()["n"],
        "textesEnCours": comptes.get(extraction.EN_COURS, 0),
        "promulgues": comptes.get(extraction.PROMULGUE, 0),
        "fichiers": ["etapes.json", "textes.json", "promulgues.json", "textes/<uid>.json"],
    })

    tailles["etapes.json"] = ecrire(sortie / "etapes.json", {
        "genereLe": genere_le,
        "etapes": [{"n": n, "nom": nom, "quoi": quoi, "textesEnCours": par_etape.get(n, 0)}
                   for n, nom, quoi in extraction.ETAPES],
    })

    for nom_fichier, statut in (("textes.json", extraction.EN_COURS),
                                ("promulgues.json", extraction.PROMULGUE)):
        lignes = cx.execute(
            f"SELECT {', '.join(CHAMPS_LISTE)}, loi_numero, loi_date, loi_url_jo"
            " FROM dossier WHERE statut = ? AND est_loi = 1"
            " ORDER BY date_dernier_mouvement DESC, uid", (statut,)).fetchall()
        textes = []
        for l in lignes:
            texte = {c: l[c] for c in CHAMPS_LISTE}
            texte["chambre"] = chambre_actuelle(cx, l["uid"])
            if statut == extraction.PROMULGUE:
                texte.update(loiNumero=l["loi_numero"], loiDate=l["loi_date"],
                             loiUrlJO=l["loi_url_jo"])
            textes.append(texte)
        tailles[nom_fichier] = ecrire(sortie / nom_fichier,
                                      {"genereLe": genere_le, "total": len(textes),
                                       "textes": textes})

    # Le détail, un fichier par texte. Seulement pour ceux que les listes
    # citent : publier les 708 dossiers qui ne font pas de loi n'aurait
    # aucun lecteur.
    details = 0
    for l in cx.execute(
            "SELECT * FROM dossier WHERE est_loi = 1 AND statut IN (?, ?)",
            (extraction.EN_COURS, extraction.PROMULGUE)):
        parcours = [dict(e) for e in cx.execute(
            "SELECT code, lecture, libelle, chambre, date, numero, conclusion, future"
            " FROM etape WHERE dossier_uid = ? ORDER BY date, rang", (l["uid"],))]
        details += ecrire(sortie / "textes" / f'{l["uid"]}.json',
                          {**dict(l), "chambre": chambre_actuelle(cx, l["uid"]),
                           "parcours": parcours})
    tailles["textes/*.json"] = details

    # GitHub Pages ne sert pas les dossiers dont le nom commence par un
    # tiret bas, et ajoute sa propre mise en page aux fichiers Markdown.
    # `.nojekyll` désactive tout ça : on veut nos fichiers, tels quels.
    (sortie / ".nojekyll").write_text("", encoding="utf-8")
    return tailles


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
