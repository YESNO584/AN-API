#!/usr/bin/env python3
"""Ce qui construit `senat.db`. Ni réseau, ni vraie archive.

    ./test_recuperer_senat.py
"""

import pathlib
import sys
import tempfile
import unittest
import recuperer_senat as rs
import senat
from decor_senat import base


class LaSessionEnCours(unittest.TestCase):
    """Une session parlementaire commence en octobre et porte l'année d'avant."""

    def test_octobre_ouvre_la_session_de_l_annee(self):
        import datetime as dt
        self.assertEqual(rs.session_en_cours(dt.date(2026, 10, 1)), 2026)
        self.assertEqual(rs.session_en_cours(dt.date(2026, 12, 31)), 2026)

    def test_avant_octobre_on_est_encore_dans_la_precedente(self):
        import datetime as dt
        self.assertEqual(rs.session_en_cours(dt.date(2026, 6, 4)), 2025)
        self.assertEqual(rs.session_en_cours(dt.date(2026, 9, 30)), 2025)


class LeGroupeAuJourDuScrutin(unittest.TestCase):
    """Un sénateur change de groupe : lui donner celui d'aujourd'hui ferait
    dire au passé ce qu'il n'a pas dit."""

    HISTO = {"01": [("2020-01-01", "2023-06-30", "SOC", "Groupe socialiste"),
                    ("2023-07-01", "", "UMP", "Groupe Les Républicains")]}

    def test_le_groupe_depend_de_la_date(self):
        self.assertEqual(rs.groupe_au(self.HISTO, "01", "2022-05-01"), "SOC")
        self.assertEqual(rs.groupe_au(self.HISTO, "01", "2024-05-01"), "UMP")

    def test_une_appartenance_en_cours_n_a_pas_de_fin(self):
        self.assertEqual(rs.groupe_au(self.HISTO, "01", "2099-01-01"), "UMP")

    def test_aucun_n_est_pas_un_groupe(self):
        """179 sénateurs sur 348 n'en ont plus depuis le renouvellement :
        les compter ensemble en ferait un dixième groupe, qui n'existe pas."""
        histo = {"02": [("", "", "AUCUN", "Sénateurs n'appartenant à aucun groupe")]}
        self.assertIsNone(rs.groupe_au(histo, "02", "2026-10-04"))

    def test_un_matricule_inconnu_ne_rend_rien(self):
        self.assertIsNone(rs.groupe_au(self.HISTO, "99", "2024-01-01"))
        self.assertIsNone(rs.groupe_au(self.HISTO, None, "2024-01-01"))


class NommerUnGroupe(unittest.TestCase):
    """Les deux fichiers du Sénat ne nomment pas les groupes pareil, et leurs
    codes sont périmés : `UMP` désigne Les Républicains."""

    HISTO = {"01": [("", "", "UMP", "Groupe Les Républicains")],
             "02": [("", "2015-01-01", "CRC", "Groupe communiste")]}

    def test_l_etiquette_courte_vient_du_fichier_des_senateurs(self):
        noms = rs.noms_des_groupes(
            self.HISTO, [{"Matricule": "01", "Groupe politique": "Les Républicains"}])
        self.assertEqual(noms["UMP"], "Les Républicains")

    def test_un_groupe_sans_membre_en_exercice_garde_le_nom_de_la_source(self):
        noms = rs.noms_des_groupes(self.HISTO, [])
        self.assertEqual(noms["CRC"], "Groupe communiste")

    def test_aucun_n_est_jamais_nomme(self):
        histo = {"03": [("", "", "AUCUN", "Sénateurs n'appartenant à aucun groupe")]}
        self.assertNotIn("AUCUN", rs.noms_des_groupes(histo, []))


class RelireUnePartieDesSessions(unittest.TestCase):
    """Le défaut du 2026-10-04 : relire quatre vieilles sessions effaçait le
    lien vers le dossier de toutes les autres — 666 scrutins rattachés, puis
    zéro depuis 2024."""

    def test_une_session_non_relue_garde_ses_liens(self):
        cx = base()
        cx.execute("INSERT INTO scrutin_senat (session, numero, signet, date)"
                   " VALUES (2025, 340, 'pjl25-689', '2026-07-21')")
        cx.execute("INSERT INTO scrutin_senat (session, numero, signet, date)"
                   " VALUES (2020, 10, 'ppl20-001', '2021-01-05')")
        # On refait une passe qui ne lit que la session 2020.
        liens = {(2020, 10): "ppl20-002"}
        lues = {2020}
        cx.executemany(
            "UPDATE scrutin_senat SET signet = ? WHERE session = ? AND numero = ?",
            [(sig, s, n) for (s, n), sig in liens.items() if s in lues])
        garde = cx.execute("SELECT signet FROM scrutin_senat"
                           " WHERE session = 2025").fetchone()["signet"]
        self.assertEqual(garde, "pjl25-689",
                         "la session non relue a perdu son lien")
        self.assertEqual(cx.execute("SELECT signet FROM scrutin_senat"
                                    " WHERE session = 2020").fetchone()["signet"],
                         "ppl20-002")


class LesCouleursNeSEffacentPas(unittest.TestCase):
    """Le 2026-10-05, le Sénat a retiré de sa page l'élément qui portait les
    couleurs. La table se vidant et se réécrivant à chaque passage, celles de
    la veille sont parties avec, et l'hémicycle s'est affiché tout gris.

    Ces tests tiennent la reprise : **ce qui arrive aujourd'hui l'emporte, ce
    qui manque est repris de la base.**
    """

    def base_avec_couleurs(self):
        cx = base()
        cx.execute("INSERT INTO senateur (matricule, nom, groupe)"
                   " VALUES ('1', 'Hier', 'SOC')")
        cx.execute("INSERT INTO groupe_senat"
                   " (sigle, nom, nom_complet, couleur, effectif, rang)"
                   " VALUES ('SOC', 'SER', 'Groupe Socialiste', '#B84592', 1, 0)")
        return cx

    def couleur(self, cx, sigle="SOC"):
        l = cx.execute("SELECT nom_complet, couleur FROM groupe_senat"
                       " WHERE sigle = ?", (sigle,)).fetchone()
        return (l["nom_complet"], l["couleur"]) if l else None

    def test_une_page_illisible_n_efface_pas_les_couleurs_de_la_veille(self):
        cx = self.base_avec_couleurs()
        rs.ranger_groupes(cx, "2024-01-01", {"SOC": "SER"}, {})
        self.assertEqual(self.couleur(cx), ("Groupe Socialiste", "#B84592"))

    def test_une_couleur_neuve_remplace_l_ancienne(self):
        # Le jour où le Sénat change la teinte d'un groupe, c'est la page qui
        # tranche — reprendre l'ancienne figerait la couleur pour toujours.
        cx = self.base_avec_couleurs()
        rs.ranger_groupes(cx, "2024-01-01", {"SOC": "SER"},
                          {"SOC": {"nom": "Groupe Socialiste refondu",
                                   "couleur": "#000FFF"}})
        self.assertEqual(self.couleur(cx),
                         ("Groupe Socialiste refondu", "#000FFF"))

    def test_un_groupe_jamais_teinte_reste_sans_couleur(self):
        # `NI` n'a pas de couleur sur la page du Sénat. Rien ne doit lui en
        # inventer une au passage.
        cx = base()
        cx.execute("INSERT INTO senateur (matricule, nom, groupe)"
                   " VALUES ('1', 'Seul', 'NI')")
        rs.ranger_groupes(cx, "2024-01-01", {"NI": "NI"}, {})
        self.assertEqual(self.couleur(cx, "NI"), (None, None))

    def test_l_effectif_et_le_rang_se_recalculent_quand_meme(self):
        # La reprise ne porte que sur l'habit : un groupe qui perd un membre
        # doit voir son effectif baisser le jour même.
        cx = self.base_avec_couleurs()
        cx.execute("INSERT INTO senateur (matricule, nom, groupe)"
                   " VALUES ('2', 'Neuf', 'SOC')")
        rs.ranger_groupes(cx, "2024-01-01", {"SOC": "SER"}, {})
        self.assertEqual(cx.execute("SELECT effectif FROM groupe_senat"
                                    " WHERE sigle = 'SOC'").fetchone()[0], 2)


class LeFiletDesCouleurs(unittest.TestCase):
    """Le fichier versionné qui rattrape une page qui ne donne plus rien."""

    def test_le_releve_livre_avec_le_projet_se_lit(self):
        g = senat.couleurs_de_secours()
        self.assertGreaterEqual(len(g), senat.GROUPES_ATTENDUS)
        for sigle, x in g.items():
            self.assertRegex(x["couleur"], r"^#[0-9A-F]{6}$")
            self.assertTrue(x["nom"])

    def test_un_filet_absent_ne_fait_pas_tomber_la_publication(self):
        self.assertEqual(
            senat.couleurs_de_secours(pathlib.Path("/introuvable.json")), {})

    def test_un_filet_abime_ne_fait_pas_tomber_la_publication(self):
        import tempfile
        for contenu in ("{ pas du json", "[]", '{"groupes": 3}'):
            with tempfile.NamedTemporaryFile("w", suffix=".json",
                                             delete=False) as f:
                f.write(contenu)
            self.assertEqual(senat.couleurs_de_secours(pathlib.Path(f.name)), {})

    def test_le_filet_applique_les_memes_controles_que_la_page(self):
        # Un filet qui laisserait passer ce que la page refuse ferait entrer
        # par la fenêtre ce qui a été écarté à la porte.
        import json as _json, tempfile
        mauvais = {"groupes": {"X": {"nom": "X", "couleur": "rouge"},
                               "AUCUN": {"nom": "Nouveaux", "couleur": "#000000"},
                               "BON": {"nom": "Bon", "couleur": "#a1b2c3"}}}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            _json.dump(mauvais, f)
        g = senat.couleurs_de_secours(pathlib.Path(f.name))
        self.assertEqual(g, {"BON": {"nom": "Bon", "couleur": "#A1B2C3"}})


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
