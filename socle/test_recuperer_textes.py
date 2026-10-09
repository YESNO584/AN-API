#!/usr/bin/env python3
"""Vérifie la récupération du texte des lois : ce qui se lit, ce qui se garde,
ce qui se relit quand les règles de lecture changent.

Ni réseau, ni vraie base. Séparé de `test_textes.py` le 2026-10-09 : celui-là
vérifie les règles de lecture, celui-ci `recuperer_textes.py`.

    ./test_recuperer_textes.py
"""

import json
import pathlib
import sqlite3
import sys
import tempfile
import unittest
import unittest.mock

import recuperer_textes
from test_textes import alinea, document, garde, titre_article

# Le schéma se trouve à côté de ce fichier, pas dans le répertoire d'où on
# lance les tests : sans cela, `python3 socle/test_textes.py` depuis la racine
# échouait là où `python3 test_textes.py` depuis `socle/` passait.
SCHEMA = pathlib.Path(__file__).resolve().parent / "schema.sql"


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
        cx.executescript(SCHEMA.read_text(encoding="utf-8"))
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


class Relecture(unittest.TestCase):
    """Quand les règles de lecture changent, ce qui a été lu se relit — sans
    jamais effacer la lecture d'avant."""

    def base(self):
        return recuperer_textes.ouvrir(pathlib.Path(tempfile.mkdtemp()) / "textes.db")

    def vieillir(self, base, *uids):
        base.executemany("UPDATE document SET lecture = 'ancienne' WHERE uid = ?",
                         [(u,) for u in uids])

    def passe(self, base, attendus, source=None):
        appels = []
        def telecharger(uid):
            appels.append(uid)
            return (source, len(source)) if source is not None else (None, 0)
        with unittest.mock.patch.object(recuperer_textes, "telecharger", telecharger):
            recuperer_textes.passe(base, attendus, minutes=5, attente=0)
        return appels

    def test_ce_qui_manque_passe_avant_ce_qui_se_relit_le_plus_recent_d_abord(self):
        base = self.base()
        for uid in ("U1", "U2"):
            recuperer_textes.ranger(base, uid, document(titre_article("Article 1er")), 10)
        self.vieillir(base, "U1", "U2")
        self.assertEqual(self.passe(base, ["U1", "U2", "U3"], source=""),
                         ["U3", "U2", "U1"])

    def test_un_document_relu_porte_les_regles_d_aujourd_hui(self):
        base = self.base()
        recuperer_textes.ranger(base, "U1", document(titre_article("Article 1er")), 10)
        self.vieillir(base, "U1")
        self.passe(base, ["U1"], source=document(titre_article("Article 2"), alinea("Neuf.")))
        self.assertEqual(recuperer_textes.articles_du_document(base, "U1"), {"Article 2": "Neuf."})
        self.assertEqual(self.passe(base, ["U1"]), [], "relu une fois, il ne se relit plus")

    def test_une_relecture_qui_echoue_ne_remplace_rien(self):
        """La lecture d'avant vaut mieux qu'un document noté absent parce que
        le serveur a coupé la connexion ce matin-là."""
        base = self.base()
        recuperer_textes.ranger(base, "U1", document(titre_article("Article 1er"),
                                                     alinea("Gardé.")), 10)
        self.vieillir(base, "U1")
        self.passe(base, ["U1"], source=None)
        self.assertEqual(recuperer_textes.articles_du_document(base, "U1"),
                         {"Article 1er": "Gardé."})

    def test_une_base_d_avant_l_empreinte_s_ouvre_et_se_relit(self):
        """La base gardée en cache n'a pas la colonne : ses documents restent
        lisibles, et valent « lus par d'anciennes règles »."""
        chemin = pathlib.Path(tempfile.mkdtemp()) / "textes.db"
        cx = sqlite3.connect(chemin)
        cx.execute("CREATE TABLE document (uid TEXT PRIMARY KEY, lu_le TEXT NOT NULL,"
                   " statut TEXT NOT NULL, octets INTEGER NOT NULL DEFAULT 0, articles TEXT)")
        cx.execute("INSERT INTO document VALUES ('U1', '2026-09-18', 'lu', 10, ?)",
                   (json.dumps({"Article 1er": "Ancien."}),))
        cx.commit(); cx.close()
        base = recuperer_textes.ouvrir(chemin)
        self.assertEqual(recuperer_textes.articles_du_document(base, "U1"),
                         {"Article 1er": "Ancien."})
        self.assertEqual(recuperer_textes.a_relire(base), {"U1"})


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
