"""Un amendement tel que publié, et son dispositif découpé en retraits et ajouts.

    ./test_extraction_amendements.py
"""
from __future__ import annotations

import sys
import http.client
import json
import pathlib
import tempfile
import unittest
import unittest.mock
import urllib.error
import extraction


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

    def test_la_position_de_la_division_est_gardee(self):
        """« Après l'article 1er » ne modifie pas l'article 1er : il crée
        l'article 1er bis. Sans ce champ, un article apparu en commission
        n'aurait aucun amendement pour l'expliquer — 2 823 amendements adoptés
        de la législature sont dans ce cas (mesuré le 2026-09-18)."""
        brut = self.dispositif("<p>Après l’article 1er, insérer l’article suivant.</p>")
        brut["amendement"]["pointeurFragmentTexte"]["division"].update(
            {"avant_A_Apres": "Après", "type": "ARTICLE"})
        a = extraction.analyser_amendement(brut)
        self.assertEqual((a["ou"], a["divisionType"]), ("Après", "ARTICLE"))

    def test_sans_position_l_amendement_porte_sur_l_article_lui_meme(self):
        a = extraction.analyser_amendement(self.dispositif("<p>Supprimer cet article.</p>"))
        self.assertEqual(a["ou"], "A")

    def test_le_document_amende_vient_du_chemin(self):
        """`json/<dossier>/<texte>/<amendement>.json` : le fichier ne dit pas
        quelle version du texte il amende, le chemin si. C'est lui qui dit à
        quelle étape l'amendement s'applique."""
        archive = self.archive_d_amendements()
        lus = list(extraction.lire_amendements(archive))
        self.assertEqual([a["texte"] for a in lus], ["PIONANR5L17B1794"])
        self.assertEqual([a["dossier"] for a in lus], ["DLR5L17N52744"])

    def archive_d_amendements(self):
        import zipfile
        chemin = pathlib.Path(tempfile.mkdtemp()) / "amendements.zip"
        with zipfile.ZipFile(chemin, "w") as zf:
            zf.writestr("json/DLR5L17N52744/PIONANR5L17B1794/AMANR5L17.json",
                        json.dumps(self.dispositif("<p>Supprimer cet article.</p>")))
        return chemin

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


class TransfertCoupe(unittest.TestCase):
    """Une archive de 297 Mo ne traverse pas toujours le réseau d'un coup.

    Les deux publications du 2026-08-31 ont échoué ainsi : coupure après
    2,6 Mo, puis après 51,7 Mo sur 297. Recommencer depuis le début n'y
    suffisait pas — il faut reprendre où l'on s'est arrêté.
    """

    class Reponse:
        """Un serveur qui livre des morceaux, et coupe quand on le lui dit."""

        def __init__(self, morceaux, coupe=False, status=200, etag="e1",
                     total=None, annonce=True):
            self.morceaux, self.coupe, self.status = list(morceaux), coupe, status
            self.headers = {"ETag": etag, "Last-Modified": "hier"}
            if annonce:
                livre = sum(len(m) for m in morceaux)
                entier = total if total is not None else livre
                if status == 206:
                    # Ce qu'annonce un vrai serveur sur une reprise : la portée
                    # envoyée, et la taille de l'archive entière. La longueur,
                    # elle, ne couvre que le morceau.
                    debut = entier - livre
                    self.headers["Content-Range"] = f"bytes {debut}-{entier - 1}/{entier}"
                    self.headers["Content-Length"] = str(livre)
                else:
                    # Sur une réponse entière, la longueur annoncée est le tout,
                    # même si le serveur coupe avant de l'avoir envoyé.
                    self.headers["Content-Length"] = str(entier)

        def __enter__(self): return self
        def __exit__(self, *_): return False

        def read(self, _taille=None):
            if self.morceaux:
                return self.morceaux.pop(0)
            if self.coupe:
                self.coupe = False
                raise http.client.IncompleteRead(b"", 999)
            return b""

    def _serveur(self, *reponses):
        suite = list(reponses)
        vues = []

        def faux(requete, **_k):
            vues.append(dict(requete.headers))
            return suite.pop(0)
        return faux, vues, suite

    def test_le_transfert_reprend_ou_il_s_est_arrete(self):
        faux, vues, reste = self._serveur(
            self.Reponse([b"debut"], coupe=True),
            self.Reponse([b"-fin"], status=206))
        with unittest.mock.patch("urllib.request.urlopen", faux):
            r = extraction.telecharger(self.fichier, url="http://x",
                                       patienter=lambda _: None)
        self.assertEqual(self.fichier.read_bytes(), b"debut-fin")
        self.assertEqual(r["octets"], 9)
        self.assertEqual(reste, [])
        # Le second appel demande la suite, pas tout depuis le début.
        self.assertEqual(vues[1].get("Range"), "bytes=5-")

    def test_si_l_archive_a_change_on_repart_de_zero(self):
        """Le serveur refuse la reprise en répondant 200 : le début est périmé."""
        faux, _, _ = self._serveur(
            self.Reponse([b"ancienne"], coupe=True),
            self.Reponse([b"nouvelle archive"], status=200))
        with unittest.mock.patch("urllib.request.urlopen", faux):
            r = extraction.telecharger(self.fichier, url="http://x",
                                       patienter=lambda _: None)
        self.assertEqual(self.fichier.read_bytes(), b"nouvelle archive")
        self.assertEqual(r["octets"], 16)

    def test_un_transfert_coupe_en_silence_est_detecte(self):
        """Lu par morceaux, un transfert coupé ne lève rien : il rend b"".

        Sans la comparaison à la taille annoncée, l'archive des amendements est
        arrivée à 4,7 Mo au lieu de 297, et le programme a cru avoir réussi.
        """
        faux, vues, _ = self._serveur(
            self.Reponse([b"debut"], total=9),          # annonce 9, en livre 5
            self.Reponse([b"-fin"], status=206))
        with unittest.mock.patch("urllib.request.urlopen", faux):
            r = extraction.telecharger(self.fichier, url="http://x",
                                       patienter=lambda _: None)
        self.assertEqual(self.fichier.read_bytes(), b"debut-fin")
        self.assertEqual(r["octets"], 9)
        self.assertEqual(vues[1].get("Range"), "bytes=5-")

    def test_un_serveur_muet_sur_la_taille_est_cru_sur_parole(self):
        """Sans Content-Length, on ne peut rien vérifier — et on n'invente pas."""
        faux, _, _ = self._serveur(self.Reponse([b"tout"], annonce=False))
        with unittest.mock.patch("urllib.request.urlopen", faux):
            r = extraction.telecharger(self.fichier, url="http://x",
                                       patienter=lambda _: None)
        self.assertEqual(r["octets"], 4)

    def test_tant_que_des_octets_arrivent_on_continue(self):
        """Une tentative fructueuse ne doit pas consommer le budget.

        Sans cette nuance, six tentatives courtes mais fructueuses épuisaient
        les essais à 13 Mo sur 297 (constaté le 2026-08-31).
        """
        morceaux = [self.Reponse([b"a"], coupe=True, total=6, status=206)
                    for _ in range(5)]
        morceaux.append(self.Reponse([b"a"], status=206, total=6))
        faux, vues, reste = self._serveur(*morceaux)
        with unittest.mock.patch("urllib.request.urlopen", faux):
            r = extraction.telecharger(self.fichier, url="http://x", essais=2,
                                       patienter=lambda _: None)
        self.assertEqual(r["octets"], 6)
        self.assertEqual(reste, [])

    def test_apres_des_tentatives_steriles_l_erreur_remonte(self):
        """Mieux vaut un échec visible qu'une publication de données vides."""
        faux, _, _ = self._serveur(
            self.Reponse([b"debut"], coupe=True, total=99),
            *[self.Reponse([], coupe=True, total=99, status=206) for _ in range(3)])
        with unittest.mock.patch("urllib.request.urlopen", faux):
            with self.assertRaises(http.client.IncompleteRead):
                extraction.telecharger(self.fichier, url="http://x", essais=3,
                                       patienter=lambda _: None)

    def test_une_reponse_http_en_erreur_n_est_pas_reessayee(self):
        """Redemander un 404 ne changerait rien."""
        refus = urllib.error.HTTPError("http://x", 404, "absent", {}, None)
        suite = [refus, self.Reponse([b"jamais lu"])]

        def faux(requete, **_k):
            issue = suite.pop(0)
            if isinstance(issue, Exception):
                raise issue
            return issue
        with unittest.mock.patch("urllib.request.urlopen", faux):
            with self.assertRaises(urllib.error.HTTPError):
                extraction.telecharger(self.fichier, url="http://x",
                                       patienter=lambda _: None)
        self.assertEqual(len(suite), 1)   # le second essai n'a pas eu lieu

    def test_un_304_ne_touche_pas_au_fichier(self):
        refus = urllib.error.HTTPError("http://x", 304, "inchangé", {}, None)

        def faux(*_a, **_k):
            raise refus
        with unittest.mock.patch("urllib.request.urlopen", faux):
            r = extraction.telecharger(self.fichier, {"If-None-Match": "e1"},
                                       url="http://x", patienter=lambda _: None)
        self.assertFalse(r["modifie"])
        self.assertEqual(r["etag"], "e1")

    def setUp(self):
        self.repertoire = tempfile.TemporaryDirectory()
        self.fichier = pathlib.Path(self.repertoire.name) / "archive.zip"

    def tearDown(self):
        self.repertoire.cleanup()


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
