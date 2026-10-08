"""Le décor des tests de la base du Sénat : une base vide au schéma du projet.
"""
from __future__ import annotations

import pathlib
import sqlite3


SCHEMA = pathlib.Path(__file__).resolve().parent / "schema_senat.sql"


def base() -> sqlite3.Connection:
    cx = sqlite3.connect(":memory:")
    cx.row_factory = sqlite3.Row
    cx.executescript(SCHEMA.read_text(encoding="utf-8"))
    return cx
