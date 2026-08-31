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
import hashlib
import pathlib
import sqlite3
import sys
import tempfile

import extraction

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


def connue(connexion: sqlite3.Connection) -> sqlite3.Row | None:
    return connexion.execute(
        "SELECT * FROM source WHERE url = ?", (extraction.URL_ARCHIVE,)).fetchone()


def entetes_conditionnelles(ligne: sqlite3.Row | None) -> dict[str, str]:
    """De quoi demander « seulement si ça a changé » et économiser 10 Mo."""
    if not ligne:
        return {}
    entetes = {}
    if ligne["etag"]:
        entetes["If-None-Match"] = ligne["etag"]
    if ligne["modifie_le"]:
        entetes["If-Modified-Since"] = ligne["modifie_le"]
    return entetes


def empreinte(fichier: pathlib.Path) -> str:
    """Le sha256 de l'archive, lu par morceaux pour ne pas la charger en mémoire."""
    condensat = hashlib.sha256()
    with fichier.open("rb") as flux:
        for morceau in iter(lambda: flux.read(1 << 20), b""):
            condensat.update(morceau)
    return condensat.hexdigest()


def ranger(connexion: sqlite3.Connection, archive: pathlib.Path, aujourdhui: str) -> tuple[int, int]:
    """Remplace le contenu de la base par celui de l'archive. Tout ou rien."""
    dossiers, etapes = [], []
    for brut in extraction.lire_archive(archive):
        d = extraction.analyser(brut, aujourdhui)
        courant = d["etapeCourante"] or {}
        prochaine = next((e for e in d["etapes"] if e["future"]), None)
        dossiers.append((
            d["uid"], d["legislature"], d["titre"], d["titreChemin"], d["type"],
            int(d["estLoi"]), d["chambreInitiale"], d["statut"], d["etape"],
            d["dateDernierMouvement"],
            courant.get("chambre"), courant.get("lecture"),
            courant.get("libelle"), courant.get("conclusion"),
            (prochaine or {}).get("date"), (prochaine or {}).get("libelle"),
            d["urlAN"], d["urlSenat"],
            d["loiNumero"], d["loiDate"], d["loiUrlJO"],
        ))
        etapes += [(
            d["uid"], e["uid"], e["code"], e["lecture"], e["libelle"], e["chambre"],
            e["date"], e["rang"], e["numero"], e["conclusion"], int(e["future"]),
        ) for e in d["etapes"]]

    with connexion:                     # une transaction, ouverte et refermée ici
        connexion.execute("DELETE FROM etape")
        connexion.execute("DELETE FROM dossier")
        connexion.executemany(
            "INSERT INTO dossier VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", dossiers)
        connexion.executemany(
            "INSERT INTO etape VALUES (?,?,?,?,?,?,?,?,?,?,?)", etapes)
    return len(dossiers), len(etapes)


def afficher_journal(connexion: sqlite3.Connection, combien: int = 10) -> None:
    lignes = connexion.execute(
        "SELECT * FROM journal ORDER BY id DESC LIMIT ?", (combien,)).fetchall()
    if not lignes:
        print("Le journal est vide : le programme n'a encore jamais tourné.")
        return
    print(f"{'début':<27}{'statut':<10}{'dossiers':>9}{'étapes':>9}  message")
    for l in lignes:
        print(f"{l['debut']:<27}{l['statut']:<10}"
              f"{l['dossiers_lus'] or 0:>9}{l['etapes_ecrites'] or 0:>9}  {l['message'] or ''}")


def main() -> int:
    analyseur = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analyseur.add_argument("--forcer", action="store_true",
                           help="recharger même si la source est inchangée")
    analyseur.add_argument("--zip", type=pathlib.Path,
                           help="lire une archive locale au lieu de la télécharger")
    analyseur.add_argument("--base", type=pathlib.Path, default=BASE,
                           help=f"fichier de base de données (défaut : {BASE.name})")
    analyseur.add_argument("--journal", action="store_true",
                           help="afficher les dernières exécutions et s'arrêter")
    options = analyseur.parse_args()

    connexion = ouvrir(options.base)
    if options.journal:
        afficher_journal(connexion)
        return 0

    debut = maintenant()
    aujourdhui = dt.date.today().isoformat()
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

    try:
        with tempfile.TemporaryDirectory() as travail:
            if options.zip:
                archive = options.zip
                if not archive.exists():
                    raise FileNotFoundError(f"archive introuvable : {archive}")
                compte_rendu = {"modifie": True, "octets": archive.stat().st_size,
                                "etag": None, "modifieLe": None}
                print(f"Archive locale : {archive}", file=sys.stderr)
            else:
                precedente = None if options.forcer else connue(connexion)
                archive = pathlib.Path(travail) / "dossiers.zip"
                compte_rendu = extraction.telecharger(
                    archive, entetes_conditionnelles(precedente))

                if not compte_rendu["modifie"]:
                    clore("inchange", octets=0,
                          message="la source répond « non modifié »")
                    print("Rien n'a changé côté Assemblée : base laissée telle quelle.",
                          file=sys.stderr)
                    return 0
                print(f"Téléchargé : {compte_rendu['octets']:,} octets", file=sys.stderr)

                # Le téléchargement conditionnel ne suffit pas : l'archive est
                # servie par plusieurs machines qui ne publient pas la même
                # génération, si bien qu'un contenu identique arrive avec des
                # en-têtes différents. On compare donc le contenu lui-même.
                compte_rendu["empreinte"] = empreinte(archive)
                if precedente and compte_rendu["empreinte"] == precedente["empreinte"]:
                    connexion.execute(
                        "UPDATE source SET etag=?, modifie_le=?, vu_le=? WHERE url=?",
                        (compte_rendu["etag"], compte_rendu["modifieLe"], maintenant(),
                         extraction.URL_ARCHIVE))
                    clore("inchange", octets=compte_rendu["octets"],
                          message="archive téléchargée mais identique à la précédente")
                    print("Archive identique à la précédente : base laissée telle quelle.",
                          file=sys.stderr)
                    return 0

            dossiers, etapes = ranger(connexion, archive, aujourdhui)

        if not options.zip:
            connexion.execute(
                "INSERT INTO source (url, etag, modifie_le, empreinte, vu_le)"
                " VALUES (?,?,?,?,?)"
                " ON CONFLICT(url) DO UPDATE SET etag=excluded.etag,"
                " modifie_le=excluded.modifie_le, empreinte=excluded.empreinte,"
                " vu_le=excluded.vu_le",
                (extraction.URL_ARCHIVE, compte_rendu["etag"], compte_rendu["modifieLe"],
                 compte_rendu["empreinte"], maintenant()))
        clore("succes", octets=compte_rendu["octets"], dossiers=dossiers, etapes=etapes)

    except Exception as erreur:                       # noqa: BLE001 — on veut tout journaliser
        clore("echec", message=f"{type(erreur).__name__}: {erreur}")
        print(f"Échec : {type(erreur).__name__}: {erreur}", file=sys.stderr)
        return 1

    resume = connexion.execute("""
        SELECT etape, COUNT(*) n FROM dossier
         WHERE statut = 'en_cours' AND est_loi = 1 AND etape IS NOT NULL
         GROUP BY etape ORDER BY etape""").fetchall()
    print(f"\n{dossiers} dossiers rangés, {etapes} étapes.", file=sys.stderr)
    print("Textes de loi en cours, par étape :", file=sys.stderr)
    for numero, nom, _ in extraction.ETAPES:
        n = next((l["n"] for l in resume if l["etape"] == numero), 0)
        print(f"     {n:5d}  {numero}. {nom}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
