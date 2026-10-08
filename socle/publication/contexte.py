"""Ce que toutes les étapes de la publication partagent.

Chaque étape reçoit ce contexte et y lit ce dont elle a besoin : la base, le
dossier de sortie, l'horodatage, les comptes préparés une fois pour toutes.
Elle y écrit la taille de ce qu'elle produit. **Aucune étape ne connaît les
autres** : c'est `publier.py` qui les enchaîne.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import pathlib
import sqlite3


@dataclasses.dataclass
class Publication:
    cx: sqlite3.Connection
    sortie: pathlib.Path
    genere_le: str
    tailles: dict[str, int]
    # Préparés une fois, lus par plusieurs étapes.
    votes: dict
    descriptions: dict
    resumes_debats: dict
    legi_cx: sqlite3.Connection | None
    forme_seule: object
    change: dict
    senat_cx: sqlite3.Connection | None
    signets: dict[str, str]
    titres: dict[str, str]
    votes_senat: dict
    themes: dict[str, list[str]]
    etape_senat: dict
    en_cours_au_senat: set[str]
    compte_amendements: dict[str, int]
    compte_paroles: dict[str, int]
    comptes: dict[str, int]
    par_etape: dict
    # Rempli par les fiches, lu par les listes : les amendements adoptés dont
    # on connaît et le scrutin et le débat. C'est pour lui que les listes
    # s'écrivent après les fiches.
    mesurables: dict[str, list[dict]] = dataclasses.field(default_factory=dict)
