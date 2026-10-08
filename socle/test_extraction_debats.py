"""Les comptes rendus de séance : qui parle, de quel texte, dans quel groupe — et le débat de chaque amendement, compté.

    ./test_extraction_debats.py
"""
from __future__ import annotations

import sys
import unittest
import unittest.mock
import extraction
from decor_extraction import SIGLES, donne_la_parole, parole, seance, section, sort_annonce, titre_de_texte


class LeGroupeDeLOrateur(unittest.TestCase):
    def test_le_sigle_est_imprime_apres_le_nom(self):
        self.assertEqual(
            extraction.sigle_d_orateur("M. Éric Martineau (Dem)", SIGLES), "Dem")

    def test_un_departement_n_est_pas_un_groupe(self):
        """La même parenthèse départage deux homonymes par leur département.
        Sans la liste des groupes, trois orateurs de la législature se
        retrouvaient dans un groupe « Alpes-Maritimes »."""
        self.assertIsNone(
            extraction.sigle_d_orateur("M. Untel (Alpes-Maritimes)", SIGLES))

    def test_sans_parenthese_on_ne_sait_pas(self):
        self.assertIsNone(extraction.sigle_d_orateur("Mme Océane Godard", SIGLES))
        self.assertIsNone(extraction.sigle_d_orateur(None, SIGLES))

    def test_la_presidence_se_reconnait_a_son_titre(self):
        for nom in ("M. le président", "Mme la présidente"):
            self.assertTrue(extraction.est_la_presidence(nom), nom)
        for nom in ("M. Éric Martineau", "M. le président de la commission", ""):
            self.assertFalse(extraction.est_la_presidence(nom), nom)

    def test_le_sigle_vu_ailleurs_sert_partout(self):
        """Le sigle n'est imprimé qu'au premier paragraphe d'une prise de
        parole : sans ce rattrapage, 8,7 % des paroles seulement ont un
        groupe, contre 94,6 % avec."""
        paroles = [{"acteur_ref": "PA1", "sigle": "SOC"},
                   {"acteur_ref": "PA1", "sigle": None},
                   {"acteur_ref": "PA2", "sigle": None}]
        extraction.completer_les_sigles(paroles)
        self.assertEqual([p["sigle"] for p in paroles], ["SOC", "SOC", None])

    def test_le_sigle_se_cherche_dans_toute_la_seance(self):
        """M. Stéphane Lenormand prend la parole 49 fois sans sigle, et les 8
        fois où le compte rendu l'imprime « (LIOT) » sont toutes dans la
        discussion des articles — une section qu'on ne publie pas. Chercher le
        sigle dans les seules sections retenues laissait 582 paroles sans
        groupe au lieu de 189."""
        corps = (titre_de_texte()
                 + section("Discussion des articles",
                           parole("M. Stéphane Lenormand (LIOT)", "Sur l’alinéa 7…",
                                  acteur="PA795902"))
                 + section("Explications de vote",
                           parole("M. Stéphane Lenormand", "Nous voterons…",
                                  acteur="PA795902")))
        racine = seance(corps)
        paroles = list(extraction.prises_de_parole(racine, SIGLES | {"LIOT"}))
        self.assertEqual([p["sigle"] for p in paroles], [None])
        extraction.completer_les_sigles(
            paroles, extraction.sigles_nommes(racine, SIGLES | {"LIOT"}))
        self.assertEqual([p["sigle"] for p in paroles], ["LIOT"])

    def test_un_orateur_qui_change_de_groupe_garde_le_plus_frequent(self):
        paroles = [{"acteur_ref": "PA1", "sigle": "RN"},
                   {"acteur_ref": "PA1", "sigle": "UDR"},
                   {"acteur_ref": "PA1", "sigle": "UDR"},
                   {"acteur_ref": "PA1", "sigle": None}]
        extraction.completer_les_sigles(paroles)
        self.assertEqual(paroles[3]["sigle"], "UDR")


class LeTexteDontOnParle(unittest.TestCase):
    def test_un_titre_cite_le_numero_de_depot(self):
        self.assertEqual(extraction.numeros_de_texte(" (n[[o]]\u00a02406)"), ["2406"])

    def test_deux_textes_discutes_ensemble(self):
        self.assertEqual(extraction.numeros_de_texte(" (n[[os]] 2406, 2401)"),
                         ["2406", "2401"])

    def test_un_debat_sans_texte_ne_cite_rien(self):
        """428 des 1 093 titres n'ont pas de numéro : questions au
        gouvernement, déclaration du gouvernement, motion de censure."""
        self.assertEqual(extraction.numeros_de_texte(""), [])
        self.assertEqual(extraction.numeros_de_texte(None), [])

    def test_le_senat_numerote_comme_nous(self):
        """« n° 698 » désigne quatre documents : une proposition de
        l'Assemblée, son rapport, et deux propositions du Sénat. Seuls les
        documents de l'Assemblée comptent."""
        docs = {
            "a": {"uid": "PIONANR5L17BTC0698", "numero": 698, "dossier": "D1"},
            "b": {"uid": "RAPPANR5L17B0698", "numero": 698, "dossier": "D1"},
            "c": {"uid": "PIONSNR5S459BTC0698", "numero": 698, "dossier": "D2"},
        }
        self.assertEqual(extraction.documents_par_numero(docs), {"698": {"D1"}})

    def test_la_date_departage_deux_dossiers(self):
        """Sans la date, 97 numéros cités désignent deux à quatre dossiers ;
        avec elle, aucun."""
        par_numero = {"698": {"D1", "D2"}}
        dates = {"D1": {"2026-02-25"}, "D2": {"2025-06-04"}}
        self.assertEqual(
            extraction.dossier_des_numeros(["698"], "2026-02-25", par_numero, dates),
            "D1")

    def test_un_dossier_indecidable_n_est_rattache_a_rien(self):
        """Mieux vaut ne rien montrer que d'attribuer un discours au mauvais
        texte."""
        par_numero = {"698": {"D1", "D2"}}
        dates = {"D1": {"2026-02-25"}, "D2": {"2026-02-25"}}
        self.assertIsNone(
            extraction.dossier_des_numeros(["698"], "2026-02-25", par_numero, dates))

    def test_un_dossier_inconnu_ne_rattache_rien(self):
        self.assertIsNone(extraction.dossier_des_numeros(["1191"], "2026-02-25", {}, {}))


class LesPrisesDeParole(unittest.TestCase):
    def paroles(self, corps, **kw):
        return list(extraction.prises_de_parole(seance(corps, **kw), SIGLES))

    def test_une_parole_porte_son_orateur_son_groupe_et_son_texte(self):
        p = self.paroles(titre_de_texte() + section(
            "Explications de vote",
            parole("M. Éric Martineau (Dem)", "La mort appartient à la vie.")))
        self.assertEqual(len(p), 1)
        self.assertEqual(p[0]["nom"], "M. Éric Martineau")
        self.assertEqual(p[0]["sigle"], "Dem")
        self.assertEqual(p[0]["texte"], "La mort appartient à la vie.")
        self.assertEqual(p[0]["numeros"], ["2406"])
        self.assertEqual(p[0]["date"], "2026-02-25")
        self.assertEqual(p[0]["section"], "Explications de vote")

    def test_seules_les_sections_d_argumentaire_comptent(self):
        """La discussion des articles parle d'un alinéa, pas du texte."""
        corps = titre_de_texte() + section(
            "Discussion des articles",
            parole("M. Éric Martineau (Dem)", "Sur l’alinéa 7…"))
        self.assertEqual(self.paroles(corps), [])

    def test_un_debat_sans_texte_ne_donne_rien(self):
        corps = ('<point nivpoint="1" code_grammaire="TITRE_TEXTE_DISCUSSION">'
                 "<orateurs/><texte>Questions au gouvernement</texte></point>"
                 + section("Discussion générale",
                           parole("M. Éric Martineau (Dem)", "Ma question…")))
        self.assertEqual(self.paroles(corps), [])

    def test_la_presidence_ne_defend_pas_un_texte(self):
        """« La parole est à M. Untel » n'est pas un argumentaire."""
        corps = titre_de_texte() + section(
            "Discussion générale",
            parole("Mme la présidente", "La parole est à M. Éric Martineau.",
                   acteur="PA721908")
            + parole("M. Éric Martineau (Dem)", "La mort appartient à la vie."))
        p = self.paroles(corps)
        self.assertEqual([x["nom"] for x in p], ["M. Éric Martineau"])

    def test_une_interruption_ne_coupe_pas_la_parole(self):
        """Le compte rendu insère « Mais non ! » au milieu d'un discours. Sans
        recollage, un même orateur apparaît deux fois de suite."""
        corps = titre_de_texte() + section(
            "Explications de vote",
            parole("M. Éric Martineau (Dem)", "Première partie.")
            + parole("M. Frédéric Valletoux", "Mais non !", acteur="PA795350",
                     code="INTERRUPTION_1_10")
            + parole("M. Éric Martineau", "Seconde partie."))
        p = self.paroles(corps)
        self.assertEqual(len(p), 1)
        self.assertEqual(p[0]["texte"], "Première partie.\n\nSeconde partie.")

    def test_deux_orateurs_font_deux_paroles(self):
        corps = titre_de_texte() + section(
            "Explications de vote",
            parole("M. Éric Martineau (Dem)", "Pour nous…")
            + parole("Mme Océane Godard (SOC)", "Deux cents heures.",
                     acteur="PA840939"))
        p = self.paroles(corps)
        self.assertEqual([(x["nom"], x["sigle"], x["ordre"]) for x in p],
                         [("M. Éric Martineau", "Dem", 1),
                          ("Mme Océane Godard", "SOC", 2)])

    def test_la_qualite_de_l_orateur_est_recopiee(self):
        corps = titre_de_texte() + section(
            "Discussion générale",
            parole("M. Frédéric Valletoux", "Mon rapport…", acteur="PA795350",
                   qualite="rapporteur"))
        self.assertEqual(self.paroles(corps)[0]["qualite"], "rapporteur")

    def test_un_nouveau_texte_ferme_la_section_precedente(self):
        """Deux textes se suivent dans la même séance : la parole du second ne
        doit pas se rattacher au premier."""
        corps = (titre_de_texte(" (n[[o]] 2406)")
                 + section("Explications de vote",
                           parole("M. Éric Martineau (Dem)", "Sur le premier."))
                 + titre_de_texte(" (n[[o]] 2401)")
                 + section("Explications de vote",
                           parole("Mme Océane Godard (SOC)", "Sur le second.",
                                  acteur="PA840939")))
        p = self.paroles(corps)
        self.assertEqual([x["numeros"] for x in p], [["2406"], ["2401"]])

    def test_le_texte_des_italiques_est_garde(self):
        """« (Applaudissements sur les bancs du groupe SOC.) » fait partie du
        compte rendu : le retirer serait choisir ce qui compte."""
        corps = titre_de_texte() + section(
            "Explications de vote",
            parole("Mme Océane Godard (SOC)",
                   "Deux cents heures.<italique> (Applaudissements.)</italique>",
                   acteur="PA840939"))
        self.assertIn("(Applaudissements.)", self.paroles(corps)[0]["texte"])

    def test_une_parole_vide_n_est_pas_publiee(self):
        corps = titre_de_texte() + section(
            "Explications de vote", parole("M. Éric Martineau (Dem)", ""))
        self.assertEqual(self.paroles(corps), [])


class LAmpleurDuDebatDUnAmendement(unittest.TestCase):
    """Combien de personnes ont parlé d'un amendement — un compte, pas un texte."""

    def blocs(self, corps, **kw):
        return list(extraction.debats_par_amendement(seance(corps, **kw)))

    def test_un_amendement_discute_seul_porte_ses_orateurs(self):
        corps = titre_de_texte() + section(
            "Discussion des articles",
            donne_la_parole("885 rectifié")
            + parole("M. Laurent Nuñez", "Il vise à suspendre le permis.",
                     acteur="PA759834")
            + parole("Mme Elsa Faucillon", "Et l’alcool ?", acteur="PA721896")
            + sort_annonce("885 rectifié"))
        self.assertEqual(self.blocs(corps), [{
            "seance": "CRSANR5L17S2026O1N168", "date": "2026-02-25",
            "numeros": ["2406"], "amendement": "885",
            "orateurs": 2, "paragraphes": 3}])

    def test_l_attribut_adt_de_la_source_n_est_pas_cru(self):
        """Il traîne d'un amendement au suivant : sur 13 665 annonces
        vérifiables il en contredit 837, et sur l'amendement 885 de la loi
        Ripost il annonce 605. Le numéro vient de la phrase du président."""
        corps = titre_de_texte() + section(
            "Discussion des articles",
            donne_la_parole("885 rectifié", adt=" 605")
            + parole("M. Laurent Nuñez", "Il vise à…", acteur="PA759834")
            + sort_annonce("885 rectifié"))
        self.assertEqual(self.blocs(corps)[0]["amendement"], "885")

    def test_une_discussion_commune_n_est_pas_decoupee(self):
        """27 % des blocs portent plusieurs amendements défendus à la suite :
        ce qui s'y dit vaut pour l'ensemble, pas pour l'un d'eux."""
        corps = titre_de_texte() + section(
            "Discussion des articles",
            donne_la_parole("366")
            + parole("Mme Danielle Brulebois", "Il rétablit l’article.",
                     acteur="PA719890")
            + donne_la_parole("236")
            + parole("M. Ugo Bernalicis", "Le nôtre le supprime.", acteur="PA720430")
            + sort_annonce("366", adopte=False))
        self.assertEqual(self.blocs(corps), [])

    def test_un_bloc_sans_sort_annonce_n_est_pas_garde(self):
        """Sans clôture, un bloc court jusqu'à l'annonce suivante et avale ce
        qui ne le concerne pas."""
        corps = titre_de_texte() + section(
            "Discussion des articles",
            donne_la_parole("885")
            + parole("M. Laurent Nuñez", "Il vise à…", acteur="PA759834"))
        self.assertEqual(self.blocs(corps), [])

    def test_deux_amendements_a_la_suite_font_deux_blocs(self):
        corps = titre_de_texte() + section(
            "Discussion des articles",
            donne_la_parole("597")
            + parole("Mme Andrée Taurinya", "Nous le supprimons.", acteur="PA794106")
            + sort_annonce("597", adopte=False)
            + donne_la_parole("598")
            + parole("M. Jean-François Coulomme", "Il vise l’alinéa 2.",
                     acteur="PA795136")
            + parole("M. Vincent Caure", "Avis défavorable.", acteur="PA842311")
            + sort_annonce("598", adopte=False))
        self.assertEqual([(b["amendement"], b["orateurs"]) for b in self.blocs(corps)],
                         [("597", 1), ("598", 2)])

    def test_la_presidence_n_est_pas_un_orateur(self):
        """Elle donne la parole, elle ne débat pas."""
        corps = titre_de_texte() + section(
            "Discussion des articles",
            donne_la_parole("885")
            + parole("M. Laurent Nuñez", "Il vise à…", acteur="PA759834")
            + parole("M. le président", "Quel est l’avis de la commission ?",
                     acteur="PA719024")
            + sort_annonce("885"))
        self.assertEqual(self.blocs(corps)[0]["orateurs"], 1)

    def test_une_interruption_est_quelqu_un_qui_prend_part_au_debat(self):
        """« Et l'alcool ? » lancé des bancs compte : c'est ce qui distingue un
        échange d'un long monologue."""
        corps = titre_de_texte() + section(
            "Discussion des articles",
            donne_la_parole("885")
            + parole("M. Laurent Nuñez", "Il vise à…", acteur="PA759834")
            + parole("M. Emeric Salmon", "C’est illégal !", acteur="PA794954",
                     code="INTERRUPTION_1_10")
            + sort_annonce("885"))
        self.assertEqual(self.blocs(corps)[0]["orateurs"], 2)

    def test_un_orateur_qui_reprend_la_parole_ne_compte_qu_une_fois(self):
        corps = titre_de_texte() + section(
            "Discussion des articles",
            donne_la_parole("885")
            + parole("M. Ugo Bernalicis", "D’abord ceci.", acteur="PA720430")
            + parole("M. Ugo Bernalicis", "Ensuite cela.", acteur="PA720430")
            + sort_annonce("885"))
        self.assertEqual(self.blocs(corps)[0]["orateurs"], 1)

    def test_un_debat_sans_texte_identifie_ne_donne_rien(self):
        corps = ('<point nivpoint="1" code_grammaire="TITRE_TEXTE_DISCUSSION">'
                 "<orateurs/><texte>Questions au gouvernement</texte></point>"
                 + section("Discussion des articles",
                           donne_la_parole("885")
                           + parole("M. Untel", "Il vise à…")
                           + sort_annonce("885")))
        self.assertEqual(self.blocs(corps), [])

    def test_le_texte_change_avec_le_point_de_niveau_1(self):
        """Deux textes se discutent dans la même séance : chaque bloc part avec
        le numéro de dépôt annoncé au-dessus de lui."""
        corps = (titre_de_texte()
                 + section("Discussion des articles",
                           donne_la_parole("12")
                           + parole("M. Untel", "Le premier texte.")
                           + sort_annonce("12"))
                 + titre_de_texte(" (n[[o]] 2984)")
                 + section("Discussion des articles",
                           donne_la_parole("885")
                           + parole("M. Untel", "Le second texte.")
                           + sort_annonce("885")))
        self.assertEqual([(b["numeros"], b["amendement"]) for b in self.blocs(corps)],
                         [(["2406"], "12"), (["2984"], "885")])


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
