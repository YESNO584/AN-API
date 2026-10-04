#!/usr/bin/env python3
"""Ce qui construit `senat.db`. Ni réseau, ni vraie archive.

    ./test_recuperer_senat.py
"""

import pathlib
import sqlite3
import sys
import unittest

import recuperer_senat as rs

SCHEMA = pathlib.Path(__file__).resolve().parent / "schema_senat.sql"


def base() -> sqlite3.Connection:
    cx = sqlite3.connect(":memory:")
    cx.row_factory = sqlite3.Row
    cx.executescript(SCHEMA.read_text(encoding="utf-8"))
    return cx


class LaSessionEnCours(unittest.TestCase):
    """Une session parlementaire commence en octobre et porte l'année d'avant."""

    def test_octobre_ouvre_la_session_de_l_annee(self):
        import datetime as dt
        self.assertEqual(rs.session_en_cours(dt.date(2026, 10, 1)), 2026)
        self.assertEqual(rs.session_en_cours(dt.date(2026, 12, 31)), 2026)

    def test_avant_octobre_on_est_encore_dans_la_precedente(self):
        import datetime as dt
        self.assertEqual(rs.session_en_cours(dt.date(2026, 6, 4)), 2025)
        self.assertEqual(rs.session_en_cours(dt.date(2026, 9, 30)), 2025)


class LeGroupeAuJourDuScrutin(unittest.TestCase):
    """Un sénateur change de groupe : lui donner celui d'aujourd'hui ferait
    dire au passé ce qu'il n'a pas dit."""

    HISTO = {"01": [("2020-01-01", "2023-06-30", "SOC", "Groupe socialiste"),
                    ("2023-07-01", "", "UMP", "Groupe Les Républicains")]}

    def test_le_groupe_depend_de_la_date(self):
        self.assertEqual(rs.groupe_au(self.HISTO, "01", "2022-05-01"), "SOC")
        self.assertEqual(rs.groupe_au(self.HISTO, "01", "2024-05-01"), "UMP")

    def test_une_appartenance_en_cours_n_a_pas_de_fin(self):
        self.assertEqual(rs.groupe_au(self.HISTO, "01", "2099-01-01"), "UMP")

    def test_aucun_n_est_pas_un_groupe(self):
        """179 sénateurs sur 348 n'en ont plus depuis le renouvellement :
        les compter ensemble en ferait un dixième groupe, qui n'existe pas."""
        histo = {"02": [("", "", "AUCUN", "Sénateurs n'appartenant à aucun groupe")]}
        self.assertIsNone(rs.groupe_au(histo, "02", "2026-10-04"))

    def test_un_matricule_inconnu_ne_rend_rien(self):
        self.assertIsNone(rs.groupe_au(self.HISTO, "99", "2024-01-01"))
        self.assertIsNone(rs.groupe_au(self.HISTO, None, "2024-01-01"))


class NommerUnGroupe(unittest.TestCase):
    """Les deux fichiers du Sénat ne nomment pas les groupes pareil, et leurs
    codes sont périmés : `UMP` désigne Les Républicains."""

    HISTO = {"01": [("", "", "UMP", "Groupe Les Républicains")],
             "02": [("", "2015-01-01", "CRC", "Groupe communiste")]}

    def test_l_etiquette_courte_vient_du_fichier_des_senateurs(self):
        noms = rs.noms_des_groupes(
            self.HISTO, [{"Matricule": "01", "Groupe politique": "Les Républicains"}])
        self.assertEqual(noms["UMP"], "Les Républicains")

    def test_un_groupe_sans_membre_en_exercice_garde_le_nom_de_la_source(self):
        noms = rs.noms_des_groupes(self.HISTO, [])
        self.assertEqual(noms["CRC"], "Groupe communiste")

    def test_aucun_n_est_jamais_nomme(self):
        histo = {"03": [("", "", "AUCUN", "Sénateurs n'appartenant à aucun groupe")]}
        self.assertNotIn("AUCUN", rs.noms_des_groupes(histo, []))


class RelireUnePartieDesSessions(unittest.TestCase):
    """Le défaut du 2026-10-04 : relire quatre vieilles sessions effaçait le
    lien vers le dossier de toutes les autres — 666 scrutins rattachés, puis
    zéro depuis 2024."""

    def test_une_session_non_relue_garde_ses_liens(self):
        cx = base()
        cx.execute("INSERT INTO scrutin_senat (session, numero, signet, date)"
                   " VALUES (2025, 340, 'pjl25-689', '2026-07-21')")
        cx.execute("INSERT INTO scrutin_senat (session, numero, signet, date)"
                   " VALUES (2020, 10, 'ppl20-001', '2021-01-05')")
        # On refait une passe qui ne lit que la session 2020.
        liens = {(2020, 10): "ppl20-002"}
        lues = {2020}
        cx.executemany(
            "UPDATE scrutin_senat SET signet = ? WHERE session = ? AND numero = ?",
            [(sig, s, n) for (s, n), sig in liens.items() if s in lues])
        garde = cx.execute("SELECT signet FROM scrutin_senat"
                           " WHERE session = 2025").fetchone()["signet"]
        self.assertEqual(garde, "pjl25-689",
                         "la session non relue a perdu son lien")
        self.assertEqual(cx.execute("SELECT signet FROM scrutin_senat"
                                    " WHERE session = 2020").fetchone()["signet"],
                         "ppl20-002")


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
