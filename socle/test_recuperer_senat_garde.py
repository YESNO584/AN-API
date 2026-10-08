"""Ce qui empêche une source du Sénat en panne de coûter des données au site : la construction à côté, le refus de remplacer par pire, une page web servie en CSV.

    ./test_recuperer_senat_garde.py
"""
from __future__ import annotations

import sys
import pathlib
import sqlite3
import tempfile
import unittest
import recuperer_senat as rs
import senat
from decor_senat import SCHEMA, base


class LaBaseSeConstruitACote(unittest.TestCase):
    """**Une reconstruction qui échoue ne doit rien coûter au site.**

    Le 2026-10-06, `data.senat.fr` a rendu une page web à la place des deux
    fichiers de sénateurs. La construction écrivait directement dans la base
    publiée : elle s'est arrêtée, a laissé une base vide, et l'onglet « Sénat »
    a perdu d'un coup la composition, le calendrier et les 30 sujets — sans que
    la publication, marquée « réussie », le signale.

    Ces tests tiennent le garde-fou : **ce qui sort du chantier doit valoir
    mieux que ce qu'il remplace, sinon on garde la veille.**
    """

    def poser(self, chemin, senateurs=348, dossiers=12450, themes=17185):
        cx = sqlite3.connect(chemin)
        cx.executescript(SCHEMA.read_text(encoding="utf-8"))
        cx.executemany("INSERT INTO senateur (matricule, nom) VALUES (?,?)",
                       [(str(i), f"S{i}") for i in range(senateurs)])
        cx.executemany("INSERT INTO dossier_senat (signet) VALUES (?)",
                       [(f"ppl-{i}",) for i in range(dossiers)])
        cx.executemany("INSERT INTO theme_senat (signet, theme, rang)"
                       " VALUES (?,?,0)",
                       [(f"ppl-{i}", "Justice") for i in range(themes)])
        cx.commit(); cx.close()

    def setUp(self):
        self.dossier = pathlib.Path(tempfile.mkdtemp())
        self.vieille = self.dossier / "senat.db"
        self.neuve = self.dossier / "senat.db.chantier"

    def test_perdre_les_senateurs_de_la_veille_est_refuse(self):
        # Le cas du 2026-10-06 : la source des sénateurs rend une page web.
        # On avait 348 sénateurs, la base neuve n'en a aucun : c'est une perte.
        self.poser(self.vieille)
        self.poser(self.neuve, senateurs=0)
        self.assertIn("composition",
                      rs.assez_pour_remplacer(self.neuve, self.vieille))

    def test_une_base_entierement_vide_ne_se_publie_jamais(self):
        # Sans base de la veille, la comparaison ne peut rien dire : c'est le
        # seul garde-fou qui reste, et c'est le cas d'un cache perdu.
        self.poser(self.neuve, senateurs=0, dossiers=0, themes=0)
        self.assertFalse(self.vieille.exists())
        self.assertIn("vide", rs.assez_pour_remplacer(self.neuve, self.vieille))

    def test_une_base_partielle_vaut_mieux_que_rien(self):
        # **Ne jamais refuser mieux.** Le 2026-10-06, les dossiers et les
        # sujets arrivaient parfaitement pendant que les sénateurs manquaient.
        # Exiger les trois gelait trois écrans pour en protéger un — alors
        # qu'un écran qui dit « pas de données » est honnête.
        self.poser(self.neuve, senateurs=0)
        self.assertFalse(self.vieille.exists())
        self.assertIsNone(rs.assez_pour_remplacer(self.neuve, self.vieille))

    def test_une_base_partielle_ne_remplace_pas_une_base_complete(self):
        self.poser(self.vieille)
        self.poser(self.neuve, senateurs=0)
        self.assertIsNotNone(rs.assez_pour_remplacer(self.neuve, self.vieille))

    def test_une_base_sans_sujets_ne_remplace_pas_une_qui_en_a(self):
        self.poser(self.vieille)
        self.poser(self.neuve, themes=0)
        self.assertIn("sujets",
                      rs.assez_pour_remplacer(self.neuve, self.vieille))

    def test_une_chute_brutale_ne_remplace_rien(self):
        # Une source à moitié lue : 100 sénateurs sur 348. Ce n'est pas une
        # actualité du Parlement, c'est une source abîmée.
        self.poser(self.vieille)
        self.poser(self.neuve, senateurs=100)
        souci = rs.assez_pour_remplacer(self.neuve, self.vieille)
        self.assertIsNotNone(souci)
        self.assertIn("348", souci)

    def test_une_base_complete_remplace(self):
        self.poser(self.vieille)
        self.poser(self.neuve, senateurs=349, dossiers=12460)
        self.assertIsNone(rs.assez_pour_remplacer(self.neuve, self.vieille))

    def test_une_variation_normale_passe(self):
        # Un sénateur qui démissionne ne doit pas bloquer la publication.
        self.poser(self.vieille)
        self.poser(self.neuve, senateurs=347)
        self.assertIsNone(rs.assez_pour_remplacer(self.neuve, self.vieille))

    def test_la_premiere_construction_n_a_rien_a_depasser(self):
        self.poser(self.neuve)
        self.assertIsNone(rs.assez_pour_remplacer(self.neuve, self.vieille))

    def test_une_base_illisible_ne_remplace_rien(self):
        self.poser(self.vieille)
        self.neuve.write_bytes(b"ceci n'est pas une base")
        self.assertIn("lisible",
                      rs.assez_pour_remplacer(self.neuve, self.vieille))


class UneSourceQuiNEnEstPlusUne(unittest.TestCase):
    """Le pire genre de panne : `200 OK`, `Content-Type: text/csv`, et du HTML.

    C'est ce que `data.senat.fr` a servi le 2026-10-06 pour ses deux fichiers
    de sénateurs. Rien ne clochait, sauf le contenu.
    """

    def ecrire(self, texte):
        f = self.dossier / "essai.csv"
        f.write_text(texte, encoding="latin-1")
        return f

    def setUp(self):
        self.dossier = pathlib.Path(tempfile.mkdtemp())

    def test_une_page_web_servie_en_csv_ne_rend_aucune_ligne(self):
        page = ("<!DOCTYPE html>\n<head><link rel=\"stylesheet\" href=\"/x.css\" />"
                "</head>\n<body>Erreur</body>\n")
        self.assertEqual(senat.lire_csv_senat(self.ecrire(page)), [])

    def test_les_autres_formes_de_page_sont_vues_aussi(self):
        for tete in ("<html>", "<?xml version=\"1.0\"?>", "  <!doctype HTML>",
                     "<head>", "<body>"):
            self.assertEqual(
                senat.lire_csv_senat(self.ecrire(tete + "\nsuite\n")), [])

    def test_un_vrai_csv_se_lit_toujours(self):
        vrai = "Matricule,Nom usuel\n21071F,Aeschlimann\n"
        self.assertEqual(senat.lire_csv_senat(self.ecrire(vrai)),
                         [{"Matricule": "21071F", "Nom usuel": "Aeschlimann"}])

    def test_un_csv_dont_une_valeur_ressemble_a_du_html_se_lit(self):
        # La garde porte sur l'en-tête, pas sur le contenu : une colonne qui
        # contiendrait une balise ne doit pas faire jeter le fichier.
        vrai = "Matricule,Note\n21071F,<b>gras</b>\n"
        self.assertEqual(len(senat.lire_csv_senat(self.ecrire(vrai))), 1)

    def test_un_historique_vide_ne_fait_pas_tomber_la_lecture(self):
        # Sans la garde, ce fichier levait `KeyError: 'Matricule'` et arrêtait
        # toute la construction.
        page = "<!DOCTYPE html>\n<body>Erreur</body>\n"
        self.assertEqual(rs.lire_historique(self.ecrire(page)), {})


class UneSourceCasseeNEnBloquePasQuatre(unittest.TestCase):
    """Le 2026-10-06, tout le dossier `senateurs/` de `data.senat.fr` rendait
    une page web — y compris pour un nom de fichier inventé — pendant que les
    dossiers, les scrutins, les séances et les sujets arrivaient parfaitement.

    Sans cette porte, un seul dossier en panne gelait toute la base du Sénat :
    la liste des sénateurs sortait vide, le garde-fou refusait de remplacer, et
    plus rien ne se mettait à jour.
    """

    SENATEUR = {"Matricule": "1", "Qualité": "M.", "Prénom usuel": "Jean",
                "Nom usuel": "Dupont", "Circonscription": "Ain",
                "Groupe politique": "SER", "État": "ACTIF"}
    HISTORIQUE = {"1": [("2023-10-01", "", "SOC", "SER")]}

    def peuplee(self, combien=348):
        cx = base()
        cx.executemany("INSERT INTO senateur (matricule, nom, groupe)"
                       " VALUES (?,?,?)",
                       [(str(i), f"S{i}", "SOC") for i in range(combien)])
        return cx

    def combien(self, cx):
        return cx.execute("SELECT COUNT(*) FROM senateur").fetchone()[0]

    def test_sans_liste_de_senateurs_la_table_n_est_pas_videe(self):
        cx = self.peuplee()
        n, noms, alertes = rs.senateurs_a_jour(cx, [], self.HISTORIQUE)
        self.assertEqual(self.combien(cx), 348)
        self.assertEqual(n, 348)
        self.assertEqual(noms, {})          # pour ne pas réécrire les groupes
        self.assertIn("la liste des sénateurs", alertes[0])

    def test_sans_historique_la_table_n_est_pas_videe_non_plus(self):
        cx = self.peuplee()
        rs.senateurs_a_jour(cx, [self.SENATEUR], {})
        self.assertEqual(self.combien(cx), 348)

    def test_les_deux_sources_manquantes_sont_toutes_deux_nommees(self):
        cx = self.peuplee()
        _, _, alertes = rs.senateurs_a_jour(cx, [], {})
        self.assertIn("la liste des sénateurs", alertes[0])
        self.assertIn("historique des groupes", alertes[0])

    def test_avec_les_deux_sources_la_liste_se_remplace(self):
        cx = self.peuplee()
        n, noms, alertes = rs.senateurs_a_jour(cx, [self.SENATEUR],
                                               self.HISTORIQUE)
        self.assertEqual(self.combien(cx), 1)
        self.assertEqual(n, 1)
        self.assertEqual(noms.get("SOC"), "SER")
        self.assertEqual(alertes, [])

    def test_ranger_senateurs_avec_une_liste_vide_vide_bien_la_table(self):
        # **C'est la raison d'être de la porte** : appelée avec une liste vide,
        # cette fonction efface tout. Si ce test cesse d'échouer sans la porte,
        # c'est que la fonction a changé et que la porte ne sert plus.
        cx = base()
        cx.executemany("INSERT INTO senateur (matricule, nom) VALUES (?,?)",
                       [(str(i), f"S{i}") for i in range(348)])
        rs.ranger_senateurs(cx, [], {})
        self.assertEqual(
            cx.execute("SELECT COUNT(*) FROM senateur").fetchone()[0], 0)


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
