#!/usr/bin/env python3
"""`recherche.json` : ce que la recherche lit en plus du titre.

Ni réseau, ni vraie base : une base minuscule au schéma du projet.

    ./test_publication_recherche.py
"""

import json
import pathlib
import sqlite3
import sys
import tempfile
import types
import unittest

from publication import recherche

SCHEMA = pathlib.Path(__file__).resolve().parent / "schema.sql"


def publication(descriptions: dict, dossiers=("D1", "D2")):
    cx = sqlite3.connect(":memory:")
    cx.row_factory = sqlite3.Row
    cx.executescript(SCHEMA.read_text(encoding="utf-8"))
    for uid in dossiers:
        cx.execute("INSERT INTO dossier (uid, legislature, titre, type, est_loi, statut)"
                   " VALUES (?, '17', 'Un titre', 'Proposition de loi ordinaire', 1, 'en_cours')",
                   (uid,))
    return types.SimpleNamespace(cx=cx, sortie=pathlib.Path(tempfile.mkdtemp()),
                                 genere_le="2026-10-14T06:00:00+00:00", tailles={},
                                 descriptions=descriptions)


def publie(p) -> dict:
    recherche.ecrire_recherche(p)
    return json.loads((p.sortie / "recherche.json").read_text(encoding="utf-8"))


class CeQueLaRechercheLit(unittest.TestCase):

    def test_tout_ce_que_la_fiche_affiche_de_la_description(self):
        """Le nom d'usage, l'accroche, le contexte et chaque point : un mot
        lu sur la fiche doit pouvoir se chercher."""
        d = {"nomUsage": {"nom": "loi Ripost", "citations": 12},
             "accroche": "Renforce les peines.", "contexte": "Avant, rien.",
             "points": ["Un point.", " Un autre. "], "origine": "ia"}
        self.assertEqual(recherche.mots_de_la_description(d),
                         "loi Ripost Renforce les peines. Avant, rien. Un point. Un autre.")

    def test_le_texte_est_publie_tel_quel(self):
        """Accents, casse et apostrophes restent : la maquette les ignore avec
        la même règle que pour le titre, et une seule règle vaut mieux que deux."""
        d = {"accroche": "L’Œuvre d’État", "points": []}
        self.assertEqual(recherche.mots_de_la_description(d), "L’Œuvre d’État")

    def test_seuls_les_textes_connus_y_figurent(self):
        p = publication({"D1": {"accroche": "Un.", "points": []},
                         "D9": {"accroche": "Disparu.", "points": []}})
        self.assertEqual(publie(p)["descriptions"], {"D1": "Un."})

    def test_un_texte_sans_description_n_y_figure_pas(self):
        p = publication({"D1": {"accroche": "Un.", "points": []}})
        contenu = publie(p)
        self.assertNotIn("D2", contenu["descriptions"])
        self.assertEqual(contenu["total"], 1)
        self.assertIn("recherche.json", p.tailles)


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
