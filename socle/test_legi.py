#!/usr/bin/env python3
"""Vérifie les règles de lecture du droit consolidé — celles qui peuvent mentir.

Ces tests ne touchent ni au réseau ni à la base. Chaque cas reproduit en petit
un piège rencontré sur les vraies données, avec la référence de la mesure.

    ./test_legi.py
"""

import io
import pathlib
import sys
import tarfile
import unittest

import legi


def article(identifiant="LEGIARTI000000000001", numero="L401-1", debut="2026-09-01",
            fin=legi.SANS_FIN, etat="VIGUEUR", texte="<p>Le texte.</p>",
            contexte=None, versions=(), liens=(), nota="", type_article=""):
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
        f"<TYPE>{type_article}</TYPE>"
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

        **La mort-née vient avant la vraie dans la liste, et c'est le point du
        test.** Écrite dans l'autre ordre, la boucle rendait la vraie avant
        d'avoir vu la mort-née : le test passait avec ou sans la règle qu'il
        prétendait vérifier. Trouvé par mutation le 2026-09-03 — la règle était
        bonne, le décor du test ne la mettait jamais à l'épreuve.
        """
        toutes = [version("MORTE", "2222-02-22", "2026-08-26", "MODIFIE_MORT_NE"),
                  version("VRAIE", "2024-02-17", "2026-08-26"),
                  version("NOTRE", "2026-08-26", legi.SANS_FIN, "VIGUEUR")]
        self.assertEqual(legi.version_precedente(toutes, "2026-08-26"), "VRAIE")

    def test_une_mort_nee_seule_ne_tient_pas_lieu_de_avant(self):
        """S'il n'y a qu'elle, il n'y a pas d'avant — et l'écran doit dire
        « rédaction précédente non retrouvée », pas montrer une rédaction qui
        n'a jamais existé en droit."""
        toutes = [version("MORTE", "2222-02-22", "2026-08-26", "MODIFIE_MORT_NE"),
                  version("NOTRE", "2026-08-26", legi.SANS_FIN, "VIGUEUR")]
        self.assertIsNone(legi.version_precedente(toutes, "2026-08-26"))

    def test_l_ordre_de_la_liste_ne_compte_pas(self):
        """La liste `<VERSIONS>` n'est pas chronologique : constaté sur ce même
        article, où une rédaction de 2015 est écrite après une de 2016."""
        toutes = [version("PLUS_TARD", "2026-09-01", legi.SANS_FIN, "VIGUEUR"),
                  version("AVANT", "2019-09-02", "2026-09-01")]
        self.assertEqual(legi.version_precedente(toutes, "2026-09-01"), "AVANT")

    def test_un_article_cree_n_a_pas_de_avant(self):
        toutes = [version("NEUF", "2026-09-01", legi.SANS_FIN, "VIGUEUR")]
        self.assertIsNone(legi.version_precedente(toutes, "2026-09-01"))

    def test_un_article_n_est_pas_sa_propre_redaction_d_avant(self):
        """Le piège de la date sentinelle, trouvé le 2026-09-03.

        Un article dont l'entrée en vigueur n'est pas fixée porte `2999-01-01`
        en début **et** en fin, et la liste des versions le contient lui-même.
        « Celle qui finit quand la nôtre commence » le désignait donc lui.
        61 des 130 articles des lois d'août 2026 étaient dans ce cas.
        """
        toutes = [version("MOI", legi.SANS_FIN, legi.SANS_FIN, ""),
                  version("JORF", legi.SANS_FIN, legi.SANS_FIN, "")]
        self.assertIsNone(legi.version_precedente(toutes, legi.SANS_FIN, "MOI"))

    def test_un_article_ne_se_designe_pas_meme_avec_une_vraie_date(self):
        """Le refus de la sentinelle ne suffit pas à couvrir le cas.

        Une rédaction peut commencer et finir le même jour — en vigueur zéro
        jour. Elle figure alors dans sa propre liste avec `fin == debut`, sans
        que la sentinelle entre en jeu. Trouvé par mutation le 2026-09-03 :
        les deux tests écrits pour ce garde-fou passaient tous les deux par le
        refus de la sentinelle, et le garde-fou lui-même n'était pas testé.
        """
        toutes = [version("MOI", "2026-03-01", "2026-03-01", "MODIFIE"),
                  version("AVANT", "2020-01-01", "2026-03-01", "MODIFIE")]
        self.assertEqual(legi.version_precedente(toutes, "2026-03-01", "MOI"),
                         "AVANT")

    def test_sans_autre_candidate_il_n_y_a_pas_d_avant(self):
        """Même cas, mais seule : ne rien rendre plutôt que soi-même."""
        toutes = [version("MOI", "2026-03-01", "2026-03-01", "MODIFIE")]
        self.assertIsNone(legi.version_precedente(toutes, "2026-03-01", "MOI"))

    def test_la_sentinelle_de_fin_n_est_pas_une_frontiere(self):
        """Une rédaction qui n'a pas commencé n'a pas d'avant, même si une autre
        rédaction « finit » à la sentinelle — c'est-à-dire ne finit pas."""
        toutes = [version("EN_VIGUEUR", "2020-01-01", legi.SANS_FIN, "VIGUEUR"),
                  version("MOI", legi.SANS_FIN, legi.SANS_FIN, "")]
        self.assertIsNone(legi.version_precedente(toutes, legi.SANS_FIN, "MOI"))

    def test_le_garde_fou_ne_gene_pas_le_cas_normal(self):
        """Une vraie date, un vrai avant : `soi` ne doit rien changer."""
        toutes = [version("AVANT", "2019-09-02", "2026-09-01"),
                  version("MOI", "2026-09-01", legi.SANS_FIN, "VIGUEUR")]
        self.assertEqual(legi.version_precedente(toutes, "2026-09-01", "MOI"), "AVANT")

    def test_lire_article_passe_son_propre_identifiant(self):
        """La correction ne vaut que si `lire_article` s'en sert."""
        xml = article(identifiant="MOI", debut=legi.SANS_FIN, fin=legi.SANS_FIN,
                      etat="", versions=[version("MOI", legi.SANS_FIN,
                                                 legi.SANS_FIN, "")])
        self.assertIsNone(legi.lire_article(xml)["precedent"])

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
                         [{"role": "egal", "texte": "les articles 222-33 et 223-14",
                           "forme": False, "colle": False}])

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


class CeQuiN_EstQueDeLaForme(unittest.TestCase):
    """Une virgule déplacée n'est pas un changement du droit."""

    def test_une_ponctuation_seule_est_de_la_forme(self):
        for signe in (",", ".", ";", "-", "—", "«", "…", " ", " "):
            self.assertTrue(legi.est_de_forme(signe), signe)

    def test_un_seul_caractere_porteur_de_sens_suffit_a_compter(self):
        self.assertFalse(legi.est_de_forme("222-33"))
        self.assertFalse(legi.est_de_forme("a"))
        self.assertFalse(legi.est_de_forme(", et"))

    def test_un_morceau_vide_n_est_pas_un_changement_de_forme(self):
        self.assertFalse(legi.est_de_forme(""))

    def test_une_espace_ajoutee_dans_une_reference_ne_change_rien(self):
        """Le cas réel : Légifrance renormalise « 222-33,222-33-2 » en
        « 222-33, 222-33-2 ». La comparaison étant mot à mot, c'est un seul
        remplacement d'un mot par deux, et le morceau contient des chiffres —
        le juger morceau par morceau le manquerait."""
        self.assertTrue(legi.remplacement_de_forme("222-33,222-33-2",
                                                   "222-33, 222-33-2"))

    def test_un_ajout_de_fond_dans_la_meme_operation_compte(self):
        self.assertFalse(legi.remplacement_de_forme("222-33,222-33-2",
                                                    "222-33, 222-33-2 et 223-14"))

    def test_le_tiret_compte_comme_ponctuation(self):
        self.assertTrue(legi.remplacement_de_forme("sous-traitant", "sous traitant"))

    def test_une_espace_ajoutee_se_montre_une_seule_fois(self):
        """Afficher « ~~I-Sont~~ I- Sont » oblige à lire le mot deux fois pour
        trouver une espace. On descend au caractère : « I- », l'espace ajoutée,
        « Sont »."""
        m = legi.morceaux("I-Sont applicables", "I- Sont applicables")
        self.assertEqual([(x["role"], x["texte"]) for x in m[:3]],
                         [("egal", "I-"), ("ajoute", " "), ("egal", "Sont")])
        self.assertTrue(m[1]["forme"])

    def test_un_tiret_retire_se_montre_une_seule_fois(self):
        """« 222-33 » devenu « 22233 » : « 222 », le tiret retiré, « 33 »."""
        m = legi.morceaux("les 222-33 du code", "les 22233 du code")
        self.assertEqual([(x["role"], x["texte"]) for x in m[1:4]],
                         [("egal", "222"), ("retire", "-"), ("egal", "33")])

    def test_les_morceaux_au_caractere_se_collent_au_precedent(self):
        """Sans quoi l'affichage insérerait une espace au milieu du mot."""
        m = legi.morceaux("I-Sont applicables", "I- Sont applicables")
        self.assertFalse(m[0]["colle"])
        self.assertTrue(all(x["colle"] for x in m[1:3]))

    def test_le_mot_reste_lisible_une_fois_recompose(self):
        """Le texte affiché doit être exactement celui en vigueur."""
        m = legi.morceaux("I-Sont applicables", "I- Sont applicables")
        rendu = ""
        for x in m:
            if x["role"] == "retire":
                continue
            rendu += ("" if x["colle"] or not rendu else " ") + x["texte"]
        self.assertEqual(rendu, "I- Sont applicables")

    def test_un_vrai_changement_reste_mot_a_mot(self):
        """On ne descend au caractère que pour la forme : « trois » devenu
        « cinq » se lit comme un mot remplacé, pas comme cinq lettres."""
        m = legi.morceaux("la durée de trois ans", "la durée de cinq ans")
        change = [x for x in m if x["role"] != "egal"]
        self.assertEqual([(x["role"], x["texte"]) for x in change],
                         [("retire", "trois"), ("ajoute", "cinq")])

    def test_un_article_dont_tout_est_de_forme_n_a_pas_change_au_fond(self):
        m = legi.morceaux("les articles 222-33,222-33-2 du code",
                          "les articles 222-33, 222-33-2 du code")
        self.assertFalse(legi.changement_de_fond(m))
        self.assertTrue(all(x["forme"] for x in m if x["role"] != "egal"))

    def test_un_vrai_changement_reste_un_vrai_changement(self):
        m = legi.morceaux("pour une durée de trois ans", "pour une durée de cinq ans")
        self.assertTrue(legi.changement_de_fond(m))

    def test_les_morceaux_identiques_ne_sont_jamais_marques_de_forme(self):
        """Sinon un texte inchangé passerait tout entier en bleu."""
        m = legi.morceaux("le maire décide", "le maire décide seul")
        self.assertFalse(any(x["forme"] for x in m if x["role"] == "egal"))

    def test_le_texte_reste_complet_meme_quand_il_est_de_forme(self):
        """On ne retire rien du texte affiché : la ponctuation fait partie de
        la loi. On la rend seulement discrète.

        La recomposition suit `colle`, comme l'affichage : un morceau collé se
        rattache au précédent sans espace, sinon on couperait les mots.
        """
        m = legi.morceaux("le maire décide", "le maire, décide")
        rendu = ""
        for x in m:
            if x["role"] == "retire":
                continue
            rendu += ("" if x["colle"] or not rendu else " ") + x["texte"]
        self.assertEqual(rendu, "le maire, décide")


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


# Un renvoi tel que Légifrance l'écrit : une annonce, puis la liste des
# articles visés dans un `<blockquote>` imbriqué.
RENVOI = ("<p>A modifié les dispositions suivantes :</p>"
          "<blockquote>- Code rural et de la pêche maritime<blockquote>"
          " Art. L230-5-1, Art. L230-5-6</blockquote></blockquote>")


def loi(numero="2026-796", titre=None, nature="LOI", debut="2026-08-20"):
    """Le `CONTEXTE` d'un article porté par une loi, et non par un code."""
    titre = titre or f"LOI n°{numero} du 18 août 2026"
    return (f'<TEXTE nature="{nature}" num="{numero}" nor="AGRS2603566L" '
            f'cid="JORFTEXT000054707007"><TITRE_TXT c_titre_court="{titre}" '
            f'debut="{debut}" fin="{legi.SANS_FIN}">{titre}</TITRE_TXT></TEXTE>')


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
