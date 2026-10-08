"""Un dossier législatif tel que publié devient-il le dossier qu'on attend ? Ses actes, ses étapes, son statut, ce que le Sénat en dit.

    ./test_extraction_dossiers.py
"""
from __future__ import annotations

import sys
import unittest
import unittest.mock
import affichage
import extraction
from decor_extraction import AUJOURDHUI, acte, dossier


class SaisineDeCommission(unittest.TestCase):
    """Un renvoi en commission le jour du dépôt n'est pas un examen.

    C'est le piège qui, non traité, classait 1 815 textes sur 1 990 « en
    commission » alors que la commission ne s'était jamais réunie.
    """

    def test_depot_et_saisine_le_meme_jour_restent_au_depot(self):
        d = extraction.analyser(dossier(
            acte("AN1-DEPOT", "2026-08-25", xsi="DepotInitiative_Type"),
            acte("AN1-COM-FOND-SAISIE", "2026-08-25"),
        ), AUJOURDHUI)
        self.assertEqual(d["etape"], 1)

    def test_une_reunion_de_commission_fait_passer_a_l_etape_2(self):
        d = extraction.analyser(dossier(
            acte("AN1-DEPOT", "2026-01-10", xsi="DepotInitiative_Type"),
            acte("AN1-COM-FOND-SAISIE", "2026-01-10"),
            acte("AN1-COM-FOND-REUNION", "2026-03-04"),
        ), AUJOURDHUI)
        self.assertEqual(d["etape"], 2)

    def test_un_rapport_ou_un_rapporteur_suffisent_aussi(self):
        for code in ("AN1-COM-FOND-RAPPORT", "AN1-COM-FOND-NOMIN"):
            with self.subTest(code=code):
                d = extraction.analyser(dossier(
                    acte("AN1-DEPOT", "2026-01-10", xsi="DepotInitiative_Type"),
                    acte(code, "2026-03-04"),
                ), AUJOURDHUI)
                self.assertEqual(d["etape"], 2)


class DoublonsApparents(unittest.TestCase):
    """Deux actes du même jour ne sont pas forcément un doublon.

    Mesuré le 2026-08-31 sur les 385 groupes d'actes qui partagent un code et
    une date : 100 se distinguent par l'heure, 196 par la réunion, et 89 par
    rien du tout.
    """

    def test_l_heure_distingue_deux_reunions_de_commission(self):
        matin = acte("AN1-COM-FOND-REUNION", dateActe="2026-03-05T09:00:00.000+01:00")
        soir = acte("AN1-COM-FOND-REUNION", dateActe="2026-03-05T21:00:00.000+01:00")
        self.assertEqual(extraction.precision_acte(matin), "09 h 00")
        self.assertEqual(extraction.precision_acte(soir), "21 h 00")

    def test_la_seance_publique_est_nommee_par_l_agenda(self):
        """Elle est datée à minuit : seule la réunion la distingue."""
        reunions = {"R1": {"debut": "2026-03-17T15:00", "quantieme": "Première"},
                    "R2": {"debut": "2026-03-17T21:30", "quantieme": "Deuxième"}}
        a = acte("AN1-DEBATS-SEANCE", "2026-03-17", reunionRef="R1")
        b = acte("AN1-DEBATS-SEANCE", "2026-03-17", reunionRef="R2")
        self.assertEqual(extraction.precision_acte(a, reunions), "1re séance")
        self.assertEqual(extraction.precision_acte(b, reunions), "2e séance")

    def test_un_quantieme_inattendu_est_rendu_tel_quel(self):
        """Mieux vaut afficher un mot inconnu que perdre la distinction."""
        reunions = {"R1": {"debut": "2026-03-17T15:00", "quantieme": "Cinquième"}}
        self.assertEqual(
            extraction.precision_acte(acte("AN1-DEBATS-SEANCE", "2026-03-17",
                                           reunionRef="R1"), reunions),
            "Cinquième")

    def test_deux_points_d_une_meme_reunion_sont_fusionnes(self):
        """Même réunion, même heure : rien ne les distingue, une seule ligne."""
        d = extraction.analyser(dossier(
            acte("AN1-DEPOT", "2026-01-10", xsi="DepotInitiative_Type"),
            acte("AN1-COM-FOND-REUNION", dateActe="2026-06-08T21:00:00.000+02:00",
                 reunionRef="R1", odjRef="R1PT1"),
            acte("AN1-COM-FOND-REUNION", dateActe="2026-06-08T21:00:00.000+02:00",
                 reunionRef="R1", odjRef="R1PT2"),
        ), AUJOURDHUI)
        reunions = [e for e in d["etapes"] if e["code"] == "AN1-COM-FOND-REUNION"]
        self.assertEqual(len(reunions), 1)

    def test_deux_seances_distinctes_ne_sont_pas_fusionnees(self):
        reunions = {"R1": {"debut": "2026-03-17T15:00", "quantieme": "Première"},
                    "R2": {"debut": "2026-03-17T21:30", "quantieme": "Deuxième"}}
        d = extraction.analyser(dossier(
            acte("AN1-DEPOT", "2026-01-10", xsi="DepotInitiative_Type"),
            acte("AN1-DEBATS-SEANCE", "2026-03-17", reunionRef="R1"),
            acte("AN1-DEBATS-SEANCE", "2026-03-17", reunionRef="R2"),
        ), AUJOURDHUI, reunions=reunions)
        seances = [e for e in d["etapes"] if e["code"] == "AN1-DEBATS-SEANCE"]
        self.assertEqual([e["precision"] for e in seances], ["1re séance", "2e séance"])


class DetailsPrisDansLesDonnees(unittest.TestCase):
    """Ce qui décrit une étape est recopié de la source, jamais rédigé.

    Chaque valeur attendue ici existe telle quelle dans l'open data. Ce test
    est là pour que personne n'y glisse plus tard une phrase inventée.
    """

    ORGANES = {"PO59051": {"libelle": "Commission des lois", "abrege": "Lois",
                           "type": "COMPER"},
               "PO838901": {"libelle": "Assemblée nationale", "abrege": "AN",
                            "type": "ASSEMBLEE"}}
    DOCUMENTS = {"T1": {"type": "Texte de commission", "numero": "1640",
                        "description": "visant à faciliter le maintien en rétention"}}

    def test_la_commission_est_nommee_par_son_identifiant(self):
        d = extraction.details_acte(acte("AN1-COM-FOND-REUNION", organeRef="PO59051"),
                                    self.ORGANES)
        self.assertEqual(d["organe"], "Commission des lois")

    def test_la_chambre_elle_meme_n_est_pas_repetee(self):
        """Une pastille dit déjà « Assemblée nationale » : la répéter n'apprend rien."""
        d = extraction.details_acte(acte("AN1-DEBATS-SEANCE", organeRef="PO838901"),
                                    self.ORGANES)
        self.assertNotIn("organe", d)

    def test_le_texte_adopte_garde_son_numero(self):
        d = extraction.details_acte(acte("AN1-COM-FOND-RAPPORT", texteAdopte="T1"),
                                    documents=self.DOCUMENTS)
        self.assertEqual(d["texteAdopte"]["numero"], "1640")
        self.assertEqual(d["texteAdopte"]["type"], "Texte de commission")

    def test_une_decision_dit_quel_texte_le_vote_a_produit(self):
        """C'est le fait le plus concret d'une séance : ce qui en sort."""
        d = extraction.details_acte(acte("AN1-DEBATS-DEC", textesAssocies={
            "texteAssocie": [{"typeTexte": "BTA", "refTexteAssocie": "T1"},
                             {"typeTexte": "TAP", "refTexteAssocie": "T2"}]}),
            documents={"T1": {"type": "Texte adopté", "numero": "163"}})
        self.assertEqual(d["texteAdopte"]["numero"], "163")

    def test_une_saisine_du_conseil_constitutionnel_dit_qui_et_pourquoi(self):
        d = extraction.details_acte(acte(
            "CC-SAISIE-AN",
            motif="En application de l'article 61§2 de la Constitution",
            casSaisine={"fam_code": "TSCCONT05", "libelle": "Soixante députés au moins"}))
        self.assertEqual(d["saisine"], "Soixante députés au moins")
        self.assertEqual(d["motif"], "En application de l'article 61§2 de la Constitution")

    def test_un_acte_sans_rien_a_dire_ne_dit_rien(self):
        self.assertEqual(extraction.details_acte(acte("AN1-DEPOT")), {})


class ParcoursQuiRepartEnArriere(unittest.TestCase):
    """Le parcours n'est pas une ligne droite.

    Après une commission mixte paritaire qui échoue, le texte repart en
    nouvelle lecture. Le classer sur « l'étape la plus avancée jamais
    atteinte » l'afficherait en sortie de navette alors qu'il est reparti.
    """

    def test_apres_une_cmp_le_texte_reparti_en_nouvelle_lecture_est_en_navette(self):
        d = extraction.analyser(dossier(
            acte("AN1-DEPOT", "2025-01-06", xsi="DepotInitiative_Type"),
            acte("AN1-DEBATS-DEC", "2025-03-11", conclusion="adoptée"),
            acte("SN1-DEBATS-DEC", "2025-05-20", conclusion="modifiée"),
            acte("CMP-DEC", "2025-07-01", conclusion="Désaccord"),
            acte("SNNLEC-DEPOT", "2026-05-12"),
        ), AUJOURDHUI)
        self.assertEqual(d["etape"], 4, "le texte est reparti chez l'autre chambre")

    def test_un_texte_arrete_a_la_cmp_y_reste(self):
        d = extraction.analyser(dossier(
            acte("AN1-DEPOT", "2025-01-06", xsi="DepotInitiative_Type"),
            acte("CMP-DEC", "2025-07-01", conclusion="Accord"),
        ), AUJOURDHUI)
        self.assertEqual(d["etape"], 5)


class ActesDuMemeJour(unittest.TestCase):
    """Plusieurs actes portent la même date ; leur ordre dans le fichier n'a
    pas de sens. Entre eux, c'est le plus avancé qui compte."""

    def test_l_ordre_dans_le_fichier_ne_change_pas_le_resultat(self):
        a = acte("AN1-COM-FOND-SAISIE", "2026-06-10")
        b = acte("AN1-DEBATS-SEANCE", "2026-06-10")
        depot = acte("AN1-DEPOT", "2026-01-01", xsi="DepotInitiative_Type")
        self.assertEqual(extraction.analyser(dossier(depot, a, b), AUJOURDHUI)["etape"],
                         extraction.analyser(dossier(depot, b, a), AUJOURDHUI)["etape"])

    def test_le_plus_avance_du_jour_l_emporte(self):
        d = extraction.analyser(dossier(
            acte("AN1-DEPOT", "2026-01-01", xsi="DepotInitiative_Type"),
            acte("AN1-COM-FOND-SAISIE", "2026-06-10"),
            acte("AN1-DEBATS-SEANCE", "2026-06-10"),
        ), AUJOURDHUI)
        self.assertEqual(d["etape"], 3)


class OrdreDuFichierSource(unittest.TestCase):
    """L'Assemblée range les lectures dans l'ordre où elles ont eu lieu.

    Cas réel : le 11 juin 2026, un texte reçoit le même jour la décision de
    l'Assemblée en 1ère lecture **et** son dépôt au Sénat en 2ème lecture.
    Les deux sont à l'étape « navette » ; c'est la position dans le fichier
    qui dit lequel est le dernier.
    """

    def test_le_dernier_acte_publie_du_jour_l_emporte(self):
        d = extraction.analyser(dossier(
            acte("SN1-DEPOT", "2025-12-03", xsi="DepotInitiative_Type"),
            acte("SN1-DEBATS-DEC", "2026-01-29", conclusion="adoptée"),
            acte("AN1-DEBATS-DEC", "2026-06-11", conclusion="rejetée"),
            acte("AN1-DEBATS-SEANCE", "2026-06-11"),
            acte("SN2-COM-FOND-SAISIE", "2026-06-11", libelle_court="2ème lecture"),
            acte("SN2-DEPOT", "2026-06-11", libelle_court="2ème lecture"),
        ), AUJOURDHUI)
        self.assertEqual(d["etape"], 4)
        self.assertEqual(d["etapeCourante"]["code"], "SN2-DEPOT",
                         "le texte est reparti au Sénat, pas resté à l'Assemblée")
        self.assertEqual(d["etapeCourante"]["chambre"], "senat")


class DatesFutures(unittest.TestCase):
    """La source contient des séances déjà programmées. Elles ne doivent
    jamais servir à classer un texte."""

    def test_une_seance_a_venir_ne_fait_pas_avancer_le_texte(self):
        d = extraction.analyser(dossier(
            acte("AN1-DEPOT", "2026-07-01", xsi="DepotInitiative_Type"),
            acte("AN1-DEBATS-SEANCE", "2026-12-15"),      # après AUJOURDHUI
        ), AUJOURDHUI)
        self.assertEqual(d["etape"], 1)
        self.assertEqual(d["dateDernierMouvement"], "2026-07-01")

    def test_mais_elle_est_conservee_et_marquee(self):
        d = extraction.analyser(dossier(
            acte("AN1-DEPOT", "2026-07-01", xsi="DepotInitiative_Type"),
            acte("AN1-DEBATS-SEANCE", "2026-12-15"),
        ), AUJOURDHUI)
        futures = [e for e in d["etapes"] if e["future"]]
        self.assertEqual([e["date"] for e in futures], ["2026-12-15"])


class Navette(unittest.TestCase):
    """Une première lecture chez la seconde chambre, c'est la navette."""

    def test_texte_parti_de_l_assemblee_et_arrive_au_senat(self):
        d = extraction.analyser(dossier(
            acte("AN1-DEPOT", "2026-01-06", xsi="DepotInitiative_Type"),
            acte("AN1-DEBATS-DEC", "2026-03-11", conclusion="adoptée"),
            acte("SN1-DEPOT", "2026-03-12"),
        ), AUJOURDHUI)
        self.assertEqual(d["etape"], 4)
        self.assertEqual(d["chambreInitiale"], "assemblee")

    def test_texte_parti_du_senat_et_arrive_a_l_assemblee(self):
        d = extraction.analyser(dossier(
            acte("SN1-DEPOT", "2026-01-06", xsi="DepotInitiative_Type"),
            acte("SN1-DEBATS-DEC", "2026-03-11", conclusion="adoptée"),
            acte("AN1-DEPOT", "2026-03-12"),
        ), AUJOURDHUI)
        self.assertEqual(d["etape"], 4)
        self.assertEqual(d["chambreInitiale"], "senat")

    def test_la_premiere_lecture_chez_soi_n_est_pas_la_navette(self):
        d = extraction.analyser(dossier(
            acte("SN1-DEPOT", "2026-01-06", xsi="DepotInitiative_Type"),
            acte("SN1-DEBATS-SEANCE", "2026-03-11"),
        ), AUJOURDHUI)
        self.assertEqual(d["etape"], 3)


class Statuts(unittest.TestCase):
    def test_un_texte_promulgue_est_marque_comme_tel(self):
        d = extraction.analyser(dossier(
            acte("AN1-DEPOT", "2025-01-06", xsi="DepotInitiative_Type"),
            acte("PROM-PUB", "2026-04-21", xsi="Promulgation_Type",
                 codeLoi="2026-667", infoJO={"urlLegifrance": "https://exemple.test/loi"}),
        ), AUJOURDHUI)
        self.assertEqual(d["statut"], extraction.PROMULGUE)
        self.assertEqual(d["loiNumero"], "2026-667")
        self.assertEqual(d["loiDate"], "2026-04-21")

    def test_un_texte_retire_est_marque_comme_tel(self):
        d = extraction.analyser(dossier(
            acte("AN1-DEPOT", "2025-01-06", xsi="DepotInitiative_Type"),
            acte("ANLUNI-RTRINI", "2025-12-18", xsi="RetraitInitiative_Type"),
        ), AUJOURDHUI)
        self.assertEqual(d["statut"], extraction.RETIRE)

    def test_un_dossier_sans_acte_date_n_a_pas_d_etape(self):
        d = extraction.analyser(dossier(acte("AN1")), AUJOURDHUI)
        self.assertEqual(d["statut"], extraction.SANS_ACTE)
        self.assertIsNone(d["etape"])

    def test_les_dossiers_qui_ne_font_pas_de_loi_sont_marques_mais_gardes(self):
        for procedure, attendu in (("Résolution", False),
                                   ("Commission d'enquête", False),
                                   ("Rapport d'information sans mission", False),
                                   ("Projet de loi ordinaire", True),
                                   ("Proposition de loi ordinaire", True)):
            with self.subTest(procedure=procedure):
                d = extraction.analyser(dossier(
                    acte("AN1-DEPOT", "2026-01-06", xsi="DepotInitiative_Type"),
                    procedure=procedure), AUJOURDHUI)
                self.assertEqual(d["estLoi"], attendu)
                self.assertEqual(d["uid"], "D1", "le dossier est gardé dans tous les cas")


class LienVersLeSenat(unittest.TestCase):
    """L'Assemblée publie l'adresse du dossier Sénat : aucun rapprochement à
    faire entre les deux chambres."""

    def test_l_adresse_du_senat_est_reprise(self):
        d = extraction.analyser(dossier(
            acte("AN1-DEPOT", "2026-01-06", xsi="DepotInitiative_Type"),
            senat="http://www.senat.fr/dossier-legislatif/pjl25-285.html"), AUJOURDHUI)
        self.assertEqual(d["urlSenat"], "http://www.senat.fr/dossier-legislatif/pjl25-285.html")

    def test_la_chaine_None_du_fichier_source_ne_devient_pas_un_lien(self):
        d = extraction.analyser(dossier(
            acte("AN1-DEPOT", "2026-01-06", xsi="DepotInitiative_Type"),
            senat="None"), AUJOURDHUI)
        self.assertIsNone(d["urlSenat"])


class Libelles(unittest.TestCase):
    def test_le_libelle_court_evite_une_parenthese_fausse(self):
        # « 1ère lecture (1ère assemblée saisie) » devient faux quand le texte
        # a commencé au Sénat : on garde « 1ère lecture ».
        a = acte("AN1", libelle_court="1ère lecture")
        a["libelleActe"]["nomCanonique"] = "1ère lecture (1ère assemblée saisie)"
        self.assertEqual(extraction.libelle(a, court=True), "1ère lecture")
        self.assertEqual(extraction.libelle(a), "1ère lecture (1ère assemblée saisie)")

    def test_l_arbre_des_actes_est_bien_aplati(self):
        arbre = {"acteLegislatif": [{
            "codeActe": "AN1",
            "actesLegislatifs": {"acteLegislatif": {
                "codeActe": "AN1-COM",
                "actesLegislatifs": {"acteLegislatif": [{"codeActe": "AN1-COM-FOND"}]},
            }},
        }]}
        self.assertEqual([a["codeActe"] for a in extraction.aplatir(arbre)],
                         ["AN1", "AN1-COM", "AN1-COM-FOND"])


class TextesArretes(unittest.TestCase):
    """Un texte peut s'arrêter sans être promulgué. Aucun de ces états ne
    prétend que c'est fini pour de bon : les sources ne le disent pas."""

    def test_un_rejet_le_dernier_jour_connu_marque_le_texte(self):
        d = extraction.analyser(dossier(
            acte("AN1-DEPOT", "2025-01-06", xsi="DepotInitiative_Type"),
            acte("AN1-DEBATS-DEC", "2026-06-11", conclusion="rejetée"),
        ), AUJOURDHUI)
        self.assertEqual(d["statut"], extraction.REJETE)

    def test_un_rejet_suivi_d_autre_chose_ne_marque_rien(self):
        """19 des 27 textes rejetés de la législature ont continué leur route."""
        d = extraction.analyser(dossier(
            acte("AN1-DEBATS-DEC", "2025-03-11", conclusion="rejetée"),
            acte("SN1-DEPOT", "2026-05-12", xsi="DepotInitiativeNavette_Type"),
            acte("AN1-DEPOT", "2025-01-06", xsi="DepotInitiative_Type"),
        ), AUJOURDHUI)
        self.assertEqual(d["statut"], extraction.EN_COURS)

    def test_le_rejet_par_une_commission_compte_aussi(self):
        d = extraction.analyser(dossier(
            acte("ANLUNI-DEPOT", "2025-01-06", xsi="DepotInitiative_Type"),
            acte("ANLUNI-COM-CAE-DEC", "2026-06-24",
                 conclusion="rejet du texte par la commission préalable"),
        ), AUJOURDHUI)
        self.assertEqual(d["statut"], extraction.REJETE)


class EtatVenuDuSenat(unittest.TestCase):
    """Le Sénat sait des fins que l'Assemblée n'enregistre pas : 29 textes que
    l'Assemblée laisse en cours sont dits « non adopté », « retiré » ou
    « caduc » par le Sénat (mesuré le 2026-08-31)."""

    def test_le_senat_peut_declarer_un_texte_non_adopte(self):
        d = extraction.analyser(
            dossier(acte("SN1-DEPOT", "2026-01-06", xsi="DepotInitiative_Type"),
                    senat="http://www.senat.fr/dossier-legislatif/ppl25-1.html"),
            AUJOURDHUI, {"ppl25-1.html": "non adopté"})
        self.assertEqual(d["statut"], extraction.NON_ADOPTE)
        self.assertEqual(d["etatSenat"], "non adopté")

    def test_caduc_et_retire_sont_repris_tels_quels(self):
        for etat, attendu in (("caduc", extraction.CADUC),
                              ("retiré", extraction.RETIRE),
                              ("Non conforme à la constitution", extraction.NON_ADOPTE)):
            with self.subTest(etat=etat):
                d = extraction.analyser(
                    dossier(acte("SN1-DEPOT", "2026-01-06", xsi="DepotInitiative_Type"),
                            senat="http://www.senat.fr/dossier-legislatif/x.html"),
                    AUJOURDHUI, {"x.html": etat})
                self.assertEqual(d["statut"], attendu)

    def test_un_etat_du_senat_qui_ne_dit_pas_une_fin_ne_change_rien(self):
        d = extraction.analyser(
            dossier(acte("SN1-DEPOT", "2026-01-06", xsi="DepotInitiative_Type"),
                    senat="http://www.senat.fr/dossier-legislatif/x.html"),
            AUJOURDHUI, {"x.html": "Première lecture (Sénat)"})
        self.assertEqual(d["statut"], extraction.EN_COURS)

    def test_une_promulgation_constatee_ne_se_discute_pas(self):
        d = extraction.analyser(dossier(
            acte("AN1-DEPOT", "2025-01-06", xsi="DepotInitiative_Type"),
            acte("PROM-PUB", "2026-04-21", xsi="Promulgation_Type", codeLoi="2026-1"),
            senat="http://www.senat.fr/dossier-legislatif/x.html"),
            AUJOURDHUI, {"x.html": "non adopté"})
        self.assertEqual(d["statut"], extraction.PROMULGUE)

    def test_les_deux_formes_d_adresse_du_senat_donnent_la_meme_cle(self):
        self.assertEqual(
            extraction.cle_senat("http://www.senat.fr/dossierleg/ppl00-074.html"),
            extraction.cle_senat("https://www.senat.fr/dossier-legislatif/ppl00-074.html"))

    def test_une_adresse_absente_ne_donne_pas_de_cle(self):
        self.assertIsNone(extraction.cle_senat(None))
        self.assertIsNone(extraction.cle_senat(""))

    def test_aucune_formulation_ne_pretend_qu_un_texte_est_fini_pour_de_bon(self):
        interdits = ("définitif", "definitif", "définitive", "jamais adopté",
                     "ne reviendra", "abandonné")
        for cle, (nom, quoi) in affichage.FINS.items():
            for mot in interdits:
                with self.subTest(issue=cle, mot=mot):
                    self.assertNotIn(mot, (nom + " " + quoi).lower().replace(
                        "il ne reviendra jamais", ""),
                        "les sources ne se prononcent pas sur le caractère définitif")


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
