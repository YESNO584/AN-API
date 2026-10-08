"""Les députés et leurs groupes : l'ordre de l'hémicycle mesuré sur les sièges, les couleurs, les auteurs et leurs photos.

    ./test_extraction_acteurs.py
"""
from __future__ import annotations

import sys
import json
import pathlib
import tempfile
import unittest
import unittest.mock
import extraction


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


class AuteursEtPhotos(unittest.TestCase):
    def _archive(self, acteurs):
        """Une archive minuscule, au format que `lire_acteurs` attend."""
        chemin = pathlib.Path(self.repertoire.name) / "acteurs.zip"
        import zipfile
        with zipfile.ZipFile(chemin, "w") as z:
            for i, a in enumerate(acteurs):
                z.writestr(f"json/acteur/{i}.json", json.dumps({"acteur": a}))
        return chemin

    ACTEUR = {"uid": {"#text": "PA1234"},
              "etatCivil": {"ident": {"civ": "M.", "prenom": "Jean", "nom": "Dupont"}},
              "mandats": {"mandat": [{"typeOrgane": "GP", "dateFin": None,
                                      "organes": {"organeRef": "PO999"}}]}}

    def test_un_depute_en_exercice_a_son_groupe_et_sa_photo(self):
        a = extraction.lire_acteurs(self._archive([self.ACTEUR]))["PA1234"]
        self.assertEqual(a["nom"], "Dupont")
        self.assertEqual(a["groupeRef"], "PO999")
        self.assertIn("1234", a["photo"])

    def test_un_senateur_ou_un_ministre_n_a_ni_groupe_ni_photo(self):
        """L'archive large ne sert qu'à nommer.

        Sans elle, 716 textes de loi sur 2 151 avaient un auteur que personne
        ne savait nommer, et 3 109 cosignataires restaient anonymes (mesuré le
        2026-09-01). Mais un sénateur n'a pas de groupe à l'Assemblée, et
        l'adresse des photos ne vaut que pour les députés.
        """
        a = extraction.lire_acteurs(self._archive([self.ACTEUR]),
                                    groupe_et_photo=False)["PA1234"]
        self.assertEqual(a["nom"], "Dupont")
        self.assertIsNone(a["groupeRef"])
        self.assertIsNone(a["photo"])

    def setUp(self):
        self.repertoire = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.repertoire.cleanup()

    # La circonscription vit dans le mandat de député, pas dans l'état civil.
    ELU = {"uid": {"#text": "PA2000"},
           "etatCivil": {"ident": {"civ": "Mme", "prenom": "Marie", "nom": "Martin"}},
           "mandats": {"mandat": [
               {"typeOrgane": "GP", "dateFin": None,
                "organes": {"organeRef": "PO999"}},
               {"typeOrgane": "ASSEMBLEE", "dateFin": None,
                "mandature": {"placeHemicycle": "077"},
                "election": {"lieu": {"departement": "Pas-de-Calais",
                                      "numDepartement": "62", "numCirco": "5"}}}]}}

    def test_la_circonscription_se_lit_dans_le_mandat_de_depute(self):
        a = extraction.lire_acteurs(self._archive([self.ELU]))["PA2000"]
        self.assertEqual(a["departement"], "Pas-de-Calais")
        self.assertEqual(a["circo"], "5")

    def test_un_mandat_de_depute_fini_ne_nomme_plus_la_circonscription(self):
        """Un député battu puis revenu porte deux mandats de député.

        Le mandat fini nommerait l'ancienne circonscription. Seul celui qui est
        encore ouvert compte — la même règle que pour le groupe politique.
        """
        double = dict(self.ELU)
        double["mandats"] = {"mandat": [
            {"typeOrgane": "ASSEMBLEE", "dateFin": "2024-06-09",
             "election": {"lieu": {"departement": "Nord", "numCirco": "1"}}},
            {"typeOrgane": "ASSEMBLEE", "dateFin": None,
             "election": {"lieu": {"departement": "Pas-de-Calais", "numCirco": "5"}}}]}
        a = extraction.lire_acteurs(self._archive([double]))["PA2000"]
        self.assertEqual(a["departement"], "Pas-de-Calais")
        self.assertEqual(a["circo"], "5")

    def test_un_groupe_fini_ne_compte_pas_davantage(self):
        """Un député qui change de groupe garde son ancien mandat de groupe."""
        change = dict(self.ELU)
        change["mandats"] = {"mandat": [
            {"typeOrgane": "GP", "dateFin": "2025-01-10",
             "organes": {"organeRef": "PO111"}},
            {"typeOrgane": "GP", "dateFin": None,
             "organes": {"organeRef": "PO222"}}]}
        a = extraction.lire_acteurs(self._archive([change]))["PA2000"]
        self.assertEqual(a["groupeRef"], "PO222")

    def test_le_numero_de_siege_perd_son_zero_de_remplissage(self):
        """La source écrit « 077 » ; on affiche 77.

        Le zéro est un remplissage de la source, pas une donnée. Le garder
        ferait écrire « siège 077 » à l'écran.
        """
        a = extraction.lire_acteurs(self._archive([self.ELU]))["PA2000"]
        self.assertEqual(a["siege"], "77")

    def test_un_depute_sans_siege_n_en_recoit_pas_un_faux(self):
        """Mesuré le 2026-09-19 : 576 députés sur 577 ont un numéro de siège.

        Le 577e n'en a pas. Mettre 0, ou une chaîne vide, le ferait passer pour
        assis quelque part.
        """
        muet = dict(self.ELU)
        muet["mandats"] = {"mandat": [{"typeOrgane": "ASSEMBLEE", "dateFin": None,
                                       "mandature": {"placeHemicycle": None}}]}
        self.assertIsNone(
            extraction.lire_acteurs(self._archive([muet]))["PA2000"]["siege"])

    def test_une_place_qui_n_est_pas_un_nombre_est_ecartee(self):
        bizarre = dict(self.ELU)
        bizarre["mandats"] = {"mandat": [{"typeOrgane": "ASSEMBLEE", "dateFin": None,
                                          "mandature": {"placeHemicycle": "tribune"}}]}
        self.assertIsNone(
            extraction.lire_acteurs(self._archive([bizarre]))["PA2000"]["siege"])

    def test_un_senateur_n_a_pas_de_circonscription_a_l_assemblee(self):
        a = extraction.lire_acteurs(self._archive([self.ELU]),
                                    groupe_et_photo=False)["PA2000"]
        self.assertIsNone(a["departement"])
        self.assertIsNone(a["circo"])
        self.assertIsNone(a["siege"])

    def test_un_depute_sans_lieu_d_election_ne_fait_pas_tomber_la_lecture(self):
        """Mesuré : le champ existe pour les 577, mais rien ne le garantit."""
        muet = dict(self.ELU)
        muet["mandats"] = {"mandat": [{"typeOrgane": "ASSEMBLEE", "dateFin": None}]}
        a = extraction.lire_acteurs(self._archive([muet]))["PA2000"]
        self.assertIsNone(a["departement"])
        self.assertIsNone(a["circo"])

    def test_l_adresse_d_une_photo_se_deduit_de_l_identifiant(self):
        self.assertEqual(
            extraction.PHOTO_DEPUTE.format("794830"),
            "https://www2.assemblee-nationale.fr/static/tribun/17/photos/794830.jpg")


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
