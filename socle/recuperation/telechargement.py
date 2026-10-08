"""Les archives de l'Assemblée : lesquelles, lesquelles peuvent manquer, et comment les demander en insistant et sans retélécharger ce qui n'a pas changé.
"""
from __future__ import annotations

import hashlib
import pathlib
import sqlite3
import sys
import time
import extraction


# Les trois jeux dont le socle a besoin. Les groupes politiques ne sont pas un
# supplément : les scrutins ne nomment pas les groupes, ils y renvoient par un
# identifiant. Sans cette table, « PO845401 a voté contre » n'apprend rien.
SOURCES = {
    "dossiers": extraction.URL_ARCHIVE,
    "scrutins": extraction.URL_SCRUTINS,
    "groupes": extraction.URL_ORGANES,
    "senat": extraction.URL_SENAT,
    "amendements": extraction.URL_AMENDEMENTS,
    # L'agenda ne sert qu'à départager deux actes du même jour, mais sans lui
    # 296 groupes d'actes s'affichent à l'identique. Voir precision_acte.
    "agenda": extraction.URL_AGENDA,
    # Sans elle, 716 textes ont un auteur sans nom : un ministre ou un
    # sénateur n'est pas un député en exercice. Voir URL_ACTEURS_LARGE.
    "acteurs": extraction.URL_ACTEURS_LARGE,
    # Les comptes rendus de séance : la seule source où un député explique un
    # texte avec ses propres phrases. Voir URL_DEBATS.
    "debats": extraction.URL_DEBATS,
}


# Les amendements pèsent 297 Mo à eux seuls, contre 45 Mo pour les cinq autres
# sources réunies. Ce sont eux qui cassent : trois publications d'affilée ont
# échoué dessus le 2026-08-31, le transfert coupé à 2,6 Mo, 51,7 Mo puis
# 3,2 Mo. Les rendre bloquants revenait à figer tout le site — le parcours des
# textes, les votes, les lois promulguées — pour une rubrique secondaire.
#
# Ils sont donc facultatifs : leur absence est publiée, pas dissimulée. La
# page dit qu'ils manquent plutôt que d'afficher « 0 amendement », ce qui
# serait faux.
# Les débats pèsent 55,8 Mo, et ils ne portent que les argumentaires : sans
# eux le parcours, les votes et les lois s'affichent normalement. Ils sont
# donc facultatifs au même titre, et leur absence est publiée, pas dissimulée.
FACULTATIVES = frozenset({"amendements", "debats"})


# Combien de fois redemander une source avant de renoncer, et combien de temps
# attendre entre deux essais.
#
# **La panne est passagère, et elle vient de chez eux.** Mesuré le 2026-09-23 :
# l'archive des amendements a répondu `HTTP Error 504: Gateway Time-out` après
# 50 secondes d'attente — le serveur de l'Assemblée n'a pas fini de préparer
# son plus gros fichier à temps. Le même fichier s'est téléchargé sans
# difficulté vingt minutes plus tard, 300 Mo en 103 secondes.
#
# Une reprise existait bien dans la publication — trois essais du programme
# entier — mais elle ne pouvait pas se déclencher : une exécution où une source
# facultative manque **réussit**, par construction. Elle doit donc se jouer
# ici, sur la source elle-même, et non dehors.
#
# **Elle vaut pour toutes les sources depuis le 2026-10-04, et pas seulement
# pour les facultatives.** Le raisonnement d'avant disait : « sans une source
# obligatoire il n'y a rien à publier, insister ne ferait que retarder
# l'erreur. » La publication n° 114 l'a démenti. Trois essais, trois `504`,
# chaque fois sur une source obligatoire — l'agenda deux fois, les acteurs une
# fois — et chaque essai avait retéléchargé les 310 Mo d'amendements avant d'y
# arriver. Un gigaoctet et neuf minutes dépensés pour éviter de redemander un
# fichier de 2,6 Mo. Le fichier des acteurs mettait alors 84 secondes pour ces
# 2,6 Mo : c'est la lenteur du serveur, pas l'absence du fichier.
#
# Une source obligatoire qui échoue **trois fois** fait toujours échouer la
# publication. Elle ne la fait plus échouer une seule fois.
ESSAIS = 3


PAUSE_ENTRE_ESSAIS = 20         # secondes


def telecharger_en_insistant(nom: str, chemin: pathlib.Path,
                             entetes: dict[str, str], url: str,
                             dormir=time.sleep) -> dict:
    """Télécharge, en redemandant jusqu'à `ESSAIS` fois.

    Ce qui distingue une source facultative d'une obligatoire n'est pas le
    nombre d'essais — c'est ce qui arrive **après** le dernier : l'appelant
    passe outre pour une facultative, et renonce pour une obligatoire.
    """
    for essai in range(1, ESSAIS + 1):
        try:
            return extraction.telecharger(chemin, entetes, url)
        except Exception as erreur:
            if essai == ESSAIS:
                raise
            print(f"  {nom:<10} essai {essai} sur {ESSAIS} :"
                  f" {erreur} — on réessaie", file=sys.stderr)
            dormir(PAUSE_ENTRE_ESSAIS)
    raise AssertionError("inatteignable")            # pragma: no cover


def connue(connexion: sqlite3.Connection, url: str) -> sqlite3.Row | None:
    return connexion.execute("SELECT * FROM source WHERE url = ?", (url,)).fetchone()


def entetes_conditionnelles(ligne: sqlite3.Row | None) -> dict[str, str]:
    """De quoi demander « seulement si ça a changé » et économiser 10 Mo."""
    if not ligne:
        return {}
    entetes = {}
    if ligne["etag"]:
        entetes["If-None-Match"] = ligne["etag"]
    if ligne["modifie_le"]:
        entetes["If-Modified-Since"] = ligne["modifie_le"]
    return entetes


def empreinte(fichier: pathlib.Path) -> str:
    """Le sha256 de l'archive, lu par morceaux pour ne pas la charger en mémoire."""
    condensat = hashlib.sha256()
    with fichier.open("rb") as flux:
        for morceau in iter(lambda: flux.read(1 << 20), b""):
            condensat.update(morceau)
    return condensat.hexdigest()
