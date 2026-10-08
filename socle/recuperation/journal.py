"""La table `journal` : ce que chaque exécution a fait, et ce qu'elle affiche en finissant.
"""
from __future__ import annotations

import sqlite3


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
