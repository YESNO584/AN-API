#!/usr/bin/env python3
"""Récupère les dossiers législatifs et les range dans la base.
Ce que fait ce programme, une fois par jour :
1. Il demande l'archive à l'Assemblée **en disant ce qu'il a déjà**. Si rien
   n'a changé, le serveur répond « 304 » et les 10 Mo ne sont pas retéléchargés.
2. Il lit l'archive et classe chaque dossier (voir `extraction.py`).
3. Il remplace le contenu de la base **en une seule transaction** : soit tout
   passe, soit rien ne bouge. Il n'y a jamais de base à moitié remplie.
4. Il écrit une ligne dans le journal. C'est ce qui rend une panne visible.
Usage :
    ./recuperer.py                  # cycle normal
    ./recuperer.py --forcer         # ignore le « rien n'a changé »
    ./recuperer.py --zip fichier    # depuis une archive locale, sans réseau
    ./recuperer.py --journal        # affiche les dernières exécutions
À programmer une fois par jour, par exemple :
    17 6 * * *  cd /chemin/socle && ./recuperer.py >> recuperer.log 2>&1
"""
from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import sqlite3
import sys
import tempfile
import extraction
from recuperation.journal import afficher_journal
from recuperation.rangement import ranger
from recuperation.telechargement import FACULTATIVES, SOURCES, connue, empreinte, entetes_conditionnelles, telecharger_en_insistant


RACINE = pathlib.Path(__file__).resolve().parent


BASE = RACINE / "parlement.db"


SCHEMA = RACINE / "schema.sql"


def maintenant() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def ouvrir(chemin: pathlib.Path) -> sqlite3.Connection:
    connexion = sqlite3.connect(chemin)
    connexion.row_factory = sqlite3.Row
    connexion.executescript(SCHEMA.read_text(encoding="utf-8"))
    return connexion


def arguments() -> argparse.Namespace:
    analyseur = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analyseur.add_argument("--forcer", action="store_true",
                           help="recharger même si la source est inchangée")
    analyseur.add_argument("--zip", nargs=len(SOURCES),
                           metavar=tuple(n.upper() for n in SOURCES),
                           type=pathlib.Path,
                           help="lire des fichiers locaux au lieu de les télécharger")
    analyseur.add_argument("--base", type=pathlib.Path, default=BASE,
                           help=f"fichier de base de données (défaut : {BASE.name})")
    analyseur.add_argument("--journal", action="store_true",
                           help="afficher les dernières exécutions et s'arrêter")
    options = analyseur.parse_args()
    if options.zip:
        options.zip = dict(zip(SOURCES, options.zip))
    return options


def archives_locales(options: argparse.Namespace) -> tuple[dict, dict]:
    """Des fichiers déjà là, au lieu de télécharger : pour rejouer un jour."""
    archives, comptes_rendus = {}, {}
    for nom, chemin in options.zip.items():
        if not chemin.exists():
            raise FileNotFoundError(f"archive introuvable : {chemin}")
        archives[nom] = chemin
        comptes_rendus[nom] = {"octets": chemin.stat().st_size}
        print(f"Archive locale ({nom}) : {chemin}", file=sys.stderr)
    return archives, comptes_rendus


def telecharger_les_sources(connexion: sqlite3.Connection,
                            options: argparse.Namespace, travail: str
                            ) -> tuple[dict, dict, dict, bool]:
    """Chaque archive, demandée seulement si elle a changé, facultative ou non.

    Rend les archives, leurs comptes rendus, les facultatives manquantes, et
    si **rien** n'a changé — auquel cas la base est laissée telle quelle.
    """
    archives, comptes_rendus, manquantes = {}, {}, {}
    inchangees = 0
    for nom, url in SOURCES.items():
        precedente = None if options.forcer else connue(connexion, url)
        chemin = pathlib.Path(travail) / f"{nom}.zip"
        try:
            cr = telecharger_en_insistant(
                nom, chemin, entetes_conditionnelles(precedente), url)
        except Exception as erreur:
            if nom not in FACULTATIVES:
                raise
            manquantes[nom] = f"{type(erreur).__name__}: {erreur}"
            print(f"  {nom:<10} indisponible : {erreur}", file=sys.stderr)
            continue
        if not cr["modifie"]:
            # Le serveur dit « rien de neuf » : on garde la copie de
            # la fois précédente. Elle n'existe pas ici — la machine
            # est neuve à chaque exécution — donc on retélécharge
            # sans condition plutôt que de travailler sans elle.
            cr = extraction.telecharger(chemin, None, url)
            inchangees += 1
        cr["empreinte"] = empreinte(chemin)
        if precedente and cr["empreinte"] == precedente["empreinte"]:
            inchangees += 1
        archives[nom], comptes_rendus[nom] = chemin, cr
        print(f"  {nom:<10} {cr['octets']:>12,} octets", file=sys.stderr)
    rien_de_neuf = (inchangees == len(SOURCES) and not manquantes
                    and not options.forcer)
    return archives, comptes_rendus, manquantes, rien_de_neuf


def marquer_les_sources_inchangees(connexion: sqlite3.Connection,
                                   comptes_rendus: dict) -> None:
    """Rien n'a changé : on note seulement qu'on a regardé."""
    for nom, url in SOURCES.items():
        connexion.execute(
            "UPDATE source SET etag=?, modifie_le=?, vu_le=? WHERE url=?",
            (comptes_rendus[nom]["etag"], comptes_rendus[nom]["modifieLe"],
             maintenant(), url))


def enregistrer_les_sources(connexion: sqlite3.Connection, comptes_rendus: dict) -> None:
    """Ce qu'on sait de chaque archive, pour ne pas la redemander demain."""
    for nom, url in SOURCES.items():
        cr = comptes_rendus.get(nom)
        if cr is None:
            continue
        connexion.execute(
            "INSERT INTO source (url, etag, modifie_le, empreinte, vu_le)"
            " VALUES (?,?,?,?,?)"
            " ON CONFLICT(url) DO UPDATE SET etag=excluded.etag,"
            " modifie_le=excluded.modifie_le, empreinte=excluded.empreinte,"
            " vu_le=excluded.vu_le",
            (url, cr["etag"], cr["modifieLe"], cr["empreinte"], maintenant()))


def resumer(connexion: sqlite3.Connection, dossiers: int, etapes: int,
            votes: int, amendements: int) -> None:
    """Ce que l'exécution affiche en finissant."""
    print("Textes de loi, par issue :", file=sys.stderr)
    for l in connexion.execute(
            "SELECT statut, COUNT(*) n FROM dossier WHERE est_loi = 1"
            " GROUP BY statut ORDER BY n DESC"):
        print(f"     {l['n']:5d}  {l['statut']}", file=sys.stderr)
    resume = connexion.execute("""
        SELECT etape, COUNT(*) n FROM dossier
         WHERE statut = 'en_cours' AND est_loi = 1 AND etape IS NOT NULL
         GROUP BY etape ORDER BY etape""").fetchall()
    print(f"\n{dossiers} dossiers, {etapes} étapes, {votes} scrutins,"
          f" {amendements} amendements rangés.", file=sys.stderr)
    lie = connexion.execute(
        "SELECT COUNT(DISTINCT dossier_uid) n FROM vote WHERE dossier_uid IS NOT NULL"
    ).fetchone()["n"]
    print(f"Scrutins rattachés à {lie} dossiers.", file=sys.stderr)
    ordre = connexion.execute(
        "SELECT sigle FROM groupe ORDER BY rang").fetchall()
    if ordre:
        print("Groupes, de gauche à droite : "
              + " · ".join(l["sigle"] for l in ordre), file=sys.stderr)
    print("Textes de loi en cours, par étape :", file=sys.stderr)
    for numero, nom, _ in extraction.ETAPES:
        n = next((l["n"] for l in resume if l["etape"] == numero), 0)
        print(f"     {n:5d}  {numero}. {nom}", file=sys.stderr)


def ouvrir_execution(connexion: sqlite3.Connection):
    """Ouvre une ligne du journal, et rend de quoi la clore."""
    debut = maintenant()
    curseur = connexion.execute(
        "INSERT INTO journal (debut, statut) VALUES (?, 'en_cours')", (debut,))
    execution = curseur.lastrowid
    connexion.commit()
    def clore(statut: str, *, octets=None, dossiers=None, etapes=None, message=None) -> None:
        connexion.execute(
            "UPDATE journal SET fin=?, statut=?, octets=?, dossiers_lus=?,"
            " etapes_ecrites=?, message=? WHERE id=?",
            (maintenant(), statut, octets, dossiers, etapes, message, execution))
        connexion.commit()
    return clore


def main() -> int:
    options = arguments()
    connexion = ouvrir(options.base)
    if options.journal:
        afficher_journal(connexion)
        return 0
    aujourdhui = dt.date.today().isoformat()
    clore = ouvrir_execution(connexion)
    try:
        with tempfile.TemporaryDirectory() as travail:
            manquantes = {}
            if options.zip:
                archives, comptes_rendus = archives_locales(options)
            else:
                archives, comptes_rendus, manquantes, rien_de_neuf = (
                    telecharger_les_sources(connexion, options, travail))
                if rien_de_neuf:
                    marquer_les_sources_inchangees(connexion, comptes_rendus)
                    clore("inchange",
                          octets=sum(c["octets"] for c in comptes_rendus.values()),
                          message="aucune des trois sources n'a changé")
                    print("Rien n'a changé côté Assemblée : base laissée telle quelle.",
                          file=sys.stderr)
                    return 0
            dossiers, etapes, votes, amendements, paroles = ranger(
                connexion, archives, aujourdhui)
        if not options.zip:
            enregistrer_les_sources(connexion, comptes_rendus)
        message = f"{votes} scrutins, {amendements} amendements, {paroles} paroles"
        if manquantes:
            message += " — source indisponible : " + ", ".join(sorted(manquantes))
        clore("succes" if not manquantes else "partiel",
              octets=sum(c["octets"] for c in comptes_rendus.values()),
              dossiers=dossiers, etapes=etapes, message=message)
    except Exception as erreur:                       # noqa: BLE001 — on veut tout journaliser
        clore("echec", message=f"{type(erreur).__name__}: {erreur}")
        print(f"Échec : {type(erreur).__name__}: {erreur}", file=sys.stderr)
        return 1
    resumer(connexion, dossiers, etapes, votes, amendements)
    return 0


if __name__ == "__main__":
    sys.exit(main())
