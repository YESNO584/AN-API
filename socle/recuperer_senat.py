#!/usr/bin/env python3
"""Construit `senat.db` : les scrutins, les sénateurs et les séances à venir.

**Pourquoi une base à part.** Celle de l'Assemblée et celle-ci ne se remplissent
pas aux mêmes heures, ne cassent pas pour les mêmes raisons, et n'ont pas les
mêmes règles. Les garder ensemble obligeait à tout refaire quand l'une bougeait.
C'est le motif de `legi.db` et de `textes.db`, pour la même raison. Le pont
entre les deux est une seule colonne, `signet` — voir `schema_senat.sql`.

**Cette étape est facultative.** Sans elle, tout le reste se publie et
l'application n'affiche simplement ni les votes du Sénat, ni sa composition, ni
son calendrier.

Usage :
    ./recuperer_senat.py                 # cycle normal
    ./recuperer_senat.py --sessions 3    # ne relire que les 3 dernières pages
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import pathlib
import shutil
import sqlite3
import sys
import tempfile
import extraction
import senat
from recuperation_senat.dossiers import ranger_dossiers, ranger_seances, ranger_themes
from recuperation_senat.garde import MARQUE_DE_FRAICHEUR, assez_pour_remplacer
from recuperation_senat.groupes import couleurs_des_groupes, ranger_groupes
from recuperation_senat.scrutins import PREMIERE_SESSION, ranger_scrutins, ranger_votes, session_en_cours
from recuperation_senat.senateurs import lire_historique, senateurs_a_jour


RACINE = pathlib.Path(__file__).resolve().parent


BASE = RACINE / "senat.db"


SCHEMA = RACINE / "schema_senat.sql"


def maintenant() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def ouvrir(chemin: pathlib.Path) -> sqlite3.Connection:
    cx = sqlite3.connect(chemin)
    cx.row_factory = sqlite3.Row
    cx.executescript(SCHEMA.read_text(encoding="utf-8"))
    return cx


def telecharger_les_sources(dossier: pathlib.Path) -> pathlib.Path:
    """Les quatre fichiers du Sénat, dans le dossier de travail. Rend l'archive
    des dossiers législatifs."""
    print("  dosleg", file=sys.stderr)
    archive = dossier / "dosleg.zip"
    extraction.telecharger(archive, None, senat.URL_DOSLEG)
    for nom, url in (("senateurs", senat.URL_SENATEURS),
                     ("histogroupes", senat.URL_HISTOGROUPES),
                     ("dossiers", senat.URL_DOSSIERS)):
        print(f"  {nom}", file=sys.stderr)
        extraction.telecharger(dossier / f"{nom}.csv", None, url)
    return archive


def sessions_a_relire(cx: sqlite3.Connection, options) -> list[int]:
    """Les sessions à relire : celle en cours toujours, les closes une seule
    fois — elles sont figées."""
    en_cours = session_en_cours()
    deja = {l["session"] for l in cx.execute(
        "SELECT DISTINCT session FROM scrutin_senat WHERE signet IS NOT NULL")}
    sessions = [s for s in range(PREMIERE_SESSION, en_cours + 1)
                if s == en_cours or s not in deja]
    if options.sessions:
        sessions = sessions[-options.sessions:]
    return sessions


def construire(chemin: pathlib.Path, options) -> list[str]:
    """Remplit une base du Sénat. Rend les alertes, lève sur un vrai échec."""
    cx = ouvrir(chemin)
    with tempfile.TemporaryDirectory() as travail:
        dossier = pathlib.Path(travail)
        archive = telecharger_les_sources(dossier)

        with cx:
            n_dos = ranger_dossiers(cx, archive)
            historique = lire_historique(dossier / "histogroupes.csv")
            actifs = [s for s in senat.lire_csv_senat(dossier / "senateurs.csv")
                      if s.get("État") == "ACTIF"]

            n_sen, noms, alertes_sources = senateurs_a_jour(
                cx, actifs, historique)
            sessions = sessions_a_relire(cx, options)
            n_scr, alertes = ranger_scrutins(cx, archive, sessions)
            alertes += alertes_sources
            # Sans l'historique, aucun vote ne peut être attribué à un
            # groupe : le recalculer rendrait 278 552 « sans groupe ».
            n_vot = (ranger_votes(cx, archive, historique, options.depuis)
                     if historique else 0)
            habits, alerte_couleurs = couleurs_des_groupes()
            if alerte_couleurs:
                alertes.append(alerte_couleurs)
            # `ranger_groupes` recompte les effectifs sur `senateur` : sans
            # liste neuve, il recompterait la même chose, mais il perdrait les
            # noms courts que seul le fichier des sénateurs porte.
            n_grp = (ranger_groupes(cx, options.depuis, noms, habits) if noms
                     else cx.execute(
                         "SELECT COUNT(*) n FROM groupe_senat").fetchone()["n"])
            n_sea = ranger_seances(cx, archive, dt.date.today().isoformat())
            n_the = ranger_themes(cx, dossier / "dossiers.csv")

            # La date de construction : c'est elle que la page affichera le
            # jour où les données du Sénat datent de la veille.
            cx.execute("INSERT OR REPLACE INTO source (url, vu_le)"
                       " VALUES (?, ?)", (MARQUE_DE_FRAICHEUR, maintenant()))

    print(f"  {n_dos:>7,} dossiers · {n_scr:>6,} scrutins ({len(sessions)} sessions"
          f" relues) · {n_vot:>6,} lignes de vote par groupe", file=sys.stderr)
    print(f"  {n_sen:>7,} sénateurs · {n_grp} groupes ({len(habits)} teintés)"
          f" · {n_sea} séances à venir"
          f" · {n_the:,} rattachements de thème", file=sys.stderr)
    cx.close()
    return alertes


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--base", type=pathlib.Path, default=BASE)
    a.add_argument("--sessions", type=int, default=0,
                   help="combien de sessions relire (0 = celles qui manquent)")
    a.add_argument("--depuis", default="2024-01-01",
                   help="la date à partir de laquelle on détaille les votes")
    options = a.parse_args()

    # **On construit à côté, et on ne remplace qu'en cas de succès complet.**
    # Avant, la construction écrivait directement dans la base publiée : le
    # 2026-10-06, une source du Sénat a rendu une page web au lieu d'un CSV,
    # la construction s'est arrêtée, et le site a perdu d'un coup la
    # composition, le calendrier et les 30 sujets du Sénat. Une reconstruction
    # qui échoue ne doit rien coûter.
    #
    # On **part de la base existante** plutôt que de rien : les sessions de
    # scrutins closes sont figées, et les relire toutes redemanderait 21 pages
    # au Sénat chaque matin pour le même résultat.
    base = options.base
    chantier = base.with_name(base.name + ".chantier")
    chantier.unlink(missing_ok=True)
    if base.exists():
        shutil.copy2(base, chantier)

    def renoncer(pourquoi: str) -> int:
        chantier.unlink(missing_ok=True)
        print(f"  {pourquoi}", file=sys.stderr)
        # Dire laquelle des deux situations on est dans : « on garde la veille »
        # serait faux le jour où il n'y a pas de veille — et c'est ce jour-là
        # que l'onglet « Sénat » s'affiche vide.
        print("  la base de la veille est gardée telle quelle" if base.exists()
              else "  et il n'y a aucune base de la veille : le site n'aura pas"
                   " de données du Sénat", file=sys.stderr)
        return 1

    try:
        alertes = construire(chantier, options)
    except Exception as erreur:
        return renoncer(f"ÉCHEC {type(erreur).__name__}: {erreur}")

    souci = assez_pour_remplacer(chantier, base)
    if souci:
        return renoncer(f"REFUS de remplacer : {souci}")

    os.replace(chantier, base)
    for x in alertes:
        print(f"  ALERTE {x}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
