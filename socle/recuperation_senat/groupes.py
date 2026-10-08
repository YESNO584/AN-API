"""Les groupes du Sénat : leur effectif, leur rang mesuré sur les votes, et leur couleur lue sur le site — ou reprise du dernier relevé, ou de la veille.
"""
from __future__ import annotations

import collections
import json
import sqlite3
import sys
import time
import senat
from recuperation_senat.site import lire_url


# `senat.fr` coupe la connexion par intermittence : mesuré le 2026-10-05, deux
# lectures sur trois ont échoué d'affilée sur un serveur qui répondait très
# bien la minute suivante. Les mêmes chiffres que pour les archives
# facultatives de l'Assemblée, pour la même raison.
ESSAIS = 3


PAUSE_ENTRE_ESSAIS = 20         # secondes


def couleurs_des_groupes() -> tuple[dict[str, dict], str | None]:
    """La couleur et le nom complet de chaque groupe.

    **La page est la source, le fichier versionné est le filet.** Trois choses
    tiennent cette fonction, et il faut les trois — le 2026-10-05, il n'y en
    avait aucune et l'hémicycle du Sénat s'est affiché tout gris :

    1. **On redemande** : le serveur coupe la connexion par intermittence.
    2. **On retombe sur `groupes_senat.json`** quand la page ne donne plus
       rien — ce jour-là, le Sénat en avait retiré l'élément porteur.
    3. Et au-delà d'ici, `ranger_groupes` **garde ce que la base avait**.

    Rend les groupes et, s'il y a lieu, la raison en clair pour le journal.
    """
    dernier = None
    for essai in range(1, ESSAIS + 1):
        try:
            groupes = senat.groupes_de_la_page(lire_url(senat.URL_GROUPES))
        except Exception as erreur:                  # réseau, délai, serveur
            dernier = f"page des groupes illisible : {erreur}"
            if essai < ESSAIS:
                print(f"  groupes   essai {essai} sur {ESSAIS} : {erreur}",
                      file=sys.stderr)
                time.sleep(PAUSE_ENTRE_ESSAIS)
            continue
        # La page a répondu. Si elle ne porte plus l'information, la
        # redemander n'y changera rien : on passe au filet tout de suite.
        souci = senat.groupes_lisibles(groupes)
        if not souci:
            return groupes, None
        dernier = souci
        break

    secours = senat.couleurs_de_secours()
    if secours:
        return secours, (f"{dernier} — couleurs reprises du relevé du "
                         f"{_date_du_secours()}")
    return {}, dernier


def _date_du_secours() -> str:
    try:
        return json.loads(senat.SECOURS.read_text(encoding="utf-8")).get(
            "_lu_le", "?")
    except (OSError, ValueError):
        return "?"


def ranger_groupes(cx: sqlite3.Connection, depuis: str, noms: dict[str, str],
                   habits: dict[str, dict] | None = None) -> int:
    """Les groupes, leur effectif, leur rang, leur nom complet et leur couleur.

    Le rang est **mesuré sur la façon de voter**, faute de pouvoir l'être sur
    les sièges — voir `senat.rang_par_les_votes`. La couleur et le nom complet,
    eux, sont recopiés du site : nous n'en inventons aucun.
    """
    effectifs = {l["groupe"]: l["n"] for l in cx.execute(
        "SELECT groupe, COUNT(*) n FROM senateur WHERE groupe IS NOT NULL"
        " GROUP BY groupe")}
    positions: dict[str, dict[str, float]] = collections.defaultdict(dict)
    for l in cx.execute(
            "SELECT v.session, v.numero, v.groupe, v.pour, v.contre"
            " FROM vote_groupe_senat v JOIN scrutin_senat s"
            "   ON s.session = v.session AND s.numero = v.numero"
            " WHERE s.date >= ?", (depuis,)):
        exprimes = l["pour"] + l["contre"]
        # Un groupe qui n'exprime presque rien sur un scrutin n'y dit rien.
        if exprimes >= 3:
            positions[l["groupe"]][f'{l["session"]}-{l["numero"]}'] = \
                l["pour"] / exprimes
    rang = {g: i for i, g in enumerate(senat.rang_par_les_votes(
        dict(positions), senat.GROUPE_LE_PLUS_A_GAUCHE))}
    # **Ne jamais effacer ce qu'on avait.** La table se vide et se réécrit à
    # chaque passage ; sans cette reprise, un jour où la page des groupes ne
    # se lit pas emportait les couleurs de la veille — c'est ce qui est arrivé
    # le 2026-10-05. Ce qui arrive aujourd'hui l'emporte, le reste est repris.
    habits = dict(habits or {})
    for l in cx.execute("SELECT sigle, nom_complet, couleur FROM groupe_senat"):
        if l["couleur"] and not habits.get(l["sigle"], {}).get("couleur"):
            habits[l["sigle"]] = {"nom": l["nom_complet"], "couleur": l["couleur"]}
    cx.execute("DELETE FROM groupe_senat")
    cx.executemany(
        "INSERT INTO groupe_senat"
        " (sigle, nom, nom_complet, couleur, effectif, rang)"
        " VALUES (?,?,?,?,?,?)",
        [(g, noms.get(g, g), habits.get(g, {}).get("nom"),
          habits.get(g, {}).get("couleur"), n, rang.get(g))
         for g, n in effectifs.items()])
    return len(effectifs)
