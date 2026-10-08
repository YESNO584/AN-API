"""Un scrutin public : sur quoi il porte, ce que chaque groupe a fait, à quel texte il se rattache.

    ./test_extraction_scrutins.py
"""
from __future__ import annotations

import sys
import unittest
import unittest.mock
import extraction
from decor_extraction import acte, dossier, scrutin


class PorteeDuVote(unittest.TestCase):
    """Sur quoi porte le vote — 7 216 des 8 434 scrutins de la législature
    portent sur un amendement, 212 seulement sur un texte entier. Les
    confondre laisserait croire qu'un texte a été adopté alors qu'un seul de
    ses amendements l'a été."""

    def test_les_cas_reels_sont_bien_classes(self):
        cas = [
            ("l'ensemble de la proposition de loi sur le remboursement…", extraction.ENSEMBLE),
            ("l'amendement n° 770 de Mme Parmentier à l'article premier…", extraction.AMENDEMENT),
            ("l'article 9 du projet de loi sur la justice criminelle…", extraction.ARTICLE),
            ("la motion de censure déposée en application de l'article 49…", extraction.MOTION),
            ("la motion de rejet préalable, déposée par Mme Panot…", extraction.MOTION),
            ("la demande de suspension de séance présentée par M. Lachaud…", extraction.AUTRE),
            ("la deuxième partie du projet de loi de financement…", extraction.ARTICLE),
        ]
        for libelle, attendu in cas:
            with self.subTest(libelle=libelle[:40]):
                self.assertEqual(extraction.classer_portee(libelle), attendu)

    def test_un_amendement_n_est_pas_un_vote_sur_le_texte(self):
        v = extraction.analyser_scrutin(
            scrutin("l'amendement n° 12 à l'ensemble du projet de loi"))
        self.assertEqual(v["portee"], extraction.AMENDEMENT,
                         "« l'ensemble » plus loin dans la phrase ne doit pas tromper")


class PositionDesGroupes(unittest.TestCase):
    """La position annoncée par la source contredit son propre décompte dans
    3 % des cas (3 033 sur 101 208, mesuré le 2026-08-31). On la recalcule."""

    def test_la_position_vient_du_decompte_pas_de_l_annonce(self):
        v = extraction.analyser_scrutin(scrutin(
            "l'ensemble de la proposition de loi",
            groupes=[("PO1", 20, "pour", 2, 16, 0)]),   # annoncé « pour », 16 contre
            {"PO1": ("RN", "Rassemblement National")})
        g = v["groupes"][0]
        self.assertEqual(g["position"], "contre")
        self.assertEqual((g["pour"], g["contre"], g["abstentions"]), (2, 16, 0))
        self.assertEqual(g["sigle"], "RN")

    def test_une_egalite_est_dite_partagee(self):
        self.assertEqual(extraction.position_dominante(5, 5, 0), "partagé")

    def test_un_groupe_qui_n_a_pas_vote_n_a_pas_de_position(self):
        self.assertIsNone(extraction.position_dominante(0, 0, 0))

    def test_l_abstention_peut_l_emporter(self):
        self.assertEqual(extraction.position_dominante(3, 2, 10), "abstention")

    def test_un_groupe_inconnu_garde_son_identifiant(self):
        v = extraction.analyser_scrutin(
            scrutin("l'ensemble", groupes=[("PO9", 5, "pour", 5, 0, 0)]), {})
        self.assertEqual(v["groupes"][0]["sigle"], "PO9")


class RattachementDesVotes(unittest.TestCase):
    """Le lien entre un vote et un texte se lit dans les deux sens, et aucun
    ne suffit seul : 34 textes en cours par le scrutin, 68 par le dossier,
    71 en réunissant les deux."""

    def test_le_scrutin_peut_nommer_son_dossier(self):
        v = extraction.analyser_scrutin(scrutin("l'ensemble", dossier="D1"))
        self.assertEqual(v["dossier"], "D1")

    def test_un_scrutin_sans_dossier_ne_l_invente_pas(self):
        self.assertIsNone(extraction.analyser_scrutin(scrutin("l'ensemble"))["dossier"])

    def test_le_dossier_peut_citer_ses_scrutins(self):
        d = dossier(
            acte("AN1-DEPOT", "2026-01-06", xsi="DepotInitiative_Type"),
            acte("AN1-DEBATS-DEC", "2026-03-11", voteRefs={"voteRef": "V42"}),
        )["dossierParlementaire"]
        self.assertEqual(extraction.refs_de_vote(d), {"V42"})

    def test_plusieurs_scrutins_cites_par_un_meme_acte(self):
        d = dossier(acte("AN1-DEBATS-DEC", "2026-03-11",
                         voteRefs={"voteRef": ["V1", "V2"]}))["dossierParlementaire"]
        self.assertEqual(extraction.refs_de_vote(d), {"V1", "V2"})

    def test_un_dossier_sans_vote_ne_rend_rien(self):
        d = dossier(acte("AN1-DEPOT", "2026-01-06"))["dossierParlementaire"]
        self.assertEqual(extraction.refs_de_vote(d), set())


class DecompteDuScrutin(unittest.TestCase):
    def test_les_chiffres_sont_des_nombres_pas_du_texte(self):
        v = extraction.analyser_scrutin(
            scrutin("l'ensemble", pour=105, contre=56, abstentions=4))
        self.assertEqual((v["pour"], v["contre"], v["abstentions"]), (105, 56, 4))
        self.assertEqual(v["votants"], 100)

    def test_un_chiffre_absent_devient_None_et_ne_casse_rien(self):
        brut = scrutin("l'ensemble")
        brut["scrutin"]["syntheseVote"]["decompte"]["pour"] = None
        self.assertIsNone(extraction.analyser_scrutin(brut)["pour"])

    def test_un_scrutin_sans_ventilation_reste_lisible(self):
        v = extraction.analyser_scrutin(scrutin("l'ensemble", groupes=()))
        self.assertEqual(v["groupes"], [])
        self.assertEqual(v["sort"], "adopté")


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
