#!/usr/bin/env python3
"""Les règles d'affichage : ce qui sort à l'écran, jamais ce qui entre en base.

Elles vivent dans `affichage.py` pour que le cache de `parlement.db` cesse de
se jeter quand une formulation change — voir l'en-tête de ce fichier-là.

    ./test_affichage.py
"""

import sys
import unittest

import affichage


class LeCalendrier(unittest.TestCase):
    """Ce qui mérite une ligne au calendrier, et ce qui n'en mérite pas."""

    def test_les_moments_ou_le_parlement_se_reunit_et_decide(self):
        for code, genre in (("AN1-DEBATS-SEANCE", "seance"),
                            ("SN2-DEBATS-SEANCE", "seance"),
                            ("AN1-DEBATS-DEC", "decision"),
                            ("SN1-DEBATS-DEC", "decision"),
                            ("AN1-COM-FOND-REUNION", "commission"),
                            ("AN1-COM-AVIS-REUNION", "commission"),
                            ("PROM-PUB", "promulgation")):
            self.assertEqual(affichage.genre_d_evenement(code), genre, code)

    def test_un_acte_administratif_n_a_rien_a_faire_dans_un_calendrier(self):
        """Un dépôt, un renvoi, une nomination : ni heure, ni public, rien à
        suivre en direct."""
        for code in ("AN1-DEPOT", "SN1-DEPOT", "AN1-COM-FOND-SAISIE",
                     "AN1-COM-FOND-NOMIN", "AN1-COM-FOND-RAPPORT", "AN20-RAPPORT"):
            self.assertIsNone(affichage.genre_d_evenement(code), code)

    def test_la_chambre_et_la_lecture_ne_changent_pas_le_genre(self):
        """Le code porte la chambre et la lecture en préfixe : on reconnaît la
        fin du code, pas le code entier."""
        self.assertEqual(affichage.genre_d_evenement("AN3-DEBATS-SEANCE"),
                         affichage.genre_d_evenement("SN1-DEBATS-SEANCE"))

    def test_un_code_vide_ne_plante_pas(self):
        self.assertIsNone(affichage.genre_d_evenement(""))
        self.assertIsNone(affichage.genre_d_evenement(None))

    def test_seuls_les_votes_qui_decident_sont_au_calendrier(self):
        """Sur 2 748 votes rattachés à un texte, 2 260 portent sur un
        amendement (mesuré le 2026-09-02). Les afficher noierait le calendrier
        sous des scrutins de détail, alors que la séance du jour les porte
        déjà."""
        self.assertIn("ensemble", affichage.VOTES_AU_CALENDRIER)
        self.assertIn("motion", affichage.VOTES_AU_CALENDRIER)
        self.assertNotIn("amendement", affichage.VOTES_AU_CALENDRIER)
        self.assertNotIn("article", affichage.VOTES_AU_CALENDRIER)

class LesEtapesDuSenat(unittest.TestCase):
    """Le Sénat découpe le parcours à sa façon, et on ne l'aligne pas sur celui
    de l'Assemblée."""

    def test_le_code_donne_le_moment(self):
        self.assertEqual(affichage.moment_au_senat("SN1-COM-FOND-RAPPORT"),
                         "rapport")
        self.assertEqual(affichage.moment_au_senat("SN1-DEBATS-DEC"), "decision")
        self.assertEqual(affichage.moment_au_senat("SN1-DEPOT"), "depot")

    def test_la_lecture_ne_change_pas_le_moment(self):
        """Première, deuxième et nouvelle lecture passent par les mêmes
        étapes : c'est ce qui permet cinq colonnes au lieu de quinze."""
        for prefixe in ("SN1", "SN2", "SNNLEC"):
            self.assertEqual(
                affichage.moment_au_senat(f"{prefixe}-DEBATS-DEC"), "decision")

    def test_un_code_inconnu_ne_rend_rien(self):
        """Une procédure accélérée n'est pas une étape du parcours : lui
        inventer une colonne serait pire que de l'ignorer."""
        self.assertIsNone(affichage.moment_au_senat("SN1-PROCACC"))
        self.assertIsNone(affichage.moment_au_senat(""))
        self.assertIsNone(affichage.moment_au_senat(None))

    def test_une_etape_de_l_assemblee_n_en_est_pas_une_du_senat(self):
        """Les codes de l'Assemblée ne doivent rien rendre : sans quoi un
        texte jamais allé au Sénat se retrouverait dans son fil."""
        for code in ("AN1-DEPOT", "AN1-COM-FOND-RAPPORT", "AN1-DEBATS-SEANCE"):
            self.assertIsNone(affichage.moment_au_senat(code))

    def test_une_lecture_du_senat_qu_on_n_a_pas_encore_vue(self):
        """Trois préfixes existent aujourd'hui ; une troisième lecture ou une
        lecture définitive au Sénat doit marcher sans qu'on y retouche."""
        self.assertEqual(affichage.moment_au_senat("SN3-DEBATS-DEC"), "decision")
        self.assertEqual(affichage.moment_au_senat("SNLECDEF-DEBATS-DEC"),
                         "decision")

    def test_chaque_moment_a_sa_colonne(self):
        """La table des codes et celle des colonnes doivent se répondre : un
        moment sans colonne rangerait des textes nulle part."""
        colonnes = {cle for cle, _, _ in affichage.ETAPES_SENAT}
        self.assertEqual(set(affichage.MOMENTS_SENAT.values()), colonnes)


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
