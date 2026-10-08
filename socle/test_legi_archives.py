"""Lire le dépôt du droit consolidé : un fichier d'article, une archive, une archive tronquée — et ce qu'une loi ajoute.

    ./test_legi_archives.py
"""
from __future__ import annotations

import sys
import io
import tarfile
import unittest
import legi
from decor_legi import RENVOI, article, loi, version, LIEN


class LireUnFichierD_Article(unittest.TestCase):

    def test_tout_ce_qu_on_retient_est_lu(self):
        xml = article(
            texte="<p>Dans chaque école&nbsp;et établissement.</p>",
            versions=[version("AVANT", "2019-09-02", "2026-09-01"),
                      version("LEGIARTI000000000001", "2026-09-01", legi.SANS_FIN, "VIGUEUR")],
            liens=[LIEN.format("MODIFIE")])
        lu = legi.lire_article(xml)
        self.assertEqual(lu["id"], "LEGIARTI000000000001")
        self.assertEqual(lu["numero"], "L401-1")
        self.assertEqual(lu["ou"], "Code de l'éducation")
        self.assertEqual(lu["etat"], "VIGUEUR")
        self.assertEqual(lu["texte"], "Dans chaque école et établissement.")
        self.assertEqual(lu["precedent"], "AVANT")
        self.assertEqual(lu["changements"][0]["loi"], "2026-798")

    def test_les_entites_html_sont_rendues_lisibles(self):
        lu = legi.lire_article(article(texte="<p>l&apos;article L&nbsp;5 &amp; suivants</p>"))
        self.assertEqual(lu["texte"], "l'article L 5 & suivants")


class LireLeDepot(unittest.TestCase):

    PAGE = ('<a href="DILA_LEGI_Presentation_20170824.pdf">…</a>'
            '<a href="Freemium_legi_global_20250713-140000.tar.gz">…</a>'
            '<a href="LEGI_20250713-205013.tar.gz">…</a>'
            '<a href="LEGI_20250712-211706.tar.gz">…</a>')

    def test_le_socle_et_les_quotidiennes_sont_separes(self):
        socle, jours = legi.archives_du_depot(self.PAGE)
        self.assertEqual(socle, "Freemium_legi_global_20250713-140000.tar.gz")
        self.assertEqual(jours, ["LEGI_20250712-211706.tar.gz",
                                 "LEGI_20250713-205013.tar.gz"])

    def test_les_quotidiennes_sont_rendues_dans_l_ordre_des_dates(self):
        """Le dépôt ne les liste pas triées ; on les applique dans l'ordre."""
        _, jours = legi.archives_du_depot(self.PAGE)
        self.assertEqual(jours, sorted(jours))

    def test_un_depot_sans_socle_ne_plante_pas(self):
        socle, jours = legi.archives_du_depot('<a href="LEGI_20250712-211706.tar.gz">…</a>')
        self.assertIsNone(socle)
        self.assertEqual(len(jours), 1)


class ParcourirUneArchive(unittest.TestCase):

    def _archive(self, fichiers):
        tampon = io.BytesIO()
        with tarfile.open(fileobj=tampon, mode="w:gz") as arc:
            for nom, contenu in fichiers:
                info = tarfile.TarInfo(nom)
                info.size = len(contenu)
                arc.addfile(info, io.BytesIO(contenu))
        tampon.seek(0)
        return tampon

    def test_seuls_les_fichiers_d_articles_sont_rendus(self):
        arc = self._archive([
            ("legi/global/code/article/LEGI/ARTI/00/LEGIARTI001.xml", b"<ARTICLE/>"),
            ("legi/global/code/section_ta/LEGI/SCTA/00/LEGISCTA001.xml", b"<SECTION/>"),
            ("legi/global/code/texte/LEGI/TEXT/00/LEGITEXT001.xml", b"<TEXTE/>"),
        ])
        noms = [nom for nom, _ in legi.parcourir_archive(arc)]
        self.assertEqual(len(noms), 1)
        self.assertTrue(noms[0].endswith("LEGIARTI001.xml"))

    def test_les_repertoires_ne_sont_pas_pris_pour_des_articles(self):
        tampon = io.BytesIO()
        with tarfile.open(fileobj=tampon, mode="w:gz") as arc:
            info = tarfile.TarInfo("legi/global/code/article/")
            info.type = tarfile.DIRTYPE
            arc.addfile(info)
        tampon.seek(0)
        self.assertEqual(list(legi.parcourir_archive(tampon)), [])


class UneArchiveTronquee(unittest.TestCase):
    """Un transfert coupé doit se voir — c'est la seule façon de le rattraper."""

    def _archive(self, fichiers):
        tampon = io.BytesIO()
        with tarfile.open(fileobj=tampon, mode="w:gz") as arc:
            for i in range(fichiers):
                info = tarfile.TarInfo(f"legi/global/code/article/LEGIARTI{i}.xml")
                info.size = 10
                arc.addfile(info, io.BytesIO(b"<ARTICLE/>"))
        return tampon.getvalue()

    def test_une_archive_minuscule_reste_valable(self):
        """La plus petite archive quotidienne du dépôt pèse 5,3 ko : une journée
        où presque rien ne change. Juger une archive sur sa taille rejetait
        celle du 25 février 2026, 17 ko et parfaitement valable (constaté le
        2026-09-02)."""
        entier = self._archive(1)
        self.assertLess(len(entier), 50_000)
        self.assertEqual(len(list(legi.parcourir_archive(io.BytesIO(entier)))), 1)

    def test_lire_jusqu_au_bout_fait_apparaitre_la_coupure(self):
        """Ouvrir l'archive et lire son premier membre ne suffit pas : un
        fichier tronqué s'ouvre très bien. C'est en la parcourant en entier que
        la coupure se voit — donc la lecture est le seul contrôle qui vaille."""
        entier = self._archive(80)
        coupe = io.BytesIO(entier[:len(entier) // 3])
        with self.assertRaises((tarfile.TarError, EOFError)):
            list(legi.parcourir_archive(coupe))

    def test_un_fichier_qui_n_est_pas_une_archive_est_refuse(self):
        with self.assertRaises((tarfile.TarError, EOFError)):
            list(legi.parcourir_archive(io.BytesIO(b"<html>404</html>")))


class CeQueLaLoiAjoute(unittest.TestCase):
    """Les articles qu'une loi écrit pour elle-même.

    On les ratait entièrement : 0 sur les 5 880 articles publiés pour les 72
    lois suivies, alors que la source les publie avec leur texte. La cause
    était une confusion de vocabulaire — voir `legi.AJOUTE`.
    """

    def test_un_article_dit_a_quelle_loi_il_appartient(self):
        xml = article(numero="12", contexte=loi("2026-796"))
        self.assertEqual(legi.loi_qui_porte(xml), "2026-796")

    def test_un_article_de_code_n_appartient_a_aucune_loi(self):
        self.assertIsNone(legi.loi_qui_porte(article()))

    def test_un_decret_n_est_pas_une_loi_meme_avec_le_meme_numero(self):
        """« Décret n°2005-850 » a la forme d'un numéro de loi. Se fier au seul
        numéro attribuerait ses articles à une loi qui n'existe pas."""
        xml = article(contexte=loi("2005-850", "Décret n°2005-850 du 27 juillet 2005",
                                   nature="DECRET"))
        self.assertIsNone(legi.loi_qui_porte(xml))

    def test_une_loi_organique_en_est_une(self):
        """Sa nature est `LOI_ORGANIQUE`. Le projet en suit une (loi 2024-1177)."""
        xml = article(contexte=loi("2024-1177", nature="LOI_ORGANIQUE"))
        self.assertEqual(legi.loi_qui_porte(xml), "2024-1177")

    def test_un_article_de_fond_est_un_ajout(self):
        xml = article(numero="12", contexte=loi(), type_article="AUTONOME")
        self.assertTrue(legi.est_un_ajout(xml, None))

    def test_un_article_mixte_aussi(self):
        xml = article(numero="12", contexte=loi(), type_article="PARTIELLEMENT_MODIF")
        self.assertTrue(legi.est_un_ajout(xml, None))

    def test_un_article_qui_n_amende_que_d_autres_textes_n_en_est_pas_un(self):
        """Rien à lire : sa substance est déjà à l'écran, sous forme des articles
        de code modifiés. 36 % des articles de loi sont dans ce cas."""
        xml = article(numero="1", contexte=loi(), type_article="ENTIEREMENT_MODIF",
                      texte=RENVOI)
        self.assertFalse(legi.est_un_ajout(xml, None))

    def test_un_renvoi_ne_se_reconnait_pas_au_debut_de_sa_phrase(self):
        """L'erreur trouvée le 2026-09-03 en vérifiant sur les vraies données.

        « I. A modifié les dispositions suivantes » ne commence pas par le
        verbe : une règle ancrée au début de la chaîne laissait passer
        8 articles sur 87, qui n'affichaient qu'une liste de références —
        article 82 de la loi 2025-127, article 44 de la loi 2026-725.
        """
        xml = article(numero="82", contexte=loi("2025-127"),
                      type_article="PARTIELLEMENT_MODIF",
                      texte="<p><br/>I. A modifié les dispositions suivantes :</p>"
                            "<blockquote>- Code de l'environnement<blockquote>"
                            " Art. L213-10-1, Art. L213-10-2</blockquote></blockquote>")
        self.assertFalse(legi.est_un_ajout(xml, None))

    def test_la_seule_phrase_de_droit_au_milieu_des_renvois_est_gardee(self):
        """Le III de l'article 8 de la loi 2026-796 : trois renvois, et une
        vraie disposition. La perdre serait pire que d'afficher les renvois."""
        xml = article(numero="8", contexte=loi("2026-796"),
                      type_article="PARTIELLEMENT_MODIF",
                      texte="<p>I. - A modifié les dispositions suivantes :</p>"
                            "<blockquote>- Code rural<blockquote> Art. L230-5-1"
                            "</blockquote></blockquote>"
                            "<p>III. - Le II bis s'applique aux contrats en cours.</p>"
                            "<p>IV. - A modifié les dispositions suivantes :</p>"
                            "<blockquote>- Code rural<blockquote> Art. L1"
                            "</blockquote></blockquote>")
        self.assertTrue(legi.est_un_ajout(xml, None))
        self.assertEqual(legi.lire_article(xml)["texte"],
                         "III. - Le II bis s'applique aux contrats en cours.")

    def test_un_type_qui_se_trompe_ne_fait_pas_perdre_du_droit(self):
        """L'article 32 de la loi 2026-201 est annoncé `ENTIEREMENT_MODIF`, et
        92 % de son contenu est une servitude au profit des jeux Olympiques
        d'hiver. Le `TYPE` de la source se trompe : le texte, non."""
        xml = article(numero="32", contexte=loi("2026-201"),
                      type_article="ENTIEREMENT_MODIF",
                      texte="<p>I. - A modifié les dispositions suivantes :</p>"
                            "<blockquote>- Code du tourisme<blockquote> Art. L342-20"
                            "</blockquote></blockquote>"
                            "<p>II. - La servitude peut être instituée au profit "
                            "du maître d'ouvrage.</p>")
        self.assertTrue(legi.est_un_ajout(xml, None))

    def test_un_article_de_renvoi_pas_encore_saisi_ne_s_annonce_pas(self):
        """Le seul cas où le `TYPE` sait plus que le texte : on connaît d'avance
        le résultat. L'annoncer aujourd'hui pour le voir disparaître demain ne
        rendrait service à personne."""
        xml = article(contexte=loi(), type_article="ENTIEREMENT_MODIF",
                      texte="<p>en cours de traitement</p>")
        self.assertFalse(legi.est_un_ajout(xml, None))

    def test_un_article_de_fond_pas_encore_saisi_s_annonce_quand_meme(self):
        """Lui aura un texte : le taire ferait disparaître un article qui
        existe. 69 des 138 articles de la loi 2026-798 étaient dans ce cas."""
        xml = article(contexte=loi(), type_article="AUTONOME",
                      texte="<p>en cours de traitement</p>")
        self.assertTrue(legi.est_un_ajout(xml, None))

    def test_une_redaction_ulterieure_n_est_pas_un_ajout(self):
        """**Le garde-fou qui compte.** Toutes les rédactions d'un article
        nomment le même porteur. Sans lui, l'article 156 de la loi de finances
        pour 2024 *tel que la loi de fin de gestion l'a modifié* passerait pour
        un article que la loi de finances a écrit — alors qu'elle ne l'a même
        pas produit."""
        xml = article(numero="156", contexte=loi("2023-1322"), type_article="AUTONOME")
        self.assertFalse(legi.est_un_ajout(xml, "LEGIARTI000000000009"))

    def test_un_type_inconnu_n_empeche_pas_de_montrer_un_texte(self):
        """La source peut inventer un `TYPE`, ou n'en mettre aucun. Ce n'est pas
        une raison pour taire un article qui a du texte."""
        for type_article in ("AUTRE_CHOSE", ""):
            with self.subTest(type_article=type_article):
                xml = article(contexte=loi(), type_article=type_article)
                self.assertTrue(legi.est_un_ajout(xml, None))

    def test_lire_article_rend_la_loi_porteuse_et_le_verdict(self):
        xml = article(numero="12", contexte=loi("2026-796"), type_article="AUTONOME")
        lu = legi.lire_article(xml)
        self.assertEqual(lu["loi_porteuse"], "2026-796")
        self.assertTrue(lu["ajout"])

    def test_un_texte_pas_encore_saisi_se_reconnait(self):
        """69 des 138 articles de la loi 2026-798, promulguée la veille."""
        self.assertTrue(legi.est_en_attente("en cours de traitement"))
        self.assertTrue(legi.est_en_attente("  En cours de traitement  "))
        self.assertFalse(legi.est_en_attente("I. - Le produit des impositions"))
        self.assertFalse(legi.est_en_attente(None))
        self.assertFalse(legi.est_en_attente(""))

    def test_un_ajout_n_a_rien_a_comparer(self):
        """Il n'a pas d'avant : l'écran doit dire « texte nouveau », pas
        « rédaction précédente non retrouvée »."""
        self.assertEqual(legi.etat_du_precedent(None, None), "aucun")

    def test_la_date_d_effet_d_un_ajout_est_son_debut(self):
        self.assertEqual(legi.date_d_effet(legi.AJOUTE, "2026-08-20", legi.SANS_FIN),
                         "2026-08-20")

    def test_un_article_sans_numero_se_nomme_par_son_debut(self):
        """Les états et annexes des lois de finances n'ont pas de numéro dans la
        source. Six sur 5 091 rédactions, et ce ne sont pas des cas perdus :
        l'état A de la loi de fin de gestion 2024 est le tableau des recettes.
        « Article » suivi de rien ne dit rien."""
        debut = ("ÉTATS LÉGISLATIFS ANNEXÉS ÉTAT A (ARTICLE 3 DE LA LOI) "
                 "VOIES ET MOYENS POUR 2024 RÉVISÉS I. - BUDGET GÉNÉRAL")
        self.assertEqual(
            legi.intitule_de_secours(debut),
            "ÉTATS LÉGISLATIFS ANNEXÉS ÉTAT A (ARTICLE 3 DE LA LOI) VOIES…")

    def test_un_intitule_de_secours_coupe_a_un_mot_entier(self):
        self.assertEqual(legi.intitule_de_secours("un deux trois quatre", 12),
                         "un deux…")

    def test_un_texte_court_n_est_pas_coupe(self):
        self.assertEqual(legi.intitule_de_secours("Court.", 62), "Court.")
        self.assertEqual(legi.intitule_de_secours(""), "")

    def test_un_seul_mot_trop_long_est_coupe_quand_meme(self):
        """Sans ce cas, `rsplit` rend la chaîne vide et l'article perd son nom."""
        self.assertEqual(legi.intitule_de_secours("abcdefghij", 5), "abcde…")

    def test_ajoute_n_est_pas_un_type_de_lien_de_la_source(self):
        """C'est notre mot. Le confondre avec le vocabulaire de LEGI ferait
        chercher dans les liens un renseignement qui n'y est pas."""
        self.assertNotIn(legi.AJOUTE, legi.CHANGEMENTS)


class L_AdresseDeLaSource(unittest.TestCase):

    def test_elle_pointe_la_redaction_precise(self):
        self.assertEqual(
            legi.url_legifrance("LEGIARTI000054724643"),
            "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000054724643")


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
