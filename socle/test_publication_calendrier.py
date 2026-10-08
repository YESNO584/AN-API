#!/usr/bin/env python3
"""Le calendrier : qui signe un texte, ce qui y entre en plus des lois, et les
moments de séance qu'aucun texte ne porte.

Ni réseau, ni vraie base : une base minuscule au schéma du projet.

    ./test_publication_calendrier.py
"""

import pathlib
import sqlite3
import sys
import unittest

from publication import calendrier as cal

SCHEMA = pathlib.Path(__file__).resolve().parent / "schema.sql"


def base() -> sqlite3.Connection:
    cx = sqlite3.connect(":memory:")
    cx.row_factory = sqlite3.Row
    cx.executescript(SCHEMA.read_text(encoding="utf-8"))
    cx.execute("INSERT INTO groupe VALUES ('PO1', 'DR', 'Droite républicaine', 8, 50, '#123456')")
    cx.executemany(
        "INSERT INTO acteur (ref, prenom, nom, groupe_ref) VALUES (?,?,?,?)",
        [("PA1", "Michel", "Barnier", "PO1"),      # Premier ministre, député aujourd'hui
         ("PA2", "Anne", "Députée", "PO1"),
         ("PA3", "Jean", "Sénateur", None)])
    return cx


def dossier(cx, uid, type_, type_document, auteur, est_loi=1):
    cx.execute(
        "INSERT INTO dossier (uid, legislature, titre, type, est_loi, statut,"
        " type_document, auteur_ref) VALUES (?, '17', ?, ?, ?, 'en_cours', ?, ?)",
        (uid, "Le texte " + uid, type_, est_loi, type_document, auteur))


def seance(cx, uid, date="2026-10-13"):
    cx.execute(
        "INSERT INTO etape (dossier_uid, code, libelle, chambre, date, rang, numero,"
        " future) VALUES (?, 'AN1-DEBATS-SEANCE', 'Discussion en séance publique',"
        " 'assemblee', ?, 0, 4, 0)", (uid, date))


class QuiSigne(unittest.TestCase):
    """L'auteur d'un texte et son groupe — ou rien, plutôt qu'un groupe faux."""

    def setUp(self):
        self.cx = base()

    def auteur(self, uid):
        return cal.auteurs_des_textes(self.cx).get(uid)

    def test_un_projet_de_loi_est_celui_du_gouvernement(self):
        """Même signé par un Premier ministre qui siège aujourd'hui au groupe
        DR : ce groupe ne l'a pas déposé."""
        dossier(self.cx, "D1", "Projet de loi ordinaire", "Projet de loi", "PA1")
        self.assertEqual(self.auteur("D1"), {"gouvernement": True})

    def test_le_type_du_document_tranche_quand_le_dossier_hesite(self):
        """« Projet ou proposition de loi organique » ne dit pas lequel des deux."""
        dossier(self.cx, "D2", "Projet ou proposition de loi organique",
                "Proposition de loi", "PA2")
        self.assertEqual(self.auteur("D2"), {"nom": "Anne Députée", "sigle": "DR",
                                             "groupe": "Droite républicaine",
                                             "couleur": "#123456"})

    def test_un_auteur_sans_groupe_garde_son_nom_seul(self):
        dossier(self.cx, "D3", "Proposition de loi ordinaire", "Proposition de loi", "PA3")
        self.assertEqual(self.auteur("D3"), {"nom": "Jean Sénateur"})

    def test_un_texte_sans_auteur_connu_n_en_porte_aucun(self):
        dossier(self.cx, "D4", "Proposition de loi ordinaire", "Proposition de loi", "PA9")
        self.assertIsNone(self.auteur("D4"))


class CeQuiEntre(unittest.TestCase):
    """Les lois, les résolutions, et les questions et débats de l'agenda."""

    def setUp(self):
        self.cx = base()
        dossier(self.cx, "LOI", "Proposition de loi ordinaire", "Proposition de loi", "PA2")
        dossier(self.cx, "RES", "Résolution Article 34-1", "Proposition de résolution",
                "PA2", est_loi=0)
        dossier(self.cx, "RAP", "Rapport d'information sans mission", None, None, est_loi=0)
        for uid in ("LOI", "RES", "RAP"):
            seance(self.cx, uid)

    def evenements(self):
        return [e for mois in cal.calendrier(self.cx).values() for e in mois]

    def test_une_resolution_entre_un_rapport_non(self):
        textes = {e.get("texte") for e in self.evenements()}
        self.assertEqual(textes & {"LOI", "RES", "RAP"}, {"LOI", "RES"})

    def test_chaque_ligne_de_texte_porte_son_auteur(self):
        for e in self.evenements():
            with self.subTest(texte=e.get("texte")):
                self.assertEqual(e["auteur"]["sigle"], "DR")

    def test_les_questions_et_les_debats_viennent_de_l_agenda(self):
        self.cx.execute(
            "INSERT INTO point_agenda VALUES ('RUAN1', 'P1', '2026-10-13', '15 h 00',"
            " 'questions', 'Questions au Gouvernement', 'Questions au Gouvernement')")
        e = [x for x in self.evenements() if x["genre"] == "questions"]
        self.assertEqual(len(e), 1)
        self.assertEqual((e[0]["heure"], e[0]["chambre"]), ("15 h 00", "assemblee"))
        self.assertNotIn("texte", e[0], "une question ne porte sur aucun texte")

    def test_une_base_d_avant_l_agenda_ne_casse_rien(self):
        """Une base construite avant la table — celle de la veille, gardée en
        cache — doit encore se publier, simplement sans questions ni débats."""
        self.cx.execute("DROP TABLE point_agenda")
        self.assertTrue(self.evenements())


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
