#!/usr/bin/env python3
"""Vérifie les règles de lecture du droit consolidé — celles qui peuvent mentir.

Ces tests ne touchent ni au réseau ni à la base. Chaque cas reproduit en petit
un piège rencontré sur les vraies données, avec la référence de la mesure.

    ./test_legi.py
"""

import io
import sys
import tarfile
import unittest

import legi


def article(identifiant="LEGIARTI000000000001", numero="L401-1", debut="2026-09-01",
            fin=legi.SANS_FIN, etat="VIGUEUR", texte="<p>Le texte.</p>",
            contexte=None, versions=(), liens=(), nota=""):
    """Un fichier d'article LEGI, réduit à ce que le module lit."""
    if contexte is None:
        contexte = ('<TEXTE nature="CODE"><TITRE_TXT c_titre_court="Code de l\'éducation" '
                    f'debut="2000-01-01" fin="{legi.SANS_FIN}">Code de l\'éducation'
                    "</TITRE_TXT></TEXTE>")
    lignes_versions = "".join(
        f'<VERSION etat="{v["etat"]}"><LIEN_ART debut="{v["debut"]}" '
        f'etat="{v["etat"]}" fin="{v["fin"]}" id="{v["id"]}" num="{numero}"/></VERSION>'
        for v in versions)
    return (
        "<?xml version='1.0' encoding='UTF-8'?><ARTICLE>"
        f"<META><META_COMMUN><ID>{identifiant}</ID></META_COMMUN><META_SPEC>"
        f"<META_ARTICLE><NUM>{numero}</NUM><ETAT>{etat}</ETAT>"
        f"<DATE_DEBUT>{debut}</DATE_DEBUT><DATE_FIN>{fin}</DATE_FIN>"
        "</META_ARTICLE></META_SPEC></META>"
        f"<CONTEXTE>{contexte}</CONTEXTE>"
        f"<VERSIONS>{lignes_versions}</VERSIONS>"
        f"<NOTA><CONTENU>{nota}</CONTENU></NOTA>"
        f"<BLOC_TEXTUEL><CONTENU>{texte}</CONTENU></BLOC_TEXTUEL>"
        f"<LIENS>{''.join(liens)}</LIENS></ARTICLE>")


def version(identifiant, debut, fin, etat="MODIFIE"):
    return {"id": identifiant, "debut": debut, "fin": fin, "etat": etat}


class LaVersionPrecedente(unittest.TestCase):
    """La règle centrale du module : quelle rédaction est « celle d'avant » ?"""

    def test_c_est_celle_qui_se_termine_quand_la_notre_commence(self):
        toutes = [version("A", "2019-09-02", "2026-09-01"),
                  version("B", "2026-09-01", legi.SANS_FIN, "VIGUEUR")]
        self.assertEqual(legi.version_precedente(toutes, "2026-09-01"), "A")

    def test_une_redaction_mort_nee_n_est_jamais_le_avant(self):
        """Le piège qui donnait un avant/après faux et spectaculaire.

        Sur l'article 6 de la loi n° 2004-575, la rédaction qui précède dans la
        liste est datée du 22 février 2222 et marquée `MODIFIE_MORT_NE` : elle
        a été votée mais n'est jamais entrée en vigueur. La retenir faisait
        tomber la part de texte commun à 13 % ; l'écarter la remonte à 97 %
        (mesuré le 2026-09-01).
        """
        toutes = [version("VRAIE", "2024-02-17", "2026-08-26"),
                  version("MORTE", "2222-02-22", "2026-08-26", "MODIFIE_MORT_NE"),
                  version("NOTRE", "2026-08-26", legi.SANS_FIN, "VIGUEUR")]
        self.assertEqual(legi.version_precedente(toutes, "2026-08-26"), "VRAIE")

    def test_l_ordre_de_la_liste_ne_compte_pas(self):
        """La liste `<VERSIONS>` n'est pas chronologique : constaté sur ce même
        article, où une rédaction de 2015 est écrite après une de 2016."""
        toutes = [version("PLUS_TARD", "2026-09-01", legi.SANS_FIN, "VIGUEUR"),
                  version("AVANT", "2019-09-02", "2026-09-01")]
        self.assertEqual(legi.version_precedente(toutes, "2026-09-01"), "AVANT")

    def test_un_article_cree_n_a_pas_de_avant(self):
        toutes = [version("NEUF", "2026-09-01", legi.SANS_FIN, "VIGUEUR")]
        self.assertIsNone(legi.version_precedente(toutes, "2026-09-01"))

    def test_les_deux_familles_de_mort_nes_sont_ecartees(self):
        self.assertTrue(legi.est_mort_ne("MODIFIE_MORT_NE"))
        self.assertTrue(legi.est_mort_ne("ABROGE_MORT_NE"))
        self.assertFalse(legi.est_mort_ne("MODIFIE"))
        self.assertFalse(legi.est_mort_ne("VIGUEUR"))


class CeQueLaLoiFait(unittest.TestCase):
    """Quatre actions se superposent différemment ; une cinquième ne compte pas."""

    LIEN = ('<LIEN cidtexte="JORFTEXT000054707332" num="14" numtexte="2026-798" '
            'sens="cible" typelien="{}">LOI n°2026-798 - art. 14</LIEN>')

    def test_une_citation_n_est_pas_un_changement(self):
        """5 520 citations pour 2 711 modifications : les compter ferait dire
        n'importe quoi à l'application (mesuré le 2026-09-01)."""
        self.assertEqual(legi.changements(article(liens=[self.LIEN.format("CITATION")])), [])

    def test_les_quatre_actions_sont_retenues(self):
        for quoi in ("MODIFIE", "CREE", "ABROGE", "TRANSFERE"):
            trouve = legi.changements(article(liens=[self.LIEN.format(quoi)]))
            self.assertEqual(trouve, [{"loi": "2026-798", "quoi": quoi, "article_loi": "14"}])

    def test_un_lien_source_dit_l_inverse_et_ne_compte_pas(self):
        """`sens="source"` veut dire « c'est moi qui cite l'autre »."""
        lien = ('<LIEN num="14" numtexte="2026-798" sens="source" '
                'typelien="MODIFIE">…</LIEN>')
        self.assertEqual(legi.changements(article(liens=[lien])), [])

    def test_l_ordre_des_attributs_ne_compte_pas(self):
        """Une expression régulière qui exige `typelien` avant `numtexte` ne
        trouve rien alors que le lien est là : l'ordre varie d'un fichier à
        l'autre."""
        lien = ('<LIEN typelien="MODIFIE" sens="cible" numtexte="2026-813" '
                'num="3">…</LIEN>')
        self.assertEqual(legi.changements(article(liens=[lien]))[0]["loi"], "2026-813")


class OuSeTrouveL_Article(unittest.TestCase):

    def test_l_intitule_valable_a_la_date_est_retenu(self):
        """Le fichier propose plusieurs intitulés, dont un daté de la sentinelle
        2999-01-01 qui n'est pas le bon."""
        contexte = ('<TEXTE><TITRE_TXT c_titre_court="Placeholder" debut="2999-01-01" '
                    'fin="2999-01-01">…</TITRE_TXT>'
                    '<TITRE_TXT c_titre_court="Loi n° 2004-575 du 21 juin 2004" '
                    'debut="2004-06-22" fin="2999-01-01">…</TITRE_TXT></TEXTE>')
        self.assertEqual(legi.ou_se_trouve(article(contexte=contexte), "2026-08-26"),
                         "Loi n° 2004-575 du 21 juin 2004")

    def test_sans_intitule_valable_on_prend_le_dernier(self):
        contexte = ('<TEXTE><TITRE_TXT c_titre_court="Ancien nom" debut="1990-01-01" '
                    'fin="1995-01-01">…</TITRE_TXT></TEXTE>')
        self.assertEqual(legi.ou_se_trouve(article(contexte=contexte), "2026-01-01"),
                         "Ancien nom")

    def test_sans_contexte_l_article_n_est_nulle_part(self):
        self.assertEqual(legi.ou_se_trouve(article(contexte=""), "2026-01-01"), "")


class ComparerDeuxRedactions(unittest.TestCase):

    def test_un_ajout_apparait_comme_ajoute(self):
        m = legi.morceaux("Le maire décide", "Le maire décide seul")
        self.assertEqual([x["role"] for x in m], ["egal", "ajoute"])
        self.assertEqual(m[1]["texte"], "seul")

    def test_un_mot_ponctue_differemment_est_un_remplacement(self):
        """La comparaison est mot à mot : « décide. » et « décide » sont deux
        mots différents. C'est voulu — la ponctuation fait partie du texte de
        loi — mais il faut le savoir en lisant un résultat."""
        m = legi.morceaux("Le maire décide.", "Le maire décide seul.")
        self.assertEqual([x["role"] for x in m], ["egal", "retire", "ajoute"])

    def test_un_remplacement_donne_un_retrait_puis_un_ajout(self):
        m = legi.morceaux("la loi n° 2026-798", "la loi n° 2026-813")
        self.assertEqual([x["role"] for x in m], ["egal", "retire", "ajoute"])

    def test_la_typographie_ne_doit_pas_faire_de_bruit(self):
        """Légifrance renormalise les espaces : « 222-33,222-33-2 » devient
        « 222-33, 222-33-2 ». Sans normalisation, ce bruit masque la seule vraie
        modification (mesuré le 2026-08-31 sur l'article 131-35-1 du code pénal).
        """
        self.assertEqual(legi.morceaux("les articles  222-33\n et 223-14",
                                       "les articles 222-33 et 223-14"),
                         [{"role": "egal", "texte": "les articles 222-33 et 223-14"}])

    def test_l_espace_insecable_compte_comme_un_espace(self):
        self.assertEqual(legi.normaliser("article L401-1"), "article L401-1")

    def test_deux_textes_identiques_sont_communs_a_cent_pour_cent(self):
        self.assertEqual(legi.part_commune("Le texte.", "Le texte."), 100)

    def test_deux_textes_etrangers_n_ont_rien_de_commun(self):
        self.assertEqual(legi.part_commune("alpha beta", "gamma delta"), 0)

    def test_deux_textes_vides_sont_identiques_et_ne_divisent_pas_par_zero(self):
        self.assertEqual(legi.part_commune("", ""), 100)


class QuandLeChangementPrendEffet(unittest.TestCase):
    """Une abrogation ne met rien en vigueur : elle met fin à une rédaction."""

    def test_une_modification_prend_effet_au_debut_de_la_nouvelle_redaction(self):
        self.assertEqual(legi.date_d_effet("MODIFIE", "2026-09-01", legi.SANS_FIN),
                         "2026-09-01")

    def test_une_abrogation_prend_effet_a_la_fin_de_l_ancienne(self):
        """L'article 1700 du code général des impôts, abrogé par la loi de
        finances de 2025, s'affichait comme entrant en vigueur le 1er juillet
        1979 — la date à laquelle le texte abrogé avait commencé à
        s'appliquer (mesuré le 2026-09-02)."""
        self.assertEqual(legi.date_d_effet("ABROGE", "1979-07-01", "2025-01-01"),
                         "2025-01-01")

    def test_une_creation_prend_effet_a_son_debut(self):
        self.assertEqual(legi.date_d_effet("CREE", "2026-09-01", legi.SANS_FIN),
                         "2026-09-01")

    def test_sans_date_utilisable_on_ne_dit_rien(self):
        self.assertIsNone(legi.date_d_effet("MODIFIE", "", legi.SANS_FIN))
        self.assertIsNone(legi.date_d_effet("ABROGE", "1979-07-01", ""))

    def test_une_date_non_encore_fixee_n_est_pas_une_date(self):
        """La loi prévoit l'abrogation mais renvoie à un décret qui n'est pas
        paru : LEGI écrit alors le 22 février 2222. Afficher cette date serait
        absurde ; 73 changements sur 2 261 sont dans ce cas."""
        self.assertIsNone(legi.date_d_effet("ABROGE", "2011-06-01", legi.SANS_DATE))
        self.assertIsNone(legi.date_d_effet("MODIFIE", legi.SANS_DATE, legi.SANS_FIN))

    def test_la_sentinelle_de_fin_n_est_pas_une_date_d_abrogation(self):
        """2999-01-01 veut dire « toujours en vigueur », pas « abrogé en 2999 »."""
        self.assertIsNone(legi.date_d_effet("ABROGE", "2011-06-01", legi.SANS_FIN))


class PourquoiPasDeComparaison(unittest.TestCase):
    """Un trou dans nos données ne doit pas passer pour un fait sur la loi."""

    def test_la_redaction_d_avant_est_connue(self):
        self.assertEqual(legi.etat_du_precedent("LEGIARTI001", "Le texte d'avant."),
                         "connu")

    def test_un_article_cree_n_a_pas_de_avant(self):
        self.assertEqual(legi.etat_du_precedent(None, None), "aucun")

    def test_un_avant_designe_mais_introuvable_se_dit(self):
        """L'article avait bien une rédaction antérieure, et nous ne l'avons pas
        retrouvée dans les archives lues. L'afficher comme « texte nouveau »
        ferait mentir l'application."""
        self.assertEqual(legi.etat_du_precedent("LEGIARTI001", None), "manquant")

    def test_un_texte_d_avant_vide_compte_comme_absent(self):
        self.assertEqual(legi.etat_du_precedent("LEGIARTI001", ""), "manquant")


class LireUnFichierD_Article(unittest.TestCase):

    def test_tout_ce_qu_on_retient_est_lu(self):
        xml = article(
            texte="<p>Dans chaque école&nbsp;et établissement.</p>",
            versions=[version("AVANT", "2019-09-02", "2026-09-01"),
                      version("LEGIARTI000000000001", "2026-09-01", legi.SANS_FIN, "VIGUEUR")],
            liens=[CeQueLaLoiFait.LIEN.format("MODIFIE")])
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


class L_AdresseDeLaSource(unittest.TestCase):

    def test_elle_pointe_la_redaction_precise(self):
        self.assertEqual(
            legi.url_legifrance("LEGIARTI000054724643"),
            "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000054724643")


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
