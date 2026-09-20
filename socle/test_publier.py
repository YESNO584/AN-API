#!/usr/bin/env python3
"""Vérifie le rattachement d'un scrutin et d'un débat à un amendement adopté.

Ni réseau, ni vraie base : une base minuscule au schéma du projet, et un cas
par défaut constaté le 2026-09-20 sur les vraies données.

    ./test_publier.py
"""

import pathlib
import sqlite3
import sys
import unittest

import publier

SCHEMA = pathlib.Path(__file__).resolve().parent / "schema.sql"

# Les deux textes de commission d'un même dossier : une première lecture, puis
# la commission mixte paritaire. C'est le décor du piège — les deux numérotent
# leurs amendements à partir de 1.
BTC_PREMIERE = "PRJLANR5L17BTC2984"
BTC_CMP = "PRJLANR5L17BTC3070"


def base() -> sqlite3.Connection:
    cx = sqlite3.connect(":memory:")
    cx.row_factory = sqlite3.Row
    cx.executescript(SCHEMA.read_text(encoding="utf-8"))
    cx.execute(
        "INSERT INTO dossier (uid, legislature, titre, type, est_loi, statut)"
        " VALUES ('D1', '17', 'Un projet de loi', 'Projet de loi ordinaire',"
        " 1, 'en_cours')")
    return cx


def amendement(cx, numero, texte_ref, article="Article 3", ordre=1):
    cx.execute(
        "INSERT INTO amendement (uid, dossier_uid, numero, ordre, article,"
        " texte_ref, ou, division, sort) VALUES (?,?,?,?,?,?,'A','ARTICLE','Adopté')",
        (f"AM{numero}{texte_ref}", "D1", numero, ordre, article, texte_ref))


def scrutin(cx, uid, date, objet, pour, contre):
    cx.execute(
        "INSERT INTO vote (uid, dossier_uid, date, numero, portee, objet, sort,"
        " pour, contre, abstentions) VALUES (?,?,?,?, 'amendement', ?, 'adopté', ?, ?, 0)",
        (uid, "D1", date, 1, objet, pour, contre))


def debat(cx, texte_numero, numero, orateurs, paragraphes=40):
    cx.execute(
        "INSERT INTO debat_amendement VALUES (?,?,?,?,?,?,?)",
        ("D1", texte_numero, numero, "CR1", "2026-07-09", orateurs, paragraphes))


def adoptes(cx, ref, fenetre=None):
    """Les amendements adoptés sur `ref`, à plat, par numéro."""
    index = publier.amendements_adoptes(
        cx, ref, publier.votes_par_amendement(cx, "D1"),
        publier.debats_par_amendement(cx, "D1"), fenetre)
    return {a["numero"]: a for liste in index.values() for a in liste}


class LeNumeroDuDocument(unittest.TestCase):
    def test_il_se_lit_a_la_fin_de_la_reference(self):
        self.assertEqual(publier.numero_de_document(BTC_PREMIERE), "2984")

    def test_les_zeros_de_tete_tombent(self):
        """La séance dit « n° 224 », la référence écrit « BTA0224 »."""
        self.assertEqual(publier.numero_de_document("PIONANR5L17BTA0224"), "224")

    def test_une_reference_sans_chiffre_ne_donne_rien(self):
        self.assertEqual(publier.numero_de_document(None), "")
        self.assertEqual(publier.numero_de_document("SANSNUMERO"), "")


class LeScrutinDUnAmendement(unittest.TestCase):
    def test_l_objet_du_scrutin_nomme_l_amendement(self):
        cx = base()
        amendement(cx, "885 (Rect)", BTC_PREMIERE)
        scrutin(cx, "V1", "2026-07-09",
                "l'amendement n° 885 (rect.) du Gouvernement à l'article 3", 39, 37)
        vote = adoptes(cx, BTC_PREMIERE)["885 (Rect)"]["vote"]
        self.assertEqual((vote["pour"], vote["contre"]), (39, 37))
        # 2 voix sur 76 suffrages exprimés.
        self.assertEqual(vote["ecart"], 0.0263)

    def test_seul_le_premier_amendement_nomme_recoit_le_vote(self):
        """« et les amendements identiques suivants » ne dit pas lesquels."""
        cx = base()
        amendement(cx, "914", BTC_PREMIERE)
        amendement(cx, "915", BTC_PREMIERE, ordre=2)
        scrutin(cx, "V1", "2026-07-09",
                "l'amendement n° 914 du Gouvernement et les amendements "
                "identiques suivants de rétablissement de l'article 24", 28, 0)
        tous = adoptes(cx, BTC_PREMIERE)
        self.assertIn("vote", tous["914"])
        self.assertNotIn("vote", tous["915"])

    def test_la_date_departage_deux_lectures_qui_numerotent_pareil(self):
        """69 couples (dossier, numéro) sur 4 372 sont portés par deux
        documents du même dossier. Sans la fenêtre de dates, le scrutin de la
        première lecture s'affichait aussi sur l'amendement de la CMP."""
        cx = base()
        amendement(cx, "1", BTC_PREMIERE)
        amendement(cx, "1", BTC_CMP)
        scrutin(cx, "V1", "2026-07-15", "l'amendement n° 1 du Gouvernement", 148, 68)
        premiere = adoptes(cx, BTC_PREMIERE, ("2026-06-24", "2026-07-15"))
        cmp = adoptes(cx, BTC_CMP, ("2026-07-20", "2026-07-21"))
        self.assertIn("vote", premiere["1"])
        self.assertNotIn("vote", cmp["1"])

    def test_deux_scrutins_dans_la_meme_fenetre_n_en_donnent_aucun(self):
        """Mieux vaut ne rien afficher que le mauvais décompte."""
        cx = base()
        amendement(cx, "1", BTC_PREMIERE)
        scrutin(cx, "V1", "2026-07-09", "l'amendement n° 1 du Gouvernement", 148, 68)
        scrutin(cx, "V2", "2026-07-10", "l'amendement n° 1 de M. Untel", 20, 19)
        self.assertNotIn(
            "vote", adoptes(cx, BTC_PREMIERE, ("2026-06-24", "2026-07-15"))["1"])

    def test_un_scrutin_sans_suffrage_exprime_n_a_pas_d_ecart(self):
        cx = base()
        amendement(cx, "12", BTC_PREMIERE)
        scrutin(cx, "V1", "2026-07-09", "l'amendement n° 12 de M. Untel", 0, 0)
        self.assertNotIn("vote", adoptes(cx, BTC_PREMIERE)["12"])


class LeDebatDUnAmendement(unittest.TestCase):
    def test_le_compte_d_orateurs_suit_le_document_amende(self):
        cx = base()
        amendement(cx, "885 (Rect)", BTC_PREMIERE)
        debat(cx, "2984", "885", orateurs=15, paragraphes=58)
        self.assertEqual(adoptes(cx, BTC_PREMIERE)["885 (Rect)"]["debat"],
                         {"orateurs": 15, "paragraphes": 58})

    def test_le_debat_d_un_autre_document_ne_deborde_pas(self):
        """Le même numéro sur le texte de la CMP ne reprend pas le compte de
        la première lecture."""
        cx = base()
        amendement(cx, "1", BTC_CMP)
        debat(cx, "2984", "1", orateurs=15)
        self.assertNotIn("debat", adoptes(cx, BTC_CMP)["1"])

    def test_un_amendement_de_commission_ne_trouve_rien(self):
        """« CL755 » n'a ni scrutin en séance ni débat : il ne doit pas
        attraper le scrutin de l'amendement n° 755."""
        cx = base()
        amendement(cx, "CL755", BTC_PREMIERE)
        scrutin(cx, "V1", "2026-07-09", "l'amendement n° 755 de M. Untel", 30, 29)
        debat(cx, "2984", "755", orateurs=12)
        seul = adoptes(cx, BTC_PREMIERE)["CL755"]
        self.assertNotIn("vote", seul)
        self.assertNotIn("debat", seul)

    def test_un_amendement_sans_rien_reste_affichable(self):
        """97 % des amendements adoptés le sont à main levée : leur ligne doit
        s'afficher quand même, sans scrutin ni débat."""
        cx = base()
        amendement(cx, "42", BTC_PREMIERE)
        seul = adoptes(cx, BTC_PREMIERE)["42"]
        self.assertEqual(seul["numero"], "42")
        self.assertNotIn("vote", seul)
        self.assertNotIn("debat", seul)


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
