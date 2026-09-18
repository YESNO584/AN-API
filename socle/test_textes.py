#!/usr/bin/env python3
"""Vérifie les règles de lecture du texte des lois, version par version.

Ni réseau, ni base : ces tests portent sur les règles, et **chaque cas
reproduit en petit un défaut constaté sur les vraies données** le 2026-09-18.
Le détail des mesures est dans `../docs/sources/textes-assemblee-html.md`.

    ./test_textes.py
"""

import json
import pathlib
import sqlite3
import sys
import tempfile
import unittest
import unittest.mock

import recuperer_textes
import textes


def document(*paragraphes: str, note: str = "") -> str:
    """Un document tel que l'Assemblée le publie, réduit à l'essentiel."""
    corps = "".join(paragraphes)
    if note:
        corps += f'<p class="assnatEndnoteText">{note}</p>'
    return f"<html><head><style>.assnat9ArticleNum {{ }}</style></head><body>{corps}</body></html>"


def titre_article(texte: str) -> str:
    return f'<p class="assnat9ArticleNum">{texte}</p>'


def alinea(texte: str) -> str:
    return f'<p class="assnatLoiTexte">{texte}</p>'


def garde() -> str:
    return ("<p>N° 1794</p><p>ASSEMBLÉE NATIONALE</p>"
            "<p>PROPOSITION DE LOI</p><p>présentée par</p>"
            "<p>M. Stéphane HABLOT, M. Pierrick COURBON, députés.</p>")


def amendement(article, ou="A", numero="AS35", auteur="Stéphane Hablot",
               sigle="SOC", type_division="ARTICLE"):
    return {"numero": numero, "auteur": auteur, "sigle": sigle,
            "division": {"article": article, "ou": ou, "type": type_division}}


class Decoupage(unittest.TestCase):
    """Où commence un article, et ce qui n'en fait pas partie."""

    def test_la_classe_du_paragraphe_ouvre_un_article(self):
        d = document(titre_article("Article 1er"), alinea("Les hôpitaux publics."))
        self.assertEqual(textes.articles(d), {"Article 1er": "Les hôpitaux publics."})

    def test_la_page_de_garde_n_est_pas_du_texte_de_loi(self):
        d = document(garde(), titre_article("Article unique"), alinea("Un alinéa."))
        self.assertEqual(list(textes.articles(d)), ["Article unique"])

    def test_sans_classe_le_mot_article_suffit(self):
        """Les « petites lois » budgétaires suivent un autre gabarit Word."""
        d = document("<p>Article 1er</p><p>Le premier alinéa.</p>",
                     "<p>Article 2</p><p>Le second.</p>")
        self.assertEqual(textes.articles(d),
                         {"Article 1er": "Le premier alinéa.", "Article 2": "Le second."})

    def test_la_note_de_fin_ne_se_colle_pas_au_dernier_article(self):
        """Constaté : les 130 cosignataires ressortaient comme du texte retiré.

        Le document de dépôt se termine par « (1) Ce groupe est composé de :
        Mme … » — la composition du groupe de l'auteur. Collée au dernier
        article, elle le faisait passer pour massivement supprimé par la
        commission. La source marque ce paragraphe `assnatEndnoteText`.
        """
        d = document(titre_article("Article 4"), alinea("La perte de recettes est compensée."),
                     note="(1) Ce groupe est composé de : Mme Marie-José ALLEMAND, "
                          "M. Joël AVIRAGNET, M. Christian BAPTISTE.")
        self.assertEqual(textes.articles(d),
                         {"Article 4": "La perte de recettes est compensée."})

    def test_un_tableau_reste_dans_l_article(self):
        """Le HTML garde les tableaux, là où le PDF les aplatissait."""
        d = document(titre_article("Article 3"),
                     "<table><tr><td>Taux</td><td>12 %</td></tr></table>")
        self.assertIn("12 %", textes.articles(d)["Article 3"])

    def test_un_document_reduit_a_sa_page_de_garde_ne_rend_rien(self):
        """Deux documents sur 149 n'ont pas d'autre contenu — leur PDF non plus."""
        self.assertEqual(textes.articles(document(garde())), {})


class Numero(unittest.TestCase):
    """Deux versions ne s'apparient que par le numéro d'article."""

    def test_le_premier_article_s_ecrit_de_trois_façons(self):
        """« Article PREMIER » (amendements) = « Article 1er » (documents).

        Sans cette règle, 137 rapprochements sur 144 échouaient et le taux
        d'explication tombait de 47 % à 28 %.
        """
        for ecrit in ("Article 1er", "Article PREMIER", "Article premier", "Article 1 er"):
            self.assertEqual(textes.numero(ecrit), "1er", ecrit)

    def test_la_mention_n_est_pas_le_numero(self):
        self.assertEqual(textes.numero("Article 1er bis (nouveau)"), "1er bis")
        self.assertEqual(textes.numero("Article 5 (Supprimé)"), "5")

    def test_le_titre_affiche_recolle_l_exposant(self):
        """« Article 1 er » vient d'un « er » en exposant dans le document
        Word : le recoller restitue ce que la source imprime."""
        self.assertEqual(textes.titre_propre("Article 1 er bis (nouveau)"),
                         "Article 1er bis (nouveau)")

    def test_l_article_voisin_d_un_article_ne(self):
        self.assertEqual(textes.racine("1er bis"), "1er")
        self.assertEqual(textes.racine("3 bis a"), "3")
        self.assertEqual(textes.racine("2"), "2")


class Mentions(unittest.TestCase):
    """« (Non modifié) » dit un état, pas un texte."""

    def test_la_mention_du_titre_est_un_etat(self):
        self.assertEqual(textes.etat("Article 1er bis (nouveau)", "Du texte."), "nouveau")
        self.assertEqual(textes.etat("Article 5 (Supprimés)", ""), "supprimé")

    def test_la_mention_en_tete_d_article_aussi(self):
        self.assertEqual(textes.etat("Article 1er", "(Non modifié) Le texte."), "non modifié")

    def test_la_mention_sort_du_texte_compare(self):
        """Laissée dedans, elle s'affichait comme un ajout de la commission —
        alors qu'elle dit que l'article n'a pas bougé."""
        self.assertEqual(textes.sans_mention("(Non modifié) Le texte."), "Le texte.")

    def test_un_article_sans_mention_n_invente_rien(self):
        self.assertIsNone(textes.etat("Article 2", "Le texte."))


class Comparaison(unittest.TestCase):
    """Ce que la commission ou la séance a changé."""

    def setUp(self):
        self.avant = {"Article 1er": "Les hôpitaux publics assurent la gratuité.",
                      "Article 2": "Un rapport annuel est remis.",
                      "Article 3": "Le Gouvernement remet un rapport."}
        self.apres = {"Article 1er": "Les établissements publics de santé assurent la gratuité.",
                      "Article 1er bis (nouveau)": "Les proches aidants en bénéficient.",
                      "Article 2": "Un rapport annuel est remis."}

    def lignes(self):
        return {l["numero"]: l for l in textes.comparer(self.avant, self.apres)}

    def test_un_article_modifie_porte_ses_morceaux(self):
        l = self.lignes()["1er"]
        self.assertEqual(l["quoi"], "modifie")
        self.assertIn("établissements", " ".join(
            m["texte"] for m in l["morceaux"] if m["role"] == "ajoute"))
        self.assertIn("hôpitaux", " ".join(
            m["texte"] for m in l["morceaux"] if m["role"] == "retire"))

    def test_un_article_identique_ne_montre_aucun_changement(self):
        l = self.lignes()["2"]
        self.assertEqual(l["quoi"], "identique")
        self.assertEqual(l["morceaux"], [])

    def test_un_article_apparu_n_a_pas_d_avant(self):
        l = self.lignes()["1er bis"]
        self.assertEqual(l["quoi"], "nouveau")
        self.assertEqual(l["etat"], "nouveau")
        self.assertEqual(l["morceaux"], [])

    def test_un_article_disparu_est_un_changement(self):
        """Un article que la nouvelle version ne porte plus doit se voir."""
        l = self.lignes()["3"]
        self.assertEqual(l["quoi"], "retire")

    def test_le_resume_compte_ce_qui_a_bougé(self):
        r = textes.resume(textes.comparer(self.avant, self.apres))
        self.assertEqual((r["modifies"], r["nouveaux"], r["retires"], r["identiques"]),
                         (1, 1, 1, 1))

    def test_la_version_deposee_n_a_rien_a_comparer(self):
        """Ses articles ne sont pas des ajouts de la commission : ils sont le
        texte de départ."""
        lignes = textes.premiere_version({"Article 1er": "Le texte."})
        self.assertEqual(lignes[0]["quoi"], "initial")
        self.assertEqual(textes.resume(lignes)["initiaux"], 1)
        self.assertEqual(textes.resume(lignes)["nouveaux"], 0)

    def test_la_mention_non_modifie_ne_fait_pas_un_changement(self):
        """Constaté : « (Non modifié) » s'affichait comme un ajout."""
        lignes = textes.comparer({"Article 1er": "Le texte."},
                                 {"Article 1er": "(Non modifié) Le texte."})
        self.assertEqual(lignes[0]["quoi"], "identique")
        self.assertEqual(lignes[0]["etat"], "non modifié")


class Amendements(unittest.TestCase):
    """L'amendement adopté que la source relie à un article."""

    def setUp(self):
        self.index = textes.amendements_du_document([
            amendement("Article PREMIER", numero="AS31"),
            amendement("Article PREMIER", numero="AS35"),
            amendement("Article 2", numero="AS37"),
            amendement("Article PREMIER", ou="Après", numero="19"),
            amendement("Titre", type_division="TITRE", numero="AS99"),
        ])

    def ligne(self, numero, quoi="modifie"):
        return {"numero": numero, "quoi": quoi}

    def test_l_article_modifie_recoit_les_siens(self):
        trouves = textes.amendements_de_l_article(self.index, self.ligne("1er"))
        self.assertEqual([a["numero"] for a in trouves], ["AS31", "AS35"])

    def test_l_amendement_apres_l_article_a_cree_l_article_suivant(self):
        """Un article « bis » ne naît pas d'un amendement sur son voisin, mais
        d'un amendement déposé **après** lui : 2 823 amendements adoptés de la
        législature sont dans ce cas."""
        trouves = textes.amendements_de_l_article(self.index, self.ligne("1er bis", "nouveau"))
        self.assertEqual([a["numero"] for a in trouves], ["19"])

    def test_un_amendement_sur_le_titre_n_est_pas_un_amendement_d_article(self):
        self.assertNotIn(("titre", "A"), self.index)

    def test_un_article_sans_amendement_rend_une_liste_vide(self):
        """31 % des changements sont dans ce cas : l'écran doit le dire, pas
        le cacher."""
        self.assertEqual(textes.amendements_de_l_article(self.index, self.ligne("4")), [])


class Recuperation(unittest.TestCase):
    """Ce qui se lit, ce qui se garde, et ce qui s'arrête à l'heure."""

    def base(self):
        return recuperer_textes.ouvrir(pathlib.Path(tempfile.mkdtemp()) / "textes.db")

    def test_seuls_les_documents_qui_portent_le_texte_sont_lus(self):
        """Un rapport ou une étude d'impact ne sont pas des versions du texte,
        et le Sénat publie les siennes ailleurs — 30 demandées ici, 30 refus."""
        for ref in ("PIONANR5L17B1794", "PIONANR5L17BTC2362", "PRJLANR5L17BTA0314"):
            self.assertTrue(recuperer_textes.est_une_version(ref), ref)
        for ref in ("RAPPANR5L17B2362", "ETDIANR5L17B2155", "ACINANR5L17B2155",
                    "PIONSNR5S479B0323"):
            self.assertFalse(recuperer_textes.est_une_version(ref), ref)

    def test_les_versions_viennent_des_etapes_du_parcours(self):
        """Aucun appel réseau pour savoir quoi lire : l'archive déjà
        téléchargée nomme le document de chaque étape."""
        chemin = pathlib.Path(tempfile.mkdtemp()) / "parlement.db"
        cx = sqlite3.connect(chemin)
        cx.executescript(pathlib.Path("schema.sql").read_text(encoding="utf-8"))
        cx.execute("INSERT INTO dossier (uid, legislature, titre, type, est_loi, statut)"
                   " VALUES ('D1', '17', 'Un texte', 'Proposition de loi ordinaire', 1, 'en_cours')")
        cx.execute("INSERT INTO dossier (uid, legislature, titre, type, est_loi, statut)"
                   " VALUES ('D2', '17', 'Un rapport', 'Rapport', 0, 'en_cours')")
        for uid, rang, details in (
                ("D1", 0, {"texteAssocie": {"ref": "PIONANR5L17B1794"}}),
                ("D1", 1, {"texteAssocie": {"ref": "RAPPANR5L17B2362"},
                           "texteAdopte": {"ref": "PIONANR5L17BTC2362"}}),
                ("D2", 0, {"texteAssocie": {"ref": "PIONANR5L17B9999"}})):
            cx.execute("INSERT INTO etape (dossier_uid, code, date, rang, numero,"
                       " future, details) VALUES (?, 'AN1-DEPOT', '2025-09-16', ?, ?, 0, ?)",
                       (uid, rang, rang, json.dumps(details)))
        cx.commit(); cx.close()
        self.assertEqual(recuperer_textes.versions_attendues(chemin),
                         ["PIONANR5L17B1794", "PIONANR5L17BTC2362"])

    def test_un_document_lu_garde_ses_articles_et_pas_le_html(self):
        base = self.base()
        source = document(titre_article("Article 1er"), alinea("Les hôpitaux publics."))
        self.assertEqual(recuperer_textes.ranger(base, "U1", source, len(source)), "lu")
        self.assertEqual(recuperer_textes.articles_du_document(base, "U1"),
                         {"Article 1er": "Les hôpitaux publics."})

    def test_un_document_sans_article_est_range_comme_tel(self):
        """Ce n'est pas un échec de lecture : c'est le plus souvent la « petite
        loi » d'un texte que l'Assemblée n'a pas adopté."""
        base = self.base()
        self.assertEqual(recuperer_textes.ranger(base, "U2", document(garde()), 100),
                         "sans_article")
        self.assertEqual(recuperer_textes.articles_du_document(base, "U2"), {})

    def test_un_document_introuvable_est_note_absent(self):
        base = self.base()
        self.assertEqual(recuperer_textes.ranger(base, "U3", None, 0), "absent")

    def test_ce_qui_est_lu_ne_se_relit_jamais(self):
        """Un texte publié ne change plus : la passe du lendemain reprend où
        celle de la veille s'est arrêtée."""
        base = self.base()
        recuperer_textes.ranger(base, "U1", document(titre_article("Article 1er")), 10)
        appels = []
        with unittest.mock.patch.object(recuperer_textes, "telecharger",
                                        lambda uid: (appels.append(uid), ("", 0))[1]):
            lus, restants = recuperer_textes.passe(base, ["U1", "U2"], minutes=5, attente=0)
        self.assertEqual(appels, ["U2"])
        self.assertEqual((lus, restants), (1, 0))

    def test_la_passe_s_arrete_dans_son_budget_de_temps(self):
        """50 minutes de lecture ajoutées d'un coup à une publication qui en
        dure trois la rendraient fragile. Elle s'arrête, et reprend demain."""
        base = self.base()
        with unittest.mock.patch.object(recuperer_textes, "telecharger",
                                        lambda uid: ("", 0)):
            lus, restants = recuperer_textes.passe(base, ["U1", "U2", "U3"],
                                                   minutes=0, attente=0)
        self.assertEqual((lus, restants), (0, 3))


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
