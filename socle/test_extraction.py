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


# ---------------------------------------------------------------------------
# Les scrutins publics
# ---------------------------------------------------------------------------

def scrutin(objet, *, uid="V1", dossier=None, sort="adopté", date="2026-06-11",
            groupes=(), type_vote="scrutin public ordinaire",
            pour=0, contre=0, abstentions=0):
    ventilation = {"organe": {"organeRef": "PO838901", "groupes": {"groupe": [
        {"organeRef": ref, "nombreMembresGroupe": str(m),
         "vote": {"positionMajoritaire": annoncee,
                  "decompteVoix": {"pour": str(p), "contre": str(c),
                                   "abstentions": str(a), "nonVotants": "0"}}}
        for ref, m, annoncee, p, c, a in groupes]}}} if groupes else None
    return {"scrutin": {
        "uid": uid, "numero": "1", "dateScrutin": date + "T00:00:00.000+02:00",
        "typeVote": {"libelleTypeVote": type_vote},
        "sort": {"code": sort, "libelle": "l'Assemblée nationale a " + sort},
        "titre": objet,
        "objet": {"libelle": objet,
                  "dossierLegislatif": {"dossierRef": dossier} if dossier else None},
        "demandeur": {"texte": "Président du groupe X"},
        "syntheseVote": {"nombreVotants": "100", "nbrSuffragesRequis": "50",
                         "decompte": {"pour": str(pour), "contre": str(contre),
                                      "abstentions": str(abstentions), "nonVotants": "0"}},
        "ventilationVotes": ventilation,
    }}


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


class OrdreDeLHemicycle(unittest.TestCase):
    """L'ordre des groupes est mesuré sur les numéros de siège publiés.

    L'hémicycle est numéroté de la droite vers la gauche : sur 61 152 numéros
    relevés le 2026-08-31, le RN se situe autour de la place 72 et LFI autour
    de la 603. Lu à l'envers, cela donne l'ordre politique habituel.
    """

    def test_le_plus_grand_numero_de_siege_est_le_plus_a_gauche(self):
        groupes = extraction.ordonner_groupes(
            {"A": {600: 50}, "B": {300: 50}, "C": {70: 50}},
            {"A": ("LFI-NFP", "La France insoumise"), "B": ("EPR", "Ensemble"),
             "C": ("RN", "Rassemblement National")})
        self.assertEqual([g["sigle"] for g in groupes], ["LFI-NFP", "EPR", "RN"])
        self.assertEqual([g["rang"] for g in groupes], [0, 1, 2])

    def test_un_groupe_sans_aucun_siege_connu_est_ecarte(self):
        groupes = extraction.ordonner_groupes(
            {"A": {600: 1}, "B": {}}, {"A": ("X", ""), "B": ("Y", "")})
        self.assertEqual([g["sigle"] for g in groupes], ["X"])

    def test_un_groupe_que_la_source_ne_nomme_plus_garde_son_identifiant(self):
        groupes = extraction.ordonner_groupes({"PO999": {400: 3}}, {})
        self.assertEqual(groupes[0]["sigle"], "PO999")
        self.assertEqual(groupes[0]["nom"], "")

    def test_la_mediane_se_calcule_sans_deplier_les_millions_de_places(self):
        self.assertEqual(extraction.mediane_depuis_histogramme({10: 1, 20: 1, 30: 1}), 20)
        self.assertEqual(extraction.mediane_depuis_histogramme({5: 100, 900: 1}), 5)
        self.assertIsNone(extraction.mediane_depuis_histogramme({}))

    def test_les_places_se_lisent_dans_les_quatre_colonnes_de_vote(self):
        brut = {"scrutin": {"ventilationVotes": {"organe": {"groupes": {"groupe": [
            {"organeRef": "A", "vote": {"decompteNominatif": {
                "pours": {"votant": [{"numPlace": "601"}, {"numPlace": "603"}]},
                "contres": {"votant": {"numPlace": "605"}},
                "abstentions": None,
                "nonVotants": {"votant": {"numPlace": "607"}},
            }}}]}}}}}
        self.assertEqual(sorted(extraction.places_du_scrutin(brut)),
                         [("A", 601), ("A", 603), ("A", 605), ("A", 607)])

    def test_une_place_absente_ou_illisible_est_ignoree(self):
        brut = {"scrutin": {"ventilationVotes": {"organe": {"groupes": {"groupe": {
            "organeRef": "A", "vote": {"decompteNominatif": {
                "pours": {"votant": [{"numPlace": None}, {"numPlace": "hors"},
                                     {"numPlace": "12"}]}}}}}}}}}
        self.assertEqual(list(extraction.places_du_scrutin(brut)), [("A", 12)])


class CouleursDesGroupes(unittest.TestCase):
    """Les couleurs sont une convention d'affichage : l'open data n'en publie
    aucune. Un groupe absent de la table reçoit une couleur calculée sur sa
    position, pour que rien ne casse quand un groupe naît ou disparaît."""

    def test_un_groupe_connu_garde_sa_couleur_conventionnelle(self):
        self.assertEqual(extraction.couleur_de_groupe("LFI-NFP", 0, 12),
                         extraction.COULEURS_GROUPES["LFI-NFP"])
        self.assertEqual(extraction.couleur_de_groupe("RN", 11, 12),
                         extraction.COULEURS_GROUPES["RN"])

    def test_un_groupe_inconnu_est_teinte_selon_sa_place(self):
        gauche = extraction.couleur_de_groupe("PO999", 0, 13)
        droite = extraction.couleur_de_groupe("PO888", 12, 13)
        self.assertEqual(gauche, extraction.DEGRADE[0])
        self.assertEqual(droite, extraction.DEGRADE[-1])
        self.assertNotEqual(gauche, droite)

    def test_un_groupe_seul_ne_fait_pas_diviser_par_zero(self):
        self.assertIn(extraction.couleur_de_groupe("PO999", 0, 1), extraction.DEGRADE)

    def test_chaque_groupe_actuel_a_une_couleur_distincte(self):
        couleurs = list(extraction.COULEURS_GROUPES.values())
        self.assertEqual(len(couleurs), len(set(couleurs)),
                         "deux groupes de la même couleur seraient indistinguables")


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
        for cle, (nom, quoi) in extraction.FINS.items():
            for mot in interdits:
                with self.subTest(issue=cle, mot=mot):
                    self.assertNotIn(mot, (nom + " " + quoi).lower().replace(
                        "il ne reviendra jamais", ""),
                        "les sources ne se prononcent pas sur le caractère définitif")


class LectureDesAmendements(unittest.TestCase):
    """Un amendement est une instruction en français, pas une différence entre
    deux textes. On l'affiche mot pour mot et on ne reconstitue rien."""

    def dispositif(self, texte):
        return {"amendement": {
            "uid": "A1", "identification": {"numeroLong": "AS20", "numeroOrdreDepot": "20"},
            "pointeurFragmentTexte": {"division": {"titre": "Article PREMIER"}},
            "signataires": {"auteur": {"typeAuteur": "Député", "acteurRef": "PA1",
                                       "groupePolitiqueRef": "PO1"}},
            "cycleDeVie": {"dateDepot": "2025-11-29",
                           "etatDesTraitements": {"etat": {"libelle": "Discuté"},
                                                  "sousEtat": {"libelle": "Adopté"}}},
            "corps": {"contenuAuteur": {"dispositif": texte, "exposeSommaire": "<p>Parce que.</p>"}},
        }}

    def test_un_champ_vide_du_xml_ne_devient_pas_un_dictionnaire(self):
        """Le format rend un champ absent par {'@xsi:nil': 'true'}. Sans filtre,
        ce dictionnaire finit dans une colonne de la base."""
        brut = self.dispositif("<p>Supprimer cet article.</p>")
        brut["amendement"]["signataires"]["auteur"]["acteurRef"] = {"@xsi:nil": "true"}
        a = extraction.analyser_amendement(brut)
        self.assertIsNone(a["auteurRef"])

    def test_le_dispositif_est_repris_mot_pour_mot_sans_balises(self):
        a = extraction.analyser_amendement(self.dispositif(
            "<p style='x'>Compl&#233;ter l&#8217;alin&#233;a 7.</p>"))
        self.assertEqual(a["dispositif"], "Compléter l’alinéa 7.")

    def test_ce_qui_est_ajoute_est_marque_vert(self):
        m = extraction.colorer_dispositif(
            "Compléter l’alinéa 7 par les mots : « , après avis simple ».")
        self.assertEqual([x["role"] for x in m], ["neutre", "ajout", "neutre"])
        self.assertEqual(m[1]["texte"], ", après avis simple")

    def test_une_suppression_marque_tout_en_rouge(self):
        m = extraction.colorer_dispositif("Supprimer les mots : « et les chiens ».")
        self.assertIn({"texte": "et les chiens", "role": extraction.RETRAIT}, m)

    def test_une_substitution_retire_le_premier_et_ajoute_le_second(self):
        m = extraction.colorer_dispositif(
            "À l’alinéa 2, substituer à la référence : « L. 1174‑3 »"
            " la référence : « L. 1174‑1 ».")
        cites = [x for x in m if x["role"] != extraction.NEUTRE]
        self.assertEqual([x["role"] for x in cites],
                         [extraction.RETRAIT, extraction.AJOUT])
        self.assertEqual(cites[0]["texte"], "L. 1174‑3")
        self.assertEqual(cites[1]["texte"], "L. 1174‑1")

    def test_une_instruction_sans_citation_reste_neutre(self):
        m = extraction.colorer_dispositif("Supprimer cet article.")
        self.assertEqual([x["role"] for x in m], [extraction.NEUTRE])

    def test_le_texte_complet_est_toujours_reconstituable_a_l_identique(self):
        """La coloration ne doit rien perdre ni rien ajouter : c'est la
        garantie qu'aucun mot de la source n'est déformé."""
        for phrase in ("Compléter l’alinéa 7 par les mots : « un chat ».",
                       "Supprimer cet article.",
                       "À l’alinéa 2, substituer aux mots : « a » les mots : « b »."):
            with self.subTest(phrase=phrase[:30]):
                m = extraction.colorer_dispositif(phrase)
                refait = "".join(x["texte"] if x["role"] == extraction.NEUTRE
                                 else "« " + x["texte"] + " »" for x in m)
                self.assertEqual(refait, phrase)

    def test_un_dispositif_absent_ne_produit_aucun_morceau(self):
        self.assertEqual(extraction.colorer_dispositif(""), [])
        self.assertEqual(extraction.colorer_dispositif(None), [])


class AuteursEtPhotos(unittest.TestCase):
    def test_l_adresse_d_une_photo_se_deduit_de_l_identifiant(self):
        self.assertEqual(
            extraction.PHOTO_DEPUTE.format("794830"),
            "https://www2.assemblee-nationale.fr/static/tribun/17/photos/794830.jpg")


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
