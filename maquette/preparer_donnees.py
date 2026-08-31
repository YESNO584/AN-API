#!/usr/bin/env python3
"""Remplit `feed.html` avec les données réelles de l'Assemblée.

Pourquoi ce script existe : ni `data.assemblee-nationale.fr` ni `data.senat.fr`
n'autorisent une page web à lire leurs fichiers directement (l'en-tête
`Access-Control-Allow-Origin` est absent — vérifié le 2026-08-31). Une page
HTML ne peut donc pas aller chercher les données au chargement. On les prépare
ici, une fois, et on les écrit dans `feed.html`, qui reste un fichier autonome.

La lecture et le classement des dossiers ne sont **pas** faits ici : ils vivent
dans `../socle/extraction.py`, avec leurs tests. Ce script n'est que l'écriture
dans la page.

Usage :
    ./preparer_donnees.py                 # télécharge, extrait, écrit feed.html
    ./preparer_donnees.py --zip fichier   # réutilise une archive déjà là
    ./preparer_donnees.py --garder-zip    # garde l'archive pour la prochaine fois

Source : https://data.assemblee-nationale.fr — Licence Ouverte (Etalab).
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import pathlib
import re
import sys
import tempfile

RACINE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE.parent / "socle"))
import extraction  # noqa: E402 — après l'ajout du socle au chemin de recherche

DEBUT, FIN = "// >>> DONNEES", "// <<< FIN DONNEES"


def preparer(archive: pathlib.Path, aujourdhui: str) -> tuple[list[dict], dict]:
    """Ne garde que ce que la maquette affiche : les textes de loi en cours."""
    textes = []
    comptes = collections.Counter()

    for brut in extraction.lire_archive(archive):
        comptes["total"] += 1
        d = extraction.analyser(brut, aujourdhui)

        if not d["estLoi"]:
            comptes["hors_loi"] += 1
            continue
        if d["statut"] != extraction.EN_COURS:
            comptes[d["statut"]] += 1
            continue

        futures = [e for e in d["etapes"] if e["future"]]
        courante = d["etapeCourante"]

        textes.append({
            "id": d["uid"],
            "titre": d["titre"],
            "type": d["type"],
            "etape": d["etape"],
            "lecture": courante["lecture"],
            "dernierActe": courante["libelle"],
            "chambre": courante["chambre"],
            "chambreInitiale": d["chambreInitiale"],
            "date": d["dateDernierMouvement"],
            "conclusion": courante["conclusion"],
            "prochaine": ({"date": futures[0]["date"], "quoi": futures[0]["libelle"]}
                          if futures else None),
            "urlAN": d["urlAN"],
            "urlSenat": d["urlSenat"],
        })

    textes.sort(key=lambda t: (t["etape"], t["date"]), reverse=True)
    return textes, comptes


def injecter(page: pathlib.Path, textes: list[dict], meta: dict) -> None:
    contenu = page.read_text(encoding="utf-8")
    bloc = (
        f"{DEBUT} — écrit par preparer_donnees.py, ne pas modifier à la main\n"
        f"const META = {json.dumps(meta, ensure_ascii=False, indent=2)};\n"
        f"const TEXTES = {json.dumps(textes, ensure_ascii=False, separators=(',', ':'))};\n"
        f"{FIN}"
    )
    motif = re.compile(re.escape(DEBUT) + r".*?" + re.escape(FIN), re.S)
    if not motif.search(contenu):
        sys.exit(f"Repères « {DEBUT} » / « {FIN} » introuvables dans {page}.")
    page.write_text(motif.sub(lambda _: bloc, contenu, count=1), encoding="utf-8")


def main() -> None:
    analyseur = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analyseur.add_argument("--zip", type=pathlib.Path,
                           help="archive déjà téléchargée, au lieu de la reprendre sur le réseau")
    analyseur.add_argument("--garder-zip", action="store_true",
                           help="conserver l'archive téléchargée dans .cache/")
    analyseur.add_argument("--page", type=pathlib.Path, default=RACINE / "feed.html",
                           help="page à mettre à jour (défaut : feed.html)")
    options = analyseur.parse_args()

    aujourdhui = dt.date.today().isoformat()

    with tempfile.TemporaryDirectory() as travail:
        if options.zip:
            archive = options.zip
            if not archive.exists():
                sys.exit(f"Archive introuvable : {archive}")
            print(f"Archive réutilisée : {archive}", file=sys.stderr)
        else:
            if options.garder_zip:
                (RACINE / ".cache").mkdir(exist_ok=True)
                archive = RACINE / ".cache" / "Dossiers_Legislatifs.json.zip"
            else:
                archive = pathlib.Path(travail) / "dossiers.zip"
            print(f"Téléchargement de {extraction.URL_ARCHIVE}", file=sys.stderr)
            compte_rendu = extraction.telecharger(archive)
            print(f"  {compte_rendu['octets']:,} octets", file=sys.stderr)

        textes, comptes = preparer(archive, aujourdhui)

    par_etape = {str(n): sum(1 for t in textes if t["etape"] == n)
                 for n, _, _ in extraction.ETAPES}

    meta = {
        "extraitLe": aujourdhui,
        "source": extraction.URL_ARCHIVE,
        "licence": "Licence Ouverte (Etalab)",
        "legislature": extraction.LEGISLATURE,
        "etapes": [{"n": n, "nom": nom, "quoi": quoi} for n, nom, quoi in extraction.ETAPES],
        "comptes": {"total": comptes["total"], "hors_loi": comptes["hors_loi"],
                    "promulgues": comptes[extraction.PROMULGUE],
                    "retires": comptes[extraction.RETIRE],
                    "sans_acte": comptes[extraction.SANS_ACTE]},
        "parEtape": par_etape,
        "enCours": len(textes),
    }
    injecter(options.page, textes, meta)

    print(f"\n{comptes['total']} dossiers de la {extraction.LEGISLATURE}e législature",
          file=sys.stderr)
    print(f"  – {comptes['hors_loi']} écartés : ne fabriquent pas de loi", file=sys.stderr)
    print(f"  – {comptes[extraction.PROMULGUE]} promulgués,"
          f" {comptes[extraction.RETIRE]} retirés,"
          f" {comptes[extraction.SANS_ACTE]} sans acte passé", file=sys.stderr)
    print(f"  = {len(textes)} textes en cours écrits dans {options.page}", file=sys.stderr)
    for n, nom, _ in extraction.ETAPES:
        print(f"        {par_etape[str(n)]:5d}  {n}. {nom}", file=sys.stderr)


if __name__ == "__main__":
    main()
