"""Ce qu'une loi change à un article : la rédaction d'avant, la comparaison, la date d'effet, et ce qui n'est que de la forme.

    ./test_legi_versions.py
"""
from __future__ import annotations

import sys
import unittest
import legi
from decor_legi import article, version, LIEN


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

    LIEN = LIEN

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


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
