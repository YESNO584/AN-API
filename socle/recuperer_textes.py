#!/usr/bin/env python3
"""Récupère le texte de chaque version d'un projet ou d'une proposition de loi.

    ./recuperer_textes.py                # rattrape ce qui manque, 20 min au plus
    ./recuperer_textes.py --minutes 60   # une passe plus longue
    ./recuperer_textes.py --documents PIONANR5L17B1794   # un seul, pour vérifier
    ./recuperer_textes.py --journal      # les dernières exécutions

Le résultat va dans `textes.db`, **à part de `parlement.db`**, pour la même
raison que `legi.db` : la base du Parlement se reconstruit chaque matin en une
minute, tandis que celle-ci demande de lire 2 295 documents un par un. On la
garde donc d'un jour sur l'autre, et on n'y ajoute que ce qui manque.

**Pourquoi une passe par jour plutôt qu'une longue.** Tout lire demande environ
50 minutes (mesuré : 2 295 documents, un appel par seconde). Ajouter ça d'un
coup à une publication qui dure trois minutes la rendrait fragile pour une
rubrique qui peut arriver en trois jours. Chaque exécution prend donc un budget
de temps, s'arrête dedans, et reprend le lendemain là où elle en était. **Un
texte publié ne change plus** : ce qui est lu ne se relit jamais.

**Le rythme, et pourquoi il est ce qu'il est.** Un appel par seconde, en
s'annonçant par un `User-Agent` qui nomme le projet. Le `robots.txt` de
l'Assemblée demande 30 secondes aux robots d'indexation ; nous ne parcourons
rien — on demande une liste connue de documents, une fois chacun, liste qui
vient de l'open data de l'Assemblée elle-même. Mesuré le 2026-09-18 : le taux
d'échec ne dépend pas de la cadence entre 0,5 et 5 secondes, et le serveur
répond « Retry-After: 5 » sur un refus passager, qu'on respecte.

Les documents sont publiés sous Licence Ouverte (Etalab), comme le reste.
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import pathlib
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request

import textes

ICI = pathlib.Path(__file__).parent
BASE = ICI / "textes.db"
PARLEMENT = ICI / "parlement.db"

# Un document par seconde. Voir la raison dans le docstring.
ATTENTE = 1.0
# Un refus passager se réessaie ; trois fois suffisent (mesuré : 10 reprises
# sur 11 au deuxième essai).
ESSAIS = 3

SCHEMA = """
CREATE TABLE IF NOT EXISTS document (
    uid      TEXT PRIMARY KEY,      -- PIONANR5L17BTC2362
    lu_le    TEXT NOT NULL,
    statut   TEXT NOT NULL,         -- lu | sans_article | absent
    octets   INTEGER NOT NULL DEFAULT 0,
    articles TEXT                   -- JSON {titre: texte}, dans l'ordre du texte
);

CREATE TABLE IF NOT EXISTS journal (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    quand    TEXT NOT NULL,
    lus      INTEGER NOT NULL,
    restants INTEGER NOT NULL,
    secondes REAL NOT NULL,
    message  TEXT
);
"""


def maintenant() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def ouvrir(chemin: pathlib.Path = BASE) -> sqlite3.Connection:
    connexion = sqlite3.connect(chemin)
    connexion.row_factory = sqlite3.Row
    connexion.executescript(SCHEMA)
    return connexion


# Un document qui porte le texte, et non un rapport, un avis ou une étude
# d'impact : les quatre familles qui déposent un texte, et les trois formes
# qu'il prend — déposé (`B`), de la commission (`BTC`), adopté (`BTA`).
# `ANR5` : le Sénat publie les siens ailleurs, et ce site-ci ne les sert pas
# (mesuré : 30 documents du Sénat demandés, 30 réponses 404).
VERSION = re.compile(r"^(PION|PRJL|PNRE|RION)ANR5L\d+(BTC|BTA|B)\d+$")


def est_une_version(ref: str) -> bool:
    return bool(VERSION.match(ref or ""))


def versions_attendues(chemin: pathlib.Path = PARLEMENT) -> list[str]:
    """Les documents que les étapes du parcours nomment, textes de loi seuls.

    Aucun appel réseau pour les connaître : l'archive des dossiers, que le
    socle télécharge chaque matin, dit à chaque étape quel document elle
    produit ou examine.
    """
    if not chemin.exists():
        return []
    connexion = sqlite3.connect(chemin)
    connexion.row_factory = sqlite3.Row
    vus: dict[str, None] = {}
    for ligne in connexion.execute(
            "SELECT e.details FROM etape e JOIN dossier d ON d.uid = e.dossier_uid"
            " WHERE d.est_loi = 1 AND e.details IS NOT NULL"
            " ORDER BY e.date, e.rang"):
        details = json.loads(ligne["details"] or "{}")
        for cle in ("texteAssocie", "texteAdopte"):
            ref = (details.get(cle) or {}).get("ref")
            if ref and est_une_version(ref):
                vus.setdefault(ref, None)
    connexion.close()
    return list(vus)


def deja_lus(base: sqlite3.Connection) -> set[str]:
    return {l["uid"] for l in base.execute("SELECT uid FROM document")}


def telecharger(uid: str) -> tuple[str | None, int]:
    """Le document, ou None s'il reste introuvable après les reprises."""
    requete = urllib.request.Request(textes.URL_DOCUMENT.format(uid),
                                     headers=textes.ENTETES)
    for essai in range(ESSAIS):
        try:
            with urllib.request.urlopen(requete, timeout=90) as reponse:
                brut = reponse.read()
                if reponse.headers.get("Content-Encoding") == "gzip":
                    brut = gzip.decompress(brut)
            return brut.decode("utf-8", "replace"), len(brut)
        except urllib.error.HTTPError as erreur:
            if erreur.code == 404:            # le document n'existe pas : inutile d'insister
                return None, 0
            # Le serveur dit lui-même quand revenir ; on l'écoute.
            time.sleep(float(erreur.headers.get("Retry-After") or 5))
        except Exception:
            time.sleep(2 + 3 * essai)
    return None, 0


def ranger(base: sqlite3.Connection, uid: str, source: str | None, octets: int) -> str:
    """Le texte extrait, pas le document : 13 % du poids, et rien de perdu.

    Mesuré sur 279 documents : le HTML pèse 421 Mo pour l'ensemble, les
    articles qu'on en tire 54 Mo. Ce qui est jeté est la mise en page Word.
    """
    if source is None:
        statut, articles = "absent", None
    else:
        trouves = textes.articles(source)
        # Un document sans article n'est pas un échec de lecture : c'est le
        # plus souvent une « petite loi » d'un texte que l'Assemblée n'a pas
        # adopté, qui ne contient aucun article, ou un document réduit à sa
        # page de garde par l'Assemblée elle-même.
        statut = "lu" if trouves else "sans_article"
        articles = json.dumps(trouves, ensure_ascii=False) if trouves else None
    base.execute("INSERT OR REPLACE INTO document VALUES (?,?,?,?,?)",
                 (uid, maintenant(), statut, octets, articles))
    return statut


def articles_du_document(base: sqlite3.Connection, uid: str) -> dict[str, str]:
    ligne = base.execute("SELECT articles FROM document WHERE uid = ?", (uid,)).fetchone()
    return json.loads(ligne["articles"]) if ligne and ligne["articles"] else {}


def passe(base: sqlite3.Connection, attendus: list[str], minutes: float,
          attente: float = ATTENTE) -> tuple[int, int]:
    """Lit ce qui manque, dans la limite du temps donné."""
    connus = deja_lus(base)
    restants = [u for u in attendus if u not in connus]
    debut, lus = time.monotonic(), 0
    for uid in restants:
        if (time.monotonic() - debut) / 60 >= minutes:
            break
        source, octets = telecharger(uid)
        ranger(base, uid, source, octets)
        base.commit()
        lus += 1
        time.sleep(attente)
    return lus, len(restants) - lus


def afficher_journal(base: sqlite3.Connection, combien: int = 10) -> None:
    for l in base.execute("SELECT * FROM journal ORDER BY id DESC LIMIT ?",
                          (combien,)).fetchall():
        print(f'{l["quand"]}  {l["lus"]:5d} lus, {l["restants"]:5d} restants,'
              f' {l["secondes"]:6.0f} s  {l["message"] or ""}')


def main(argv: list[str] | None = None) -> int:
    arguments = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    arguments.add_argument("--minutes", type=float, default=20,
                           help="budget de temps de la passe (20 par défaut)")
    arguments.add_argument("--documents", nargs="*",
                           help="ne lire que ces identifiants")
    arguments.add_argument("--journal", action="store_true",
                           help="afficher les dernières exécutions")
    arguments.add_argument("--attente", type=float, default=ATTENTE,
                           help="secondes entre deux appels (1 par défaut)")
    options = arguments.parse_args(argv)

    base = ouvrir()
    if options.journal:
        afficher_journal(base)
        return 0

    attendus = options.documents or versions_attendues()
    if not attendus:
        print("Aucune version à lire : la base du Parlement est-elle construite ?",
              file=sys.stderr)
        return 0
    debut = time.monotonic()
    lus, restants = passe(base, attendus, options.minutes, options.attente)
    secondes = time.monotonic() - debut
    compte = dict(base.execute(
        "SELECT statut, COUNT(*) n FROM document GROUP BY statut").fetchall())
    message = ", ".join(f"{n} {s}" for s, n in sorted(compte.items()))
    base.execute("INSERT INTO journal (quand, lus, restants, secondes, message)"
                 " VALUES (?,?,?,?,?)",
                 (maintenant(), lus, restants, secondes, message))
    base.commit()
    print(f"{lus} documents lus en {secondes:.0f} s, {restants} restants. {message}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
