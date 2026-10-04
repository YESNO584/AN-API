#!/usr/bin/env python3
"""Les règles de lecture des sources du Sénat.

Ni réseau, ni vraie base : des morceaux de sources réelles, recopiés.

    ./test_senat.py
"""

import io
import pathlib
import sys
import tempfile
import unittest

import senat


class LeSignetFaitLePont(unittest.TestCase):
    """C'est la seule clé entre les deux chambres, et les deux la publient."""

    def test_un_texte_ordinaire(self):
        self.assertEqual(
            senat.signet_de("https://www.senat.fr/dossier-legislatif/pjl25-689.html"),
            "pjl25-689")

    def test_l_ancienne_forme_de_l_adresse(self):
        """`/dossierleg/` a précédé `/dossier-legislatif/`."""
        self.assertEqual(
            senat.signet_de("http://www.senat.fr/dossierleg/ppl00-074.html"),
            "ppl00-074")

    def test_un_texte_budgetaire_n_a_pas_de_tiret(self):
        """Quatre textes de finances étaient perdus par une règle qui exigeait
        un tiret (mesuré le 2026-10-04)."""
        for url, attendu in (
                ("https://www.senat.fr/dossier-legislatif/plfss2026.html", "plfss2026"),
                ("http://www.senat.fr/dossier-legislatif/pjlf2025.html", "pjlf2025")):
            self.assertEqual(senat.signet_de(url), attendu)

    def test_rien_d_autre_ne_passe(self):
        self.assertIsNone(senat.signet_de("https://www.senat.fr/senateur/x.html"))
        self.assertIsNone(senat.signet_de(""))
        self.assertIsNone(senat.signet_de(None))


# Un extrait vrai de la page des scrutins de la session 2025-2026.
PAGE = """
<p class="my-2"> <a href="2025/scr2025-340.html">Scrutin N&deg;340</a>&nbsp;:
sur l'ensemble du projet de loi d'urgence - <a
href="/dossier-legislatif/pjl25-689.html">consulter le dossier l&eacute;gislatif</a>.
<span class="badge">Adoption</span> </p>
<p class="my-2"> <a href="2025/scr2025-339.html">Scrutin N&deg;339</a>&nbsp;:
sur l'ensemble de la proposition de loi - <a
href="/dossier-legislatif/ppl25-304.html">consulter le dossier</a>. </p>
<p class="my-2"> <a href="2025/scr2025-130.html">Scrutin N&deg;130</a>&nbsp;:
sur la d&eacute;claration du Gouvernement. </p>
"""


class LaPageDesScrutins(unittest.TestCase):
    """Le seul endroit où le Sénat relie un scrutin à un texte."""

    def test_chaque_scrutin_prend_son_dossier(self):
        self.assertEqual(senat.scrutins_de_la_page(PAGE), {
            (2025, 340): "pjl25-689",
            (2025, 339): "ppl25-304",
            (2025, 130): None,
        })

    def test_un_scrutin_sans_dossier_ne_prend_pas_celui_du_suivant(self):
        """La déclaration du Gouvernement est la dernière : si la règle
        débordait, elle lui donnerait un texte qu'elle n'a pas."""
        self.assertIsNone(senat.scrutins_de_la_page(PAGE)[(2025, 130)])

    def test_la_mise_en_page_ne_compte_pas(self):
        """Le jour où le Sénat refera sa page, seules les adresses doivent
        importer. On retire toutes les classes et tous les mots."""
        nu = PAGE.replace('class="my-2"', "").replace("<p", "<div").replace(
            "consulter le dossier l&eacute;gislatif", "ici")
        self.assertEqual(senat.scrutins_de_la_page(nu)[(2025, 340)], "pjl25-689")

    def test_une_page_vide_se_voit(self):
        self.assertEqual(senat.page_lisible({}), "aucun scrutin lu sur la page")

    def test_une_page_qui_a_perdu_ses_liens_se_voit(self):
        """C'est le cas qui, sans garde-fou, publierait « aucun vote au Sénat »
        sur tous les textes."""
        casse = {(2025, n): None for n in range(100)}
        casse[(2025, 1)] = "pjl25-689"
        self.assertIn("moins de 90", senat.page_lisible(casse))

    def test_une_page_qui_rapetisse_se_voit(self):
        """Une page de session ne fait que grandir : moins de scrutins qu'hier
        veut dire qu'on ne la lit plus correctement."""
        # Une page réaliste : les vraies en portent de 129 à 445, dont 97 à
        # 100 % avec un dossier.
        bonne = {(2025, n): f"pjl25-{n}" for n in range(100)}
        self.assertIsNone(senat.page_lisible(bonne))
        self.assertIn("contre 120", senat.page_lisible(bonne, attendus=120))



DUMP = """\
COPY loi (loicod, signet, loiint) FROM stdin;
150         \tpjl99-342\td'orientation pour l'outre-mer
138         \t\\N\tun texte sans signet
\\.
COPY autre (x) FROM stdin;
1
\\.
"""


class LireUnDump(unittest.TestCase):
    def test_les_colonnes_sont_nommees_par_l_entete(self):
        l = list(senat.lignes_du_dump(io.StringIO(DUMP), "loi"))
        self.assertEqual(len(l), 2)
        self.assertEqual(l[0]["signet"], "pjl99-342")

    def test_la_valeur_absente_devient_rien(self):
        l = list(senat.lignes_du_dump(io.StringIO(DUMP), "loi"))
        self.assertIsNone(l[1]["signet"])

    def test_la_lecture_s_arrete_a_la_fin_de_la_table(self):
        """Sans le « \\\\. », la lecture d'une table avalerait la suivante."""
        self.assertEqual(len(list(senat.lignes_du_dump(io.StringIO(DUMP), "autre"))), 1)

    def test_les_colonnes_a_largeur_fixe_se_nettoient(self):
        l = list(senat.lignes_du_dump(io.StringIO(DUMP), "loi"))
        self.assertEqual(senat.net(l[0]["loicod"]), "150")
        self.assertIsNone(senat.net(None))


class LireUnCsvDuSenat(unittest.TestCase):
    def ecrire(self, contenu):
        d = tempfile.mkdtemp()
        f = pathlib.Path(d) / "x.csv"
        f.write_bytes(contenu.encode("latin-1"))
        return f

    def test_latin1_et_lignes_de_commentaire(self):
        """Lu en UTF-8, le fichier affiche « S?nateur » ; sans sauter les
        lignes « % », l'en-tête est faux."""
        f = self.ecrire("% un commentaire\nMatricule;Nom\n01;Sénateur\n")
        self.assertEqual(senat.lire_csv_senat(f),
                         [{"Matricule": "01", "Nom": "Sénateur"}])

    def test_le_separateur_change_d_un_fichier_a_l_autre(self):
        """Les fichiers de sénateurs emploient la virgule, celui des dossiers
        le point-virgule. Forcer l'un rendait une seule colonne, sans erreur."""
        f = self.ecrire("% requête\nMatricule,Nom,Groupe\n83008P,Abadie,RDSE\n")
        self.assertEqual(senat.lire_csv_senat(f),
                         [{"Matricule": "83008P", "Nom": "Abadie",
                           "Groupe": "RDSE"}])

    def test_un_fichier_vide_ne_casse_pas(self):
        self.assertEqual(senat.lire_csv_senat(self.ecrire("% rien\n")), [])


class LesThemesDUnTexte(unittest.TestCase):
    """Le Sénat classe chaque dossier ; l'application n'avait aucune notion de
    sujet avant lui."""

    def test_un_theme_simple(self):
        self.assertEqual(senat.themes_de("Justice"), ["Justice"])

    def test_plusieurs_themes_se_decoupent_sur_la_virgule(self):
        self.assertEqual(
            senat.themes_de("Collectivités territoriales, Pouvoirs publics et Constitution"),
            ["Collectivités territoriales", "Pouvoirs publics et Constitution"])

    def test_un_nom_de_theme_peut_contenir_une_virgule(self):
        """Trois en contiennent une, et le découpage naïf en inventait trois
        qui n'existent pas : « fiscalité », « commerce et artisanat »,
        « sciences et techniques »."""
        for valeur, attendu in (
                ("Économie et finances, fiscalité",
                 ["Économie et finances, fiscalité"]),
                ("PME, commerce et artisanat", ["PME, commerce et artisanat"]),
                ("Recherche, sciences et techniques",
                 ["Recherche, sciences et techniques"])):
            self.assertEqual(senat.themes_de(valeur), attendu)

    def test_un_nom_compose_melange_aux_autres(self):
        self.assertEqual(
            senat.themes_de("Société, Économie et finances, fiscalité, Travail"),
            ["Économie et finances, fiscalité", "Société", "Travail"])

    def test_rien_ne_donne_rien(self):
        self.assertEqual(senat.themes_de(""), [])
        self.assertEqual(senat.themes_de(None), [])
        self.assertEqual(senat.themes_de("  "), [])


class LOrdreDesGroupes(unittest.TestCase):
    """Il ne peut pas se mesurer sur les sièges au Sénat : on le mesure sur la
    façon de voter."""

    def test_la_gauche_et_la_droite_se_separent(self):
        # Deux blocs qui votent à l'opposé, et un groupe au milieu.
        positions = {
            "GAUCHE1": {"a": 0.0, "b": 0.0, "c": 1.0},
            "GAUCHE2": {"a": 0.0, "b": 0.1, "c": 1.0},
            "MILIEU":  {"a": 0.5, "b": 0.5, "c": 0.5},
            "DROITE1": {"a": 1.0, "b": 1.0, "c": 0.0},
            "DROITE2": {"a": 1.0, "b": 0.9, "c": 0.0},
        }
        rang = senat.rang_par_les_votes(positions)
        self.assertEqual(set(rang), set(positions))
        gauche = [rang.index("GAUCHE1"), rang.index("GAUCHE2")]
        droite = [rang.index("DROITE1"), rang.index("DROITE2")]
        self.assertTrue(max(gauche) < min(droite) or max(droite) < min(gauche),
                        f"les deux blocs sont mêlés : {rang}")
        self.assertLess(min(gauche + droite), rang.index("MILIEU"))
        self.assertGreater(max(gauche + droite), rang.index("MILIEU"))

    def test_un_depart_malheureux_ne_rend_plus_l_ordre_alphabetique(self):
        """Le vecteur de départ alterné pouvait être orthogonal au signal, et
        la méthode rendait alors l'ordre alphabétique **sans rien dire**."""
        # Deux groupes exactement opposés : c'est le cas qui annulait tout.
        positions = {"ZGAUCHE": {"a": 0.0}, "ADROITE": {"a": 1.0}}
        self.assertEqual(senat.rang_par_les_votes(positions),
                         ["ZGAUCHE", "ADROITE"])

    def test_des_groupes_qui_votent_pareil_ne_se_rangent_pas(self):
        positions = {"A": {"x": 0.5}, "B": {"x": 0.5}, "C": {"x": 0.5}}
        self.assertEqual(senat.rang_par_les_votes(positions), ["A", "B", "C"])

    def test_un_seul_groupe_ne_se_range_pas(self):
        self.assertEqual(senat.rang_par_les_votes({"SEUL": {"a": 1.0}}), ["SEUL"])
        self.assertEqual(senat.rang_par_les_votes({}), [])


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
