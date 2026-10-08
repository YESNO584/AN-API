"""Les scrutins du Sénat : leurs chiffres depuis l'open data, le dossier qu'ils concernent depuis le site, et qui a voté quoi au jour du vote.
"""
from __future__ import annotations

import collections
import datetime as dt
import pathlib
import sqlite3
import sys
import urllib.error
import urllib.request
import senat
from recuperation_senat.senateurs import groupe_au
from recuperation_senat.site import lire_page


# Les pages de scrutins remontent à la session 2006-2007. Les sessions closes
# sont figées — vérifié le 2026-10-04, trois pages relues à quarante minutes
# d'intervalle sont identiques à l'octet près — donc une seule bouge vraiment.
PREMIERE_SESSION = 2006


def session_en_cours(aujourdhui: dt.date | None = None) -> int:
    """La session parlementaire commence en octobre et porte l'année d'avant.

    Le 4 octobre 2026 appartient à la session « 2026-2027 », que le Sénat
    nomme `scr2026`. Le 4 juin 2026 appartient encore à `scr2025`.
    """
    j = aujourdhui or dt.date.today()
    return j.year if j.month >= 10 else j.year - 1


def ranger_scrutins(cx: sqlite3.Connection, archive: pathlib.Path,
                    sessions: list[int]) -> tuple[int, list[str]]:
    """Les scrutins, leurs chiffres, et le dossier que chacun concerne.

    Les chiffres viennent de l'open data ; **le dossier vient des pages du
    site**, parce qu'aucun fichier publié ne relie un scrutin à un texte.
    """
    alertes = []
    liens: dict[tuple[int, int], str | None] = {}
    for annee in sessions:
        connus = cx.execute(
            "SELECT COUNT(*) n FROM scrutin_senat WHERE session = ?",
            (annee,)).fetchone()["n"]
        try:
            trouves = senat.scrutins_de_la_page(lire_page(annee))
        except urllib.error.HTTPError as erreur:
            # **Une session qui n'a pas encore voté n'a pas de page.** La
            # session 2026-2027 s'est ouverte le 1er octobre et son adresse
            # répondait 404 le 4 : ce n'est pas une panne, et l'annoncer comme
            # telle ferait crier au loup chaque rentrée.
            if erreur.code == 404 and annee == session_en_cours():
                print(f"  session {annee} : pas encore de scrutin",
                      file=sys.stderr)
            else:
                alertes.append(f"session {annee} : HTTP {erreur.code}")
            continue
        except Exception as erreur:
            alertes.append(f"session {annee} : {type(erreur).__name__}: {erreur}")
            continue
        # **Le témoin de structure.** Une page refaite arrive, pèse son poids,
        # et la lecture en tire zéro : sans lui, on publierait « aucun vote au
        # Sénat » partout, ce qui serait faux.
        souci = senat.page_lisible(trouves, attendus=connus or None)
        if souci:
            alertes.append(f"session {annee} : {souci}")
            continue
        liens.update(trouves)

    # **Le lien n'est écrit que pour les sessions qu'on vient de lire.** Écraser
    # tout avec ce qu'on a sous la main effaçait les liens des sessions non
    # relues : 666 scrutins rattachés, puis zéro depuis 2024, après une passe
    # qui ne portait que sur quatre vieilles sessions (constaté le 2026-10-04).
    lues = {a for a in sessions if any(s == a for s, _ in liens)}
    lignes = []
    for l in senat.lire_dump(archive, "scr"):
        cle = (int(l["sesann"]), int(l["scrnum"]))
        lignes.append((cle[0], cle[1], (l["scrdat"] or "")[:10],
                       senat.net(l["scrint"]), l["scrpou"], l["scrcon"]))
    # Les chiffres se réécrivent toujours ; le lien, seulement pour une session
    # dont la page a été lue sans alerte.
    cx.executemany(
        "INSERT INTO scrutin_senat (session, numero, date, objet, pour, contre)"
        " VALUES (?,?,?,?,?,?) ON CONFLICT (session, numero) DO UPDATE SET"
        " date = excluded.date, objet = excluded.objet,"
        " pour = excluded.pour, contre = excluded.contre", lignes)
    cx.executemany(
        "UPDATE scrutin_senat SET signet = ? WHERE session = ? AND numero = ?",
        [(sig, s, n) for (s, n), sig in liens.items() if s in lues])
    return len(lignes), alertes


def ranger_votes(cx: sqlite3.Connection, archive: pathlib.Path,
                 historique: dict, depuis: str) -> int:
    """Qui a voté quoi, groupe par groupe, **au jour du scrutin**.

    Un sénateur change de groupe : lui donner celui d'aujourd'hui ferait dire
    au passé ce qu'il n'a pas dit. L'historique des appartenances donne le bon,
    et le rapprochement est total — 278 552 votes sur 278 552 depuis 2024
    (mesuré le 2026-10-04).

    `depuis` borne le travail : 1,66 million de votes nominatifs existent, et
    l'application n'affiche que ceux des textes qu'elle suit.
    """
    POSITIONS = {"1": "pour", "2": "contre", "3": "abstentions", "4": "non_votants"}
    dates = {(l["session"], l["numero"]): l["date"] for l in cx.execute(
        "SELECT session, numero, date FROM scrutin_senat"
        " WHERE date >= ? AND signet IS NOT NULL", (depuis,))}
    compte: dict[tuple, collections.Counter] = collections.defaultdict(
        collections.Counter)
    sans_groupe = 0
    for l in senat.lire_dump(archive, "votsen"):
        cle = (int(l["sesann"]), int(l["scrnum"]))
        quand = dates.get(cle)
        if not quand:
            continue
        sigle = groupe_au(historique, senat.net(l["senmat"]), quand)
        if not sigle:
            sans_groupe += 1
            continue
        compte[(cle[0], cle[1], sigle)][POSITIONS.get(l["posvotcod"], "")] += 1
    if sans_groupe:
        print(f"  {sans_groupe:,} votes sans groupe retrouvé", file=sys.stderr)
    cx.executemany(
        "INSERT OR REPLACE INTO vote_groupe_senat VALUES (?,?,?,?,?,?,?)",
        [(s, n, g, c["pour"], c["contre"], c["abstentions"], c["non_votants"])
         for (s, n, g), c in compte.items()])
    return len(compte)
