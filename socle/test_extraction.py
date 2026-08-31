#!/usr/bin/env python3
"""Vérifie le classement des étapes — la partie du socle qui peut se tromper.

Ces tests ne touchent ni au réseau ni à la base : ils portent sur les règles de
lecture, c'est-à-dire sur les trois pièges relevés à l'étape 0. Chacun a été
constaté sur les vraies données ; les cas ci-dessous les reproduisent en petit.

    ./test_extraction.py
"""

import sys
import unittest

import extraction

AUJOURDHUI = "2026-08-31"


def acte(code, date=None, xsi=None, libelle_court=None, conclusion=None, **extra):
    a = {"codeActe": code, "uid": "u-" + code}
    if date:
        a["dateActe"] = date + "T00:00:00.000+02:00"
    if xsi:
        a["@xsi:type"] = xsi
    a["libelleActe"] = {"nomCanonique": libelle_court or code, "libelleCourt": libelle_court}
    if conclusion:
        a["statutConclusion"] = {"libelle": conclusion}
    a.update(extra)
    return a


def dossier(*actes, procedure="Proposition de loi ordinaire", senat=None, uid="D1"):
    return {"dossierParlementaire": {
        "uid": uid, "legislature": "17",
        "titreDossier": {"titre": "Un texte", "titreChemin": "un_texte", "senatChemin": senat},
        "procedureParlementaire": {"libelle": procedure},
        "actesLegislatifs": {"acteLegislatif": list(actes)},
    }}


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


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
