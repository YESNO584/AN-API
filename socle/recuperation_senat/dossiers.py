"""Ce qui vient du dump et du CSV des dossiers : les dossiers eux-mêmes, les séances à venir, les sujets.
"""
from __future__ import annotations

import pathlib
import sqlite3
import senat


def ranger_seances(cx: sqlite3.Connection, archive: pathlib.Path,
                   aujourdhui: str) -> int:
    """Les séances à venir, et le texte que chacune examine.

    **Un piège du nom de colonne, mesuré le 2026-10-04** : `date_seance.lecidt`
    ne porte pas un `lecidt` mais un `lecassidt`. Le chemin est donc
    `date_seance` → `lecass` → `lecture` → `loi.signet`, et croire au nom de la
    colonne rendait zéro séance sur dix-neuf.
    """
    lecass = {senat.net(l["lecassidt"]): senat.net(l["lecidt"])
              for l in senat.lire_dump(archive, "lecass")}
    lecture = {senat.net(l["lecidt"]): senat.net(l["loicod"])
               for l in senat.lire_dump(archive, "lecture")}
    signet = {senat.net(l["loicod"]): senat.net(l["signet"])
              for l in senat.lire_dump(archive, "loi") if l["signet"]}
    lignes = set()
    for l in senat.lire_dump(archive, "date_seance"):
        quand = (l["date_s"] or "")[:10]
        if quand <= aujourdhui:
            continue
        sig = signet.get(lecture.get(lecass.get(senat.net(l["lecidt"]), ""), ""))
        if sig:
            lignes.add((quand, sig))
    cx.execute("DELETE FROM seance_senat")
    cx.executemany("INSERT INTO seance_senat VALUES (?,?)", sorted(lignes))
    return len(lignes)


def ranger_themes(cx: sqlite3.Connection, chemin: pathlib.Path) -> int:
    """Le sujet de chaque dossier, tel que le Sénat le classe.

    Le fichier est celui que le socle lit déjà pour l'état d'un dossier, mais
    il est retéléchargé ici — 3,5 Mo — plutôt que partagé : les deux bases
    restent indépendantes, et c'est tout l'intérêt de les avoir séparées.
    """
    lignes = []
    for l in senat.lire_csv_senat(chemin):
        sig = senat.signet_de(l.get("URL du dossier"))
        if not sig:
            continue
        for rang, theme in enumerate(senat.themes_de(l.get("Thèmes"))):
            lignes.append((sig, theme, rang))
    cx.execute("DELETE FROM theme_senat")
    cx.executemany("INSERT OR REPLACE INTO theme_senat VALUES (?,?,?)", lignes)
    return len(lignes)


def ranger_dossiers(cx: sqlite3.Connection, archive: pathlib.Path) -> int:
    """Les dossiers du Sénat, pour faire le pont et nommer ce qu'on affiche."""
    lignes = [(senat.net(l["signet"]), senat.net(l["loicod"]),
               senat.net(l["loiint"]), senat.net(l["etaloicod"]))
              for l in senat.lire_dump(archive, "loi") if l["signet"]]
    cx.executemany("INSERT OR REPLACE INTO dossier_senat VALUES (?,?,?,?)", lignes)
    return len(lignes)
