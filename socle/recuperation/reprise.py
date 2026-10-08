"""Ce qu'une archive facultative absente ne doit pas emporter : les lignes de la veille, mises de côté avant la transaction et reposées dedans.
"""
from __future__ import annotations

import pathlib
import sqlite3


# Les tables qu'une archive facultative remplit à elle seule, et l'archive dont
# chacune dépend. Ce sont exactement celles qu'une absence viderait.
REPRISES = {
    "amendements": ("amendement",),
    "debats": ("parole", "debat_amendement"),
}


def a_reprendre(connexion: sqlite3.Connection,
                archives: dict[str, pathlib.Path]) -> dict[str, list[sqlite3.Row]]:
    """Les lignes de la veille à remettre en place, archive absente par archive
    absente. Lues avant la transaction, puisque celle-ci les effacera."""
    repris = {}
    for source, tables in REPRISES.items():
        if source in archives:
            continue
        for table in tables:
            repris[table] = connexion.execute(f"SELECT * FROM {table}").fetchall()
    return repris


def reposer(connexion: sqlite3.Connection, repris: dict[str, list[sqlite3.Row]],
            connus: set[str]) -> dict[str, list[tuple]]:
    """Repose les lignes de la veille, **dans la transaction qui vient de les
    effacer**. Seules reviennent celles dont le dossier existe encore : un
    dossier que l'archive ne porte plus n'a pas à ressusciter par ses
    amendements."""
    gardees = {}
    for table, anciennes in repris.items():
        lignes = [tuple(l) for l in anciennes if l["dossier_uid"] in connus]
        gardees[table] = lignes
        if lignes:
            trous = ",".join("?" * len(lignes[0]))
            connexion.executemany(f"INSERT INTO {table} VALUES ({trous})", lignes)
    return gardees
