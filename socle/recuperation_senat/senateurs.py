"""Les sénateurs en exercice et leur groupe au jour voulu — ou ceux d'hier, quand leur source ne se lit pas.
"""
from __future__ import annotations

import collections
import datetime as dt
import pathlib
import sqlite3
import senat


# Le groupe « AUCUN » n'en est pas un : depuis le renouvellement du
# 2026-09-27, 179 sénateurs sur 348 n'ont pas redéclaré leur appartenance.
# L'écran doit le dire, pas l'inventer en un dixième groupe.
PAS_UN_GROUPE = frozenset({"AUCUN", "", None})


def lire_historique(chemin: pathlib.Path) -> dict[str, list[tuple]]:
    """L'appartenance de chaque sénateur à un groupe, avec ses dates.

    **La clé est le code du groupe, pas son nom.** Les deux fichiers du Sénat
    ne nomment pas les groupes pareil — l'un écrit « SER », l'autre « Groupe
    Socialiste, Écologiste et Républicain » — et ils ne se rejoignent que par
    le matricule du sénateur. Ranger les votes par nom laissait tous les rangs
    vides (constaté le 2026-10-04).

    **Et le code est périmé** : `UMP` désigne Les Républicains, `LREM` le RDPI.
    Il sert de clé, jamais d'étiquette.

    Une appartenance en cours n'a pas de date de fin — 353 sur 3 552.
    """
    par_matricule: dict[str, list[tuple]] = collections.defaultdict(list)
    for l in senat.lire_csv_senat(chemin):
        par_matricule[l["Matricule"]].append((
            (l["Date de début d\'appartenance"] or "")[:10],
            (l["Date de fin d\'appartenance"] or "")[:10],
            l["Code du groupe politique"],
            l["Nom court du groupe politique"]))
    return par_matricule


def groupe_au(historique: dict, matricule: str | None, quand: str) -> str | None:
    """Le code du groupe d'un sénateur à cette date, ou rien."""
    for debut, fin, code, _ in historique.get(matricule or "", ()):
        if code in PAS_UN_GROUPE:
            continue
        if (not debut or debut <= quand) and (not fin or quand <= fin):
            return code
    return None


def noms_des_groupes(historique: dict, actifs: list[dict]) -> dict[str, str]:
    """Comment nommer chaque groupe à l'écran.

    L'étiquette courte vient du fichier des sénateurs, retrouvée par le
    matricule ; un groupe qui n'a plus aucun membre en exercice garde le nom
    long de la source, faute de mieux.
    """
    noms = {}
    for lignes in historique.values():
        for _, _, code, nom in lignes:
            if code not in PAS_UN_GROUPE:
                noms.setdefault(code, nom)
    aujourdhui = dt.date.today().isoformat()
    for s in actifs:
        code = groupe_au(historique, s["Matricule"], aujourdhui)
        court = s.get("Groupe politique")
        if code and court and court != "Aucun":
            noms[code] = court
    return noms


def senateurs_a_jour(cx: sqlite3.Connection, actifs: list[dict],
                     historique: dict) -> tuple[int, dict, list[str]]:
    """Met la liste des sénateurs à jour, **ou garde celle d'hier**.

    **Une source cassée ne doit pas en bloquer quatre.** Le 2026-10-06, tout
    le dossier `senateurs/` de `data.senat.fr` rendait une page web — y compris
    pour un nom de fichier inventé — pendant que les dossiers, les scrutins,
    les séances et les sujets arrivaient parfaitement. Sans cette porte, un
    seul dossier en panne gelait toute la base du Sénat : la liste sortait
    vide, le garde-fou refusait de remplacer, et plus rien ne se mettait à
    jour.

    `senateur` et `groupe_senat` sont alors laissées **telles qu'elles sont** :
    ni vidées, ni remplies de vide. **Un Parlement sans aucun membre n'existe
    pas** — une liste vide est toujours une panne, jamais une actualité.

    Rend le nombre de sénateurs, les noms courts des groupes (vides si la
    source manque, pour que `ranger_groupes` ne soit pas appelé), et les
    alertes à écrire au journal.
    """
    if actifs and historique:
        return (ranger_senateurs(cx, actifs, historique),
                noms_des_groupes(historique, actifs), [])
    manquants = " et ".join(
        n for n, v in (("la liste des sénateurs", actifs),
                       ("l'historique des groupes", historique)) if not v)
    garde = cx.execute("SELECT COUNT(*) n FROM senateur").fetchone()["n"]
    return garde, {}, [f"{manquants} : source illisible — les {garde} "
                       f"sénateurs déjà en base sont gardés tels quels"]


def ranger_senateurs(cx: sqlite3.Connection, actifs: list[dict],
                     historique: dict) -> int:
    """Les sénateurs en exercice.

    **Tout vient de `data.senat.fr`, sous Licence Ouverte 2.0.** Le fichier du
    site qui porterait le numéro de siège et la photo n'est pas repris : les
    photographies ne sont pas libres, et un numéro de siège ne sert à rien
    puisque l'hémicycle ne peut pas se dessiner (voir `senat.rang_par_les_votes`).
    """
    aujourdhui = dt.date.today().isoformat()
    cx.execute("DELETE FROM senateur")
    cx.executemany(
        "INSERT INTO senateur (matricule, civilite, prenom, nom, groupe,"
        " circonscription) VALUES (?,?,?,?,?,?)",
        [(s["Matricule"], s["Qualité"], s["Prénom usuel"], s["Nom usuel"],
          groupe_au(historique, s["Matricule"], aujourdhui),
          s["Circonscription"]) for s in actifs])
    return len(actifs)
