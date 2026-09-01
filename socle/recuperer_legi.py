#!/usr/bin/env python3
"""Récupère, dans le droit consolidé, ce que nos lois y ont changé.

    ./recuperer_legi.py                 # rattrape tout ce qui manque
    ./recuperer_legi.py --lois 2026-813 # une seule loi, pour vérifier
    ./recuperer_legi.py --sans-socle    # seulement les archives quotidiennes

Le résultat va dans `legi.db`, **à part de `parlement.db`**. C'est voulu : la
base du Parlement se reconstruit chaque matin en une minute, tandis que celle-ci
demande une passe de quinze minutes sur un fichier de 1,1 Go. On garde donc la
seconde d'un jour sur l'autre, et on n'y ajoute que les archives nouvelles.

**Rien n'est déplié sur le disque.** Le socle pèse 9,5 Go déplié, en 2,5
millions de fichiers minuscules. On le lit en flux, deux fois : la première
passe repère les rédactions que nos lois ont changées, la seconde va chercher
les rédactions d'avant, dont on ne connaît l'identité qu'à l'issue de la
première.

Source : https://echanges.dila.gouv.fr/OPENDATA/LEGI/ — Licence Ouverte (Etalab).
"""

from __future__ import annotations

import argparse
import pathlib
import sqlite3
import sys
import time
import urllib.request

import extraction
import legi

ICI = pathlib.Path(__file__).parent
BASE = ICI / "legi.db"
TRAVAIL = ICI / "archives_legi"
# En dessous, ce n'est pas une archive : la plus petite quotidienne du dépôt
# pèse une centaine de kilo-octets.
MINIMUM = 50_000

SCHEMA = """
CREATE TABLE IF NOT EXISTS archive (
    nom         TEXT PRIMARY KEY,       -- le fichier tel qu'il s'appelle au dépôt
    vu_le       TEXT NOT NULL,
    redactions  INTEGER NOT NULL DEFAULT 0
);

-- Une rédaction d'article : pas « l'article L401-1 », mais l'une de ses
-- versions successives, avec la période où elle s'applique.
CREATE TABLE IF NOT EXISTS redaction (
    id          TEXT PRIMARY KEY,       -- LEGIARTI…
    numero      TEXT,
    ou          TEXT,                   -- « Code de l'éducation »
    etat        TEXT,
    debut       TEXT,
    fin         TEXT,
    texte       TEXT,
    nota        TEXT,
    precedent   TEXT                    -- la rédaction d'avant, ou NULL
);

-- Ce qu'une loi a fait à une rédaction. Les simples citations n'y sont pas.
CREATE TABLE IF NOT EXISTS changement (
    loi          TEXT NOT NULL,         -- « 2026-813 »
    quoi         TEXT NOT NULL,         -- MODIFIE, CREE, ABROGE, TRANSFERE, DEPLACE
    article_loi  TEXT,                  -- l'article de la loi qui a agi
    redaction_id TEXT NOT NULL REFERENCES redaction(id),
    PRIMARY KEY (loi, quoi, redaction_id)
);

CREATE INDEX IF NOT EXISTS changement_par_loi ON changement(loi);
"""


def ouvrir(chemin: pathlib.Path = BASE) -> sqlite3.Connection:
    """Ouvre la base en écriture, en la partageant avec les lecteurs.

    `journal_mode = WAL` n'est pas un réglage de confort : sans lui, un simple
    lecteur — `publier.py` qui regarde la base pendant qu'on la remplit —
    bloque l'écriture, et une passe de quarante minutes se termine par
    « database is locked » après avoir tout perdu. Constaté le 2026-09-01.
    """
    base = sqlite3.connect(chemin, timeout=60)
    base.row_factory = sqlite3.Row
    base.execute("PRAGMA journal_mode = WAL")
    base.execute("PRAGMA busy_timeout = 60000")
    base.executescript(SCHEMA)
    return base


def nos_lois(chemin: pathlib.Path = ICI / "parlement.db") -> set[str]:
    """Les numéros des lois promulguées que le projet suit.

    Sans elles, on garderait tout le droit français ; avec elles, on ne garde
    que ce qui concerne les textes affichés.
    """
    if not chemin.exists():
        return set()
    with sqlite3.connect(chemin) as parlement:
        return {numero for (numero,) in parlement.execute(
            "SELECT loi_numero FROM dossier "
            "WHERE statut = 'promulgue' AND loi_numero IS NOT NULL AND loi_numero != ''")}


def page_du_depot() -> str:
    requete = urllib.request.Request(
        legi.DEPOT_LEGI, headers={"User-Agent": "AN-API/socle (recuperation open data)"})
    with urllib.request.urlopen(requete, timeout=120) as reponse:
        return reponse.read().decode("utf-8", "replace")


def deux_passes(chemin: pathlib.Path, lois: set[str], base: sqlite3.Connection) -> int:
    """Lit une archive et range ce qui concerne nos lois. Rend le nombre de rédactions.

    Première passe : les rédactions que nos lois ont changées. On note au passage
    l'identité de la rédaction d'avant, que la première passe a pu croiser sans
    savoir qu'elle en aurait besoin — l'ordre des fichiers dans l'archive est
    arbitraire. Seconde passe : on va chercher ces rédactions-là.
    """
    voulues: set[str] = set()
    gardees = 0

    with chemin.open("rb") as flux:
        for _, brut in legi.parcourir_archive(flux):
            xml = brut.decode("utf-8", "replace")
            actions = [c for c in legi.changements(xml) if c["loi"] in lois]
            if not actions:
                continue
            article = legi.lire_article(xml)
            ranger(base, article)
            for action in actions:
                base.execute(
                    "INSERT OR REPLACE INTO changement "
                    "(loi, quoi, article_loi, redaction_id) VALUES (?, ?, ?, ?)",
                    (action["loi"], action["quoi"], action["article_loi"], article["id"]))
            gardees += 1
            # On enregistre au fil de l'eau : une passe sur le socle dure un
            # quart d'heure, et tout perdre sur un incident de la dernière
            # minute serait absurde.
            if gardees % 200 == 0:
                base.commit()
            if article["precedent"]:
                voulues.add(article["precedent"])
    base.commit()

    voulues -= {ligne["id"] for ligne in base.execute(
        "SELECT id FROM redaction WHERE texte IS NOT NULL")}
    if voulues:
        with chemin.open("rb") as flux:
            for _, brut in legi.parcourir_archive(flux):
                xml = brut.decode("utf-8", "replace")
                identifiant = legi.champ(legi.champ(xml, "META_COMMUN"), "ID")
                if identifiant in voulues:
                    ranger(base, legi.lire_article(xml))
                    gardees += 1
                    voulues.discard(identifiant)
                    if not voulues:
                        break
    base.commit()
    return gardees


def ranger(base: sqlite3.Connection, article: dict) -> None:
    base.execute(
        "INSERT OR REPLACE INTO redaction "
        "(id, numero, ou, etat, debut, fin, texte, nota, precedent) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (article["id"], article["numero"], article["ou"], article["etat"],
         article["debut"], article["fin"], article["texte"], article["nota"],
         article["precedent"]))


def deja_vues(base: sqlite3.Connection) -> set[str]:
    return {ligne["nom"] for ligne in base.execute("SELECT nom FROM archive")}


def traiter(nom: str, lois: set[str], base: sqlite3.Connection) -> int:
    """Télécharge une archive, la lit, la range, puis l'efface du disque.

    L'archive n'est effacée **qu'en cas de succès** : le socle met une dizaine
    de minutes à arriver, et une relance après incident doit repartir du
    fichier déjà là plutôt que de le retélécharger.
    """
    TRAVAIL.mkdir(exist_ok=True)
    chemin = TRAVAIL / nom
    # Une archive vide ou absente au moment de la lire n'est pas une fatalité :
    # on la redemande. Constaté le 2026-09-01, une fois, sans cause identifiée —
    # le socle avait bien été téléchargé, et n'était plus là dix secondes plus
    # tard. Plutôt que de tout perdre, on recommence, et on le dit.
    for essai in range(1, 4):
        if not chemin.exists() or chemin.stat().st_size < MINIMUM:
            chemin.unlink(missing_ok=True)
            extraction.telecharger(chemin, url=legi.DEPOT_LEGI + nom)
        if chemin.exists() and chemin.stat().st_size >= MINIMUM:
            break
        print(f"    {nom} introuvable ou vide après téléchargement "
              f"(essai {essai} sur 3)", file=sys.stderr, flush=True)
    else:
        raise RuntimeError(f"{nom} : impossible d'obtenir l'archive")

    gardees = deux_passes(chemin, lois, base)
    chemin.unlink(missing_ok=True)
    base.execute("INSERT OR REPLACE INTO archive (nom, vu_le, redactions) VALUES (?, ?, ?)",
                 (nom, time.strftime("%Y-%m-%dT%H:%M:%S"), gardees))
    base.commit()
    return gardees


def main(argv: list[str] | None = None) -> int:
    arguments = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    arguments.add_argument("--lois", nargs="*",
                           help="ne garder que ces numéros de loi (pour vérifier)")
    arguments.add_argument("--sans-socle", action="store_true",
                           help="ne pas lire le socle de 1,1 Go")
    arguments.add_argument("--maximum", type=int,
                           help="s'arrêter après ce nombre d'archives")
    options = arguments.parse_args(argv)

    lois = set(options.lois) if options.lois else nos_lois()
    if not lois:
        print("Aucune loi promulguée à suivre : lancez d'abord recuperer.py.",
              file=sys.stderr)
        return 1

    base = ouvrir()
    socle, quotidiennes = legi.archives_du_depot(page_du_depot())
    faites = deja_vues(base)

    a_faire = [] if (options.sans_socle or not socle or socle in faites) else [socle]
    a_faire += [nom for nom in quotidiennes if nom not in faites]
    if options.maximum:
        a_faire = a_faire[:options.maximum]

    print(f"{len(lois)} lois suivies · {len(faites)} archives déjà lues · "
          f"{len(a_faire)} à lire")
    debut = time.time()
    for rang, nom in enumerate(a_faire, 1):
        depart = time.time()
        print(f"  [{rang}/{len(a_faire)}] {nom}…", flush=True)
        gardees = traiter(nom, lois, base)
        print(f"  [{rang}/{len(a_faire)}] {nom} — {gardees} rédactions "
              f"en {time.time() - depart:.0f} s", flush=True)

    total = base.execute("SELECT COUNT(*) FROM redaction").fetchone()[0]
    changements = base.execute("SELECT COUNT(*) FROM changement").fetchone()[0]
    concernees = base.execute("SELECT COUNT(DISTINCT loi) FROM changement").fetchone()[0]
    print(f"\n{total} rédactions, {changements} changements, {concernees} lois "
          f"— en {(time.time() - debut) / 60:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
