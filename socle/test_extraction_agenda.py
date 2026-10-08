#!/usr/bin/env python3
"""L'agenda : les questions au Gouvernement et les débats, que seul l'agenda
publie, et les votes solennels qu'il annonce.

    ./test_extraction_agenda.py
"""
from __future__ import annotations

import sys
import unittest
import extraction


def point(type_point, etat="Confirmé", objet=None, uid="P1"):
    return {"uid": uid, "typePointODJ": type_point, "cycleDeVie": {"etat": etat},
            "objet": objet if objet is not None else type_point}


def seance(*points, uid="RUANR5L17S2026IDS30001", etat="Confirmé",
           debut="2026-10-13T15:00:00.000+02:00", xsi="seance_type"):
    # Un seul point arrive en objet, plusieurs en liste : la source fait ainsi.
    contenu = points[0] if len(points) == 1 else list(points)
    return {"@xsi:type": xsi, "uid": uid, "timeStampDebut": debut,
            "cycleDeVie": {"etat": etat},
            "ODJ": {"pointsODJ": {"pointODJ": contenu}}}


class CeQuiEntre(unittest.TestCase):
    """Les trois types de point qu'aucun dossier ne porte, et eux seuls."""

    def test_questions_et_debats_d_une_seance_tenue(self):
        points = extraction.points_de_seance(seance(
            point("Questions au Gouvernement", uid="P1"),
            point("Débat d'initiative parlementaire", uid="P2",
                  objet="Débat sur le thème : « La politique du logement »"),
            point("Déclaration du Gouvernement suivie d'un débat", uid="P3")))
        self.assertEqual([p["genre"] for p in points], ["questions", "debat", "debat"])
        self.assertEqual(points[1]["objet"],
                         "Débat sur le thème : « La politique du logement »",
                         "l'intitulé est celui de la source, mot pour mot")
        self.assertEqual((points[0]["date"], points[0]["heure"]),
                         ("2026-10-13", "15 h 00"))

    def test_un_point_seul_arrive_en_objet_et_non_en_liste(self):
        points = extraction.points_de_seance(seance(point("Questions au Gouvernement")))
        self.assertEqual(len(points), 1)

    def test_une_discussion_de_texte_n_entre_pas(self):
        """Le parcours de son dossier la porte déjà : la reprendre la doublerait."""
        for t in ("Discussion", "Suite de la discussion",
                  "Questions orales sans débat", "Ouverture et clôture de session"):
            with self.subTest(type=t):
                self.assertEqual(extraction.points_de_seance(seance(point(t))), [])


class LesVotesSolennels(unittest.TestCase):
    """Le seul point retenu qui peut désigner un texte — par le lien que la
    source publie, et par rien d'autre."""

    def test_un_vote_passe_porte_le_dossier_que_la_source_designe(self):
        p = point("Vote solennel")
        p["dossiersLegislatifsRefs"] = {"dossierRef": "DLR5L17N52100"}
        (v,) = extraction.points_de_seance(seance(p))
        self.assertEqual((v["genre"], v["dossier"]), ("vote_solennel", "DLR5L17N52100"))

    def test_un_vote_annonce_sans_lien_ne_designe_aucun_texte(self):
        """Les votes à venir n'ont que leur intitulé : on ne cherche pas le
        texte par son titre."""
        (v,) = extraction.points_de_seance(seance(point(
            "Vote solennel", objet="Vote solennel sur le projet de loi de finances pour 2027")))
        self.assertIsNone(v["dossier"])

    def test_plusieurs_dossiers_le_premier_compte(self):
        p = point("Vote solennel")
        p["dossiersLegislatifsRefs"] = {"dossierRef": ["D1", "D2"]}
        (v,) = extraction.points_de_seance(seance(p))
        self.assertEqual(v["dossier"], "D1")


class CeQuiNEntrePas(unittest.TestCase):
    """Ce qui n'a pas eu lieu, ou pas à l'Assemblée."""

    def test_une_seance_supprimee_n_a_pas_eu_lieu(self):
        self.assertEqual(extraction.points_de_seance(seance(
            point("Questions au Gouvernement"), etat="Supprimé")), [])

    def test_un_point_supprime_a_ete_retire_ou_reporte(self):
        points = extraction.points_de_seance(seance(
            point("Questions au Gouvernement", etat="Supprimé", uid="P1"),
            point("Débat d'initiative parlementaire", uid="P2")))
        self.assertEqual([p["point"] for p in points], ["P2"])

    def test_une_seance_du_senat_n_entre_pas(self):
        """L'archive porte aussi 148 séances du Sénat : elles ne sont pas
        celles de l'Assemblée, quel que soit leur ordre du jour."""
        self.assertEqual(extraction.points_de_seance(seance(
            point("Questions au Gouvernement"), uid="RUSNR5L17S2026IDS30898")), [])

    def test_une_reunion_de_commission_n_entre_pas(self):
        self.assertEqual(extraction.points_de_seance(seance(
            point("Questions au Gouvernement"), xsi="reunionCommission_type",
            uid="RUANR5L17S2026IDC450000")), [])


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
