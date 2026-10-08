"""Ce qui empêche une base neuve mais appauvrie de remplacer celle de la veille.
"""
from __future__ import annotations

import pathlib
import sqlite3


# Ce que la base doit porter pour valoir d'être publiée. Ce ne sont pas des
# seuils de qualité : ce sont les tables sans lesquelles un écran entier
# disparaît de l'application.
VITAL = {
    "senateur": "la composition du Sénat",
    "dossier_senat": "le pont avec nos textes",
    "theme_senat": "les sujets",
}


MARQUE_DE_FRAICHEUR = "senat.db"


def compter(chemin: pathlib.Path) -> dict[str, int]:
    cx = sqlite3.connect(chemin)
    try:
        return {t: cx.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in VITAL}
    except sqlite3.Error:
        return {}
    finally:
        cx.close()


def assez_pour_remplacer(neuve: pathlib.Path,
                         ancienne: pathlib.Path) -> str | None:
    """Ce qui empêche de remplacer la base de la veille, ou rien.

    **La règle tient en une phrase : ne jamais remplacer par pire, mais ne
    jamais refuser mieux.** Le 2026-10-06, `data.senat.fr` a rendu une page web
    à la place de ses fichiers de sénateurs : la construction laissait une base
    vide et l'onglet « Sénat » perdait tout.

    Exiger que **chaque** table vitale soit remplie était la première parade —
    et elle protégeait trop large : le même jour, les dossiers, les séances et
    les sujets arrivaient parfaitement, et ils restaient bloqués parce que la
    liste des sénateurs manquait. Un écran qui dit honnêtement « pas de
    données » vaut mieux que trois écrans gelés.

    Trois refus, donc, et seulement trois : une base illisible ; une base
    **entièrement** vide ; et une table qui **perd plus d'un quart** de ses
    lignes, ce qui n'arrive pas en un jour au Parlement et signe une source à
    moitié lue.
    """
    neuf = compter(neuve)
    if not neuf:
        return "la base construite n'est pas lisible"
    if not any(neuf.values()):
        return "la base construite est entièrement vide"
    if not ancienne.exists():
        return None
    vieux = compter(ancienne)
    for table, quoi in VITAL.items():
        avant, apres = vieux.get(table, 0), neuf[table]
        if avant and apres < avant * 0.75:
            return (f"{quoi} : {apres:,} lignes contre {avant:,} la veille"
                    f" ({apres / avant:.0%})")
    return None
