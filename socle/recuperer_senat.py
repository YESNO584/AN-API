#!/usr/bin/env python3
"""Construit `senat.db` : les scrutins, les sénateurs et les séances à venir.

**Pourquoi une base à part.** Celle de l'Assemblée et celle-ci ne se remplissent
pas aux mêmes heures, ne cassent pas pour les mêmes raisons, et n'ont pas les
mêmes règles. Les garder ensemble obligeait à tout refaire quand l'une bougeait.
C'est le motif de `legi.db` et de `textes.db`, pour la même raison. Le pont
entre les deux est une seule colonne, `signet` — voir `schema_senat.sql`.

**Cette étape est facultative.** Sans elle, tout le reste se publie et
l'application n'affiche simplement ni les votes du Sénat, ni sa composition, ni
son calendrier.

Usage :
    ./recuperer_senat.py                 # cycle normal
    ./recuperer_senat.py --sessions 3    # ne relire que les 3 dernières pages
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import pathlib
import shutil
import sqlite3
import sys
import tempfile
import time
import urllib.error
import urllib.request

import extraction
import senat

RACINE = pathlib.Path(__file__).resolve().parent
BASE = RACINE / "senat.db"
SCHEMA = RACINE / "schema_senat.sql"

# Les pages de scrutins remontent à la session 2006-2007. Les sessions closes
# sont figées — vérifié le 2026-10-04, trois pages relues à quarante minutes
# d'intervalle sont identiques à l'octet près — donc une seule bouge vraiment.
PREMIERE_SESSION = 2006


def maintenant() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def ouvrir(chemin: pathlib.Path) -> sqlite3.Connection:
    cx = sqlite3.connect(chemin)
    cx.row_factory = sqlite3.Row
    cx.executescript(SCHEMA.read_text(encoding="utf-8"))
    return cx


def session_en_cours(aujourdhui: dt.date | None = None) -> int:
    """La session parlementaire commence en octobre et porte l'année d'avant.

    Le 4 octobre 2026 appartient à la session « 2026-2027 », que le Sénat
    nomme `scr2026`. Le 4 juin 2026 appartient encore à `scr2025`.
    """
    j = aujourdhui or dt.date.today()
    return j.year if j.month >= 10 else j.year - 1


def lire_url(url: str) -> str:
    """Une page du site du Sénat, compressée quand le serveur le veut bien."""
    requete = urllib.request.Request(
        url,
        headers={"Accept-Encoding": "gzip",
                 "User-Agent": "qui-vote-quoi (github.com/yesno584/AN-API)"})
    with urllib.request.urlopen(requete, timeout=120) as r:
        brut = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            import gzip
            brut = gzip.decompress(brut)
    return brut.decode("utf-8", "replace")


def lire_page(annee: int) -> str:
    """Une page de scrutins : 285 Ko en clair, 29 Ko sur le fil."""
    return lire_url(senat.URL_SCRUTINS.format(annee=annee))


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


def ranger_seances(cx: sqlite3.Connection, archive: pathlib.Path,
                   aujourdhui: str) -> int:
    """Les séances à venir, et le texte que chacune examine.

    **Un piège du nom de colonne, mesuré le 2026-10-04** : `date_seance.lecidt`
    ne porte pas un `lecidt` mais un `lecassidt`. Le chemin est donc
    `date_seance` → `lecass` → `lecture` → `loi.signet`, et croire au nom de la
    colonne rendait zéro séance sur dix-neuf.
    """
    lecass = {senat.net(l["lecassidt"]): senat.net(l["lecidt"])
              for l in senat.lire_dump(archive, "lecass")}
    lecture = {senat.net(l["lecidt"]): senat.net(l["loicod"])
               for l in senat.lire_dump(archive, "lecture")}
    signet = {senat.net(l["loicod"]): senat.net(l["signet"])
              for l in senat.lire_dump(archive, "loi") if l["signet"]}
    lignes = set()
    for l in senat.lire_dump(archive, "date_seance"):
        quand = (l["date_s"] or "")[:10]
        if quand <= aujourdhui:
            continue
        sig = signet.get(lecture.get(lecass.get(senat.net(l["lecidt"]), ""), ""))
        if sig:
            lignes.add((quand, sig))
    cx.execute("DELETE FROM seance_senat")
    cx.executemany("INSERT INTO seance_senat VALUES (?,?)", sorted(lignes))
    return len(lignes)


def ranger_themes(cx: sqlite3.Connection, chemin: pathlib.Path) -> int:
    """Le sujet de chaque dossier, tel que le Sénat le classe.

    Le fichier est celui que le socle lit déjà pour l'état d'un dossier, mais
    il est retéléchargé ici — 3,5 Mo — plutôt que partagé : les deux bases
    restent indépendantes, et c'est tout l'intérêt de les avoir séparées.
    """
    lignes = []
    for l in senat.lire_csv_senat(chemin):
        sig = senat.signet_de(l.get("URL du dossier"))
        if not sig:
            continue
        for rang, theme in enumerate(senat.themes_de(l.get("Thèmes"))):
            lignes.append((sig, theme, rang))
    cx.execute("DELETE FROM theme_senat")
    cx.executemany("INSERT OR REPLACE INTO theme_senat VALUES (?,?,?)", lignes)
    return len(lignes)


def ranger_dossiers(cx: sqlite3.Connection, archive: pathlib.Path) -> int:
    """Les dossiers du Sénat, pour faire le pont et nommer ce qu'on affiche."""
    lignes = [(senat.net(l["signet"]), senat.net(l["loicod"]),
               senat.net(l["loiint"]), senat.net(l["etaloicod"]))
              for l in senat.lire_dump(archive, "loi") if l["signet"]]
    cx.executemany("INSERT OR REPLACE INTO dossier_senat VALUES (?,?,?,?)", lignes)
    return len(lignes)


def construire(chemin: pathlib.Path, options) -> list[str]:
    """Remplit une base du Sénat. Rend les alertes, lève sur un vrai échec."""
    cx = ouvrir(chemin)
    with tempfile.TemporaryDirectory() as travail:
        dossier = pathlib.Path(travail)
        print("  dosleg", file=sys.stderr)
        archive = dossier / "dosleg.zip"
        extraction.telecharger(archive, None, senat.URL_DOSLEG)
        for nom, url in (("senateurs", senat.URL_SENATEURS),
                         ("histogroupes", senat.URL_HISTOGROUPES),
                         ("dossiers", senat.URL_DOSSIERS)):
            print(f"  {nom}", file=sys.stderr)
            extraction.telecharger(dossier / f"{nom}.csv", None, url)

        with cx:
            n_dos = ranger_dossiers(cx, archive)
            historique = lire_historique(dossier / "histogroupes.csv")
            actifs = [s for s in senat.lire_csv_senat(dossier / "senateurs.csv")
                      if s.get("État") == "ACTIF"]

            n_sen, noms, alertes_sources = senateurs_a_jour(
                cx, actifs, historique)
            # Les sessions à relire : celle en cours toujours, les closes une
            # seule fois — elles sont figées.
            en_cours = session_en_cours()
            deja = {l["session"] for l in cx.execute(
                "SELECT DISTINCT session FROM scrutin_senat WHERE signet IS NOT NULL")}
            sessions = [s for s in range(PREMIERE_SESSION, en_cours + 1)
                        if s == en_cours or s not in deja]
            if options.sessions:
                sessions = sessions[-options.sessions:]
            n_scr, alertes = ranger_scrutins(cx, archive, sessions)
            alertes += alertes_sources
            # Sans l'historique, aucun vote ne peut être attribué à un
            # groupe : le recalculer rendrait 278 552 « sans groupe ».
            n_vot = (ranger_votes(cx, archive, historique, options.depuis)
                     if historique else 0)
            habits, alerte_couleurs = couleurs_des_groupes()
            if alerte_couleurs:
                alertes.append(alerte_couleurs)
            # `ranger_groupes` recompte les effectifs sur `senateur` : sans
            # liste neuve, il recompterait la même chose, mais il perdrait les
            # noms courts que seul le fichier des sénateurs porte.
            n_grp = (ranger_groupes(cx, options.depuis, noms, habits) if noms
                     else cx.execute(
                         "SELECT COUNT(*) n FROM groupe_senat").fetchone()["n"])
            n_sea = ranger_seances(cx, archive, dt.date.today().isoformat())
            n_the = ranger_themes(cx, dossier / "dossiers.csv")

            # La date de construction : c'est elle que la page affichera le
            # jour où les données du Sénat datent de la veille.
            cx.execute("INSERT OR REPLACE INTO source (url, vu_le)"
                       " VALUES (?, ?)", (MARQUE_DE_FRAICHEUR, maintenant()))

    print(f"  {n_dos:>7,} dossiers · {n_scr:>6,} scrutins ({len(sessions)} sessions"
          f" relues) · {n_vot:>6,} lignes de vote par groupe", file=sys.stderr)
    print(f"  {n_sen:>7,} sénateurs · {n_grp} groupes ({len(habits)} teintés)"
          f" · {n_sea} séances à venir"
          f" · {n_the:,} rattachements de thème", file=sys.stderr)
    cx.close()
    return alertes


# Ce que la base doit porter pour valoir d'être publiée. Ce ne sont pas des
# seuils de qualité : ce sont les tables sans lesquelles un écran entier
# disparaît de l'application.
VITAL = {
    "senateur": "la composition du Sénat",
    "dossier_senat": "le pont avec nos textes",
    "theme_senat": "les sujets",
}
MARQUE_DE_FRAICHEUR = "senat.db"


def compter(chemin: pathlib.Path) -> dict[str, int]:
    cx = sqlite3.connect(chemin)
    try:
        return {t: cx.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in VITAL}
    except sqlite3.Error:
        return {}
    finally:
        cx.close()


def assez_pour_remplacer(neuve: pathlib.Path,
                         ancienne: pathlib.Path) -> str | None:
    """Ce qui empêche de remplacer la base de la veille, ou rien.

    **La règle tient en une phrase : ne jamais remplacer par pire, mais ne
    jamais refuser mieux.** Le 2026-10-06, `data.senat.fr` a rendu une page web
    à la place de ses fichiers de sénateurs : la construction laissait une base
    vide et l'onglet « Sénat » perdait tout.

    Exiger que **chaque** table vitale soit remplie était la première parade —
    et elle protégeait trop large : le même jour, les dossiers, les séances et
    les sujets arrivaient parfaitement, et ils restaient bloqués parce que la
    liste des sénateurs manquait. Un écran qui dit honnêtement « pas de
    données » vaut mieux que trois écrans gelés.

    Trois refus, donc, et seulement trois : une base illisible ; une base
    **entièrement** vide ; et une table qui **perd plus d'un quart** de ses
    lignes, ce qui n'arrive pas en un jour au Parlement et signe une source à
    moitié lue.
    """
    neuf = compter(neuve)
    if not neuf:
        return "la base construite n'est pas lisible"
    if not any(neuf.values()):
        return "la base construite est entièrement vide"
    if not ancienne.exists():
        return None
    vieux = compter(ancienne)
    for table, quoi in VITAL.items():
        avant, apres = vieux.get(table, 0), neuf[table]
        if avant and apres < avant * 0.75:
            return (f"{quoi} : {apres:,} lignes contre {avant:,} la veille"
                    f" ({apres / avant:.0%})")
    return None


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--base", type=pathlib.Path, default=BASE)
    a.add_argument("--sessions", type=int, default=0,
                   help="combien de sessions relire (0 = celles qui manquent)")
    a.add_argument("--depuis", default="2024-01-01",
                   help="la date à partir de laquelle on détaille les votes")
    options = a.parse_args()

    # **On construit à côté, et on ne remplace qu'en cas de succès complet.**
    # Avant, la construction écrivait directement dans la base publiée : le
    # 2026-10-06, une source du Sénat a rendu une page web au lieu d'un CSV,
    # la construction s'est arrêtée, et le site a perdu d'un coup la
    # composition, le calendrier et les 30 sujets du Sénat. Une reconstruction
    # qui échoue ne doit rien coûter.
    #
    # On **part de la base existante** plutôt que de rien : les sessions de
    # scrutins closes sont figées, et les relire toutes redemanderait 21 pages
    # au Sénat chaque matin pour le même résultat.
    base = options.base
    chantier = base.with_name(base.name + ".chantier")
    chantier.unlink(missing_ok=True)
    if base.exists():
        shutil.copy2(base, chantier)

    def renoncer(pourquoi: str) -> int:
        chantier.unlink(missing_ok=True)
        print(f"  {pourquoi}", file=sys.stderr)
        # Dire laquelle des deux situations on est dans : « on garde la veille »
        # serait faux le jour où il n'y a pas de veille — et c'est ce jour-là
        # que l'onglet « Sénat » s'affiche vide.
        print("  la base de la veille est gardée telle quelle" if base.exists()
              else "  et il n'y a aucune base de la veille : le site n'aura pas"
                   " de données du Sénat", file=sys.stderr)
        return 1

    try:
        alertes = construire(chantier, options)
    except Exception as erreur:
        return renoncer(f"ÉCHEC {type(erreur).__name__}: {erreur}")

    souci = assez_pour_remplacer(chantier, base)
    if souci:
        return renoncer(f"REFUS de remplacer : {souci}")

    os.replace(chantier, base)
    for x in alertes:
        print(f"  ALERTE {x}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
