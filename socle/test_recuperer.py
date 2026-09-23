#!/usr/bin/env python3
"""Vérifie ce qui protège les deux archives facultatives.

Deux règles, nées de la même panne : le 2026-09-23, l'archive des amendements
a répondu « 504 » après cinquante secondes, et trois publications sur six y ont
perdu les 110 000 amendements du site pour la journée.

1. Une source facultative se redemande avant d'être déclarée absente.
2. Une source absente n'emporte plus les lignes de la veille avec elle.

Ni réseau, ni vraie base.

    ./test_recuperer.py
"""

import pathlib
import sqlite3
import sys
import unittest

import recuperer

SCHEMA = pathlib.Path(__file__).resolve().parent / "schema.sql"


def base(dossiers=("D1",)) -> sqlite3.Connection:
    cx = sqlite3.connect(":memory:")
    cx.row_factory = sqlite3.Row
    cx.executescript(SCHEMA.read_text(encoding="utf-8"))
    for uid in dossiers:
        cx.execute(
            "INSERT INTO dossier (uid, legislature, titre, type, est_loi, statut)"
            " VALUES (?, '17', 'Un projet de loi', 'Projet de loi ordinaire',"
            " 1, 'en_cours')", (uid,))
    return cx


def amendement(cx, uid, dossier="D1"):
    cx.execute("INSERT INTO amendement (uid, dossier_uid, numero, sort)"
               " VALUES (?,?,?, 'Adopté')", (uid, dossier, uid))


def parole(cx, ordre, dossier="D1"):
    cx.execute("INSERT INTO parole VALUES (?,'CR1','2026-07-09','Discussion"
               " générale',?,'PA1','Une députée','rapporteure','RN','Merci.')",
               (dossier, ordre))


def debat(cx, numero, dossier="D1"):
    cx.execute("INSERT INTO debat_amendement VALUES (?,'2984',?,'CR1',"
               "'2026-07-09',9,40)", (dossier, numero))


class RedemanderUneSourceFacultative(unittest.TestCase):
    """Un seul essai faisait perdre les amendements de toute la journée pour
    une minute d'indisponibilité chez eux."""

    def telecharger(self, reponses):
        """Un faux téléchargement qui joue `reponses` dans l'ordre : une
        exception se lève, tout le reste se renvoie."""
        essais = []

        def faux(chemin, entetes, url):
            essais.append(url)
            reponse = reponses[len(essais) - 1]
            if isinstance(reponse, Exception):
                raise reponse
            return reponse

        return faux, essais

    def insister(self, nom, reponses):
        faux, essais = self.telecharger(reponses)
        vrai = recuperer.extraction.telecharger
        recuperer.extraction.telecharger = faux
        dodos = []
        try:
            return recuperer.telecharger_en_insistant(
                nom, pathlib.Path("/rien"), {}, "u", dormir=dodos.append), essais, dodos
        finally:
            recuperer.extraction.telecharger = vrai

    def test_une_source_obligatoire_echoue_tout_de_suite(self):
        """Sans elle il n'y a rien à publier : insister ne ferait que retarder
        l'erreur."""
        with self.assertRaises(OSError):
            self.insister("dossiers", [OSError("504")])

    def test_une_source_facultative_est_redemandee(self):
        (reponse, essais, dodos) = self.insister(
            "amendements", [OSError("504"), {"statut": 200}])
        self.assertEqual(reponse, {"statut": 200})
        self.assertEqual(len(essais), 2)
        self.assertEqual(dodos, [recuperer.PAUSE_ENTRE_ESSAIS])

    def test_elle_n_est_pas_redemandee_indefiniment(self):
        with self.assertRaises(OSError):
            self.insister("debats", [OSError("504")] * recuperer.ESSAIS_FACULTATIVE)

    def test_le_premier_essai_reussi_est_le_dernier(self):
        """Ce qui marche du premier coup ne se redemande pas."""
        (_, essais, dodos) = self.insister("amendements", [{"statut": 200}])
        self.assertEqual(len(essais), 1)
        self.assertEqual(dodos, [])


class GarderLesLignesDeLaVeille(unittest.TestCase):
    """La base se reconstruit de fond en comble ; une archive absente n'a rien
    pour réécrire ce qu'on vient d'effacer."""

    ARCHIVES = {n: pathlib.Path("/rien") for n in recuperer.SOURCES}

    def test_rien_n_est_repris_quand_tout_est_arrive(self):
        cx = base()
        amendement(cx, "AM1")
        self.assertEqual(recuperer.a_reprendre(cx, self.ARCHIVES), {})

    def test_l_archive_des_amendements_absente_les_met_de_cote(self):
        cx = base()
        amendement(cx, "AM1")
        parole(cx, 1)
        archives = {n: c for n, c in self.ARCHIVES.items() if n != "amendements"}
        repris = recuperer.a_reprendre(cx, archives)
        self.assertEqual(list(repris), ["amendement"])
        self.assertEqual(len(repris["amendement"]), 1)

    def test_l_archive_des_debats_absente_met_de_cote_ses_deux_tables(self):
        """Les prises de parole et le compte d'orateurs viennent du même
        fichier : l'un ne survit pas sans l'autre."""
        cx = base()
        parole(cx, 1)
        debat(cx, "885")
        archives = {n: c for n, c in self.ARCHIVES.items() if n != "debats"}
        repris = recuperer.a_reprendre(cx, archives)
        self.assertEqual(sorted(repris), ["debat_amendement", "parole"])

    def test_les_lignes_reviennent_apres_l_effacement(self):
        cx = base()
        amendement(cx, "AM1")
        repris = recuperer.a_reprendre(
            cx, {n: c for n, c in self.ARCHIVES.items() if n != "amendements"})
        cx.execute("DELETE FROM amendement")
        recuperer.reposer(cx, repris, {"D1"})
        self.assertEqual(
            [l["uid"] for l in cx.execute("SELECT uid FROM amendement")], ["AM1"])

    def test_un_dossier_disparu_ne_ressuscite_pas_par_ses_amendements(self):
        """Ce qui revient est filtré sur les dossiers que l'archive porte encore."""
        cx = base(("D1", "D2"))
        amendement(cx, "AM1", "D1")
        amendement(cx, "AM2", "D2")
        repris = recuperer.a_reprendre(
            cx, {n: c for n, c in self.ARCHIVES.items() if n != "amendements"})
        cx.execute("DELETE FROM dossier WHERE uid = 'D2'")
        cx.execute("DELETE FROM amendement")
        gardees = recuperer.reposer(cx, repris, {"D1"})
        self.assertEqual([l["uid"] for l in cx.execute("SELECT uid FROM amendement")],
                         ["AM1"])
        self.assertEqual(len(gardees["amendement"]), 1)

    def test_effacer_le_dossier_emporte_ses_amendements_en_cascade(self):
        """Pourquoi « ne pas effacer la table » n'aurait pas suffi : les lignes
        pendent au dossier par une clé étrangère en cascade."""
        cx = base()
        cx.execute("PRAGMA foreign_keys = ON")
        amendement(cx, "AM1")
        parole(cx, 1)
        cx.execute("DELETE FROM dossier")
        self.assertEqual(
            cx.execute("SELECT COUNT(*) n FROM amendement").fetchone()["n"], 0)
        self.assertEqual(
            cx.execute("SELECT COUNT(*) n FROM parole").fetchone()["n"], 0)


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
