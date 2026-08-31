#!/usr/bin/env python3
"""Écrit les données de la base en fichiers tout prêts, à publier tels quels.

Pourquoi des fichiers plutôt qu'un serveur : les données ne changent qu'une
fois par jour et personne ne les modifie. Il n'y a donc rien à calculer en
direct. Des fichiers publiés quelque part suffisent — pas de machine à louer,
à surveiller ni à mettre à jour, et l'application démarre plus vite parce
qu'elle lit un fichier au lieu d'interroger un serveur.

Ce que ça produit (environ 2,5 Mo au total, 120 Ko pour la liste une fois
compressée) :

    public/etat.json              d'où viennent les données et de quand
    public/etapes.json            les six étapes du parcours, et leurs comptes
    public/textes.json            les textes en cours — le fichier principal
    public/promulgues.json        les lois déjà promulguées
    public/textes/<uid>.json      un fichier par texte, avec tout son parcours

Usage :
    ./publier.py                  # écrit dans public/
    ./publier.py --vers dossier
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import shutil
import sqlite3
import sys

import extraction

RACINE = pathlib.Path(__file__).resolve().parent
BASE = RACINE / "parlement.db"
SORTIE = RACINE / "public"
MAQUETTE = RACINE.parent / "maquette" / "feed.html"

# Ce que la liste embarque pour chaque texte. Volontairement court : elle est
# chargée en entier par l'application, qui filtre et cherche ensuite toute
# seule, hors connexion. Le reste est dans le fichier de détail.
CHAMPS_LISTE = ("uid", "titre", "type", "chambre", "chambre_initiale", "etape",
                "date_dernier_mouvement", "lecture", "dernier_acte", "conclusion",
                "prochaine_date", "prochaine_quoi", "url_an", "url_senat")

CHAMPS_VOTE = ("uid", "date", "type", "portee", "objet", "sort", "annonce",
               "demandeur", "votants", "requis", "pour", "contre", "abstentions",
               "non_votants")


def resume_votes(cx: sqlite3.Connection) -> dict[str, dict]:
    """Par texte, de quoi afficher une carte sans ouvrir son fichier de détail.

    On ne retient que le vote **sur l'ensemble du texte** le plus récent :
    c'est celui qui décide si le texte poursuit son chemin. Les 7 218 votes
    sur des amendements comptent, mais ne se résument pas — ils sont dans le
    fichier de détail.
    """
    resume: dict[str, dict] = {}
    for l in cx.execute(
            "SELECT dossier_uid, COUNT(*) n,"
            " SUM(portee = 'ensemble') ensembles,"
            " MAX(date) derniere"
            " FROM vote WHERE dossier_uid IS NOT NULL GROUP BY dossier_uid"):
        resume[l["dossier_uid"]] = {"votes": l["n"], "votesEnsemble": l["ensembles"],
                                    "dernierVote": l["derniere"], "voteEnsemble": None}
    for l in cx.execute(
            "SELECT dossier_uid, date, sort, pour, contre, abstentions, objet"
            " FROM vote WHERE dossier_uid IS NOT NULL AND portee = 'ensemble'"
            " ORDER BY date"):
        resume[l["dossier_uid"]]["voteEnsemble"] = {
            "date": l["date"], "sort": l["sort"], "pour": l["pour"],
            "contre": l["contre"], "abstentions": l["abstentions"],
            "objet": l["objet"],
        }
    return resume


def votes_du_texte(cx: sqlite3.Connection, uid: str) -> list[dict]:
    votes = []
    for v in cx.execute(
            f"SELECT {', '.join(CHAMPS_VOTE)} FROM vote WHERE dossier_uid = ?"
            " ORDER BY date DESC, numero DESC", (uid,)):
        # Rangés comme dans l'hémicycle, de la gauche à la droite. Un groupe
        # que la source ne nomme plus — un groupe dissous — passe en fin de
        # liste plutôt que de disparaître.
        groupes = [dict(g) for g in cx.execute(
            "SELECT vg.sigle, vg.nom, vg.membres, vg.position, vg.pour, vg.contre,"
            " vg.abstentions, vg.non_votants, g.rang, g.couleur"
            " FROM vote_groupe vg LEFT JOIN groupe g ON g.ref = vg.organe_ref"
            " WHERE vg.vote_uid = ?"
            " ORDER BY g.rang IS NULL, g.rang, vg.membres DESC", (v["uid"],))]
        votes.append({**dict(v), "groupes": groupes})
    return votes


def ecrire(chemin: pathlib.Path, contenu, brut: bytes | None = None) -> int:
    """Écrit du JSON, ou des octets tels quels si `brut` est fourni."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if brut is None:
        brut = json.dumps(contenu, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    chemin.write_bytes(brut)
    return len(brut)


def publier(cx: sqlite3.Connection, sortie: pathlib.Path) -> dict[str, int]:
    # On repart d'un dossier vide : un texte promulgué hier ne doit pas rester
    # dans la liste des textes en cours d'avant-hier.
    if sortie.exists():
        shutil.rmtree(sortie)
    sortie.mkdir(parents=True)

    tailles: dict[str, int] = {}
    genere_le = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    votes = resume_votes(cx)

    comptes = {l["statut"]: l["n"] for l in cx.execute(
        "SELECT statut, COUNT(*) n FROM dossier WHERE est_loi = 1 GROUP BY statut")}
    par_etape = {l["etape"]: l["n"] for l in cx.execute(
        "SELECT etape, COUNT(*) n FROM dossier"
        " WHERE statut='en_cours' AND est_loi=1 AND etape IS NOT NULL GROUP BY etape")}

    chargement = cx.execute(
        "SELECT * FROM journal WHERE statut = 'succes' ORDER BY id DESC LIMIT 1").fetchone()

    tailles["etat.json"] = ecrire(sortie / "etat.json", {
        "genereLe": genere_le,
        "source": extraction.URL_ARCHIVE,
        "licence": "Licence Ouverte (Etalab)",
        "legislature": extraction.LEGISLATURE,
        "dernierChargement": dict(chargement) if chargement else None,
        "dossiers": cx.execute("SELECT COUNT(*) n FROM dossier").fetchone()["n"],
        "etapesEnregistrees": cx.execute("SELECT COUNT(*) n FROM etape").fetchone()["n"],
        "textesEnCours": comptes.get(extraction.EN_COURS, 0),
        "promulgues": comptes.get(extraction.PROMULGUE, 0),
        "scrutins": cx.execute("SELECT COUNT(*) n FROM vote").fetchone()["n"],
        "textesAvecVote": cx.execute(
            "SELECT COUNT(DISTINCT d.uid) n FROM dossier d JOIN vote v ON v.dossier_uid = d.uid"
            " WHERE d.est_loi = 1 AND d.statut IN ('en_cours','promulgue')").fetchone()["n"],
        "fichiers": ["etapes.json", "groupes.json", "textes.json", "promulgues.json",
                     "textes/<uid>.json"],
    })

    # Les groupes, rangés de la gauche à la droite de l'hémicycle. L'ordre est
    # mesuré sur les numéros de siège publiés ; la couleur est une convention
    # d'affichage, que la page reprend telle quelle plutôt que d'en inventer.
    tailles["groupes.json"] = ecrire(sortie / "groupes.json", {
        "genereLe": genere_le,
        "ordre": "de la gauche à la droite de l'hémicycle, d'après les numéros"
                 " de siège publiés par l'Assemblée",
        "couleurs": "convention d'affichage — l'open data n'en publie aucune",
        "groupes": [dict(g) for g in cx.execute(
            "SELECT ref, sigle, nom, rang, siege_median, couleur"
            " FROM groupe ORDER BY rang")],
    })

    tailles["etapes.json"] = ecrire(sortie / "etapes.json", {
        "genereLe": genere_le,
        "etapes": [{"n": n, "nom": nom, "quoi": quoi, "textesEnCours": par_etape.get(n, 0)}
                   for n, nom, quoi in extraction.ETAPES],
        # Les lois promulguées ne sont pas une septième étape : c'est l'après.
        # Mais un lecteur qui compte les textes doit les retrouver quelque part.
        "promulguees": comptes.get(extraction.PROMULGUE, 0),
    })

    for nom_fichier, statut in (("textes.json", extraction.EN_COURS),
                                ("promulgues.json", extraction.PROMULGUE)):
        # Les plus avancés d'abord : un texte près d'être promulgué intéresse
        # plus qu'une proposition déposée et jamais examinée — et celles-ci
        # sont l'immense majorité.
        lignes = cx.execute(
            f"SELECT {', '.join(CHAMPS_LISTE)}, loi_numero, loi_date, loi_url_jo"
            " FROM dossier WHERE statut = ? AND est_loi = 1"
            " ORDER BY etape DESC, date_dernier_mouvement DESC, uid", (statut,)).fetchall()
        textes = []
        for l in lignes:
            texte = {c: l[c] for c in CHAMPS_LISTE}
            texte.update(votes.get(l["uid"], {"votes": 0, "votesEnsemble": 0,
                                              "dernierVote": None, "voteEnsemble": None}))
            if statut == extraction.PROMULGUE:
                texte.update(loiNumero=l["loi_numero"], loiDate=l["loi_date"],
                             loiUrlJO=l["loi_url_jo"])
            textes.append(texte)
        tailles[nom_fichier] = ecrire(sortie / nom_fichier,
                                      {"genereLe": genere_le, "total": len(textes),
                                       "textes": textes})

    # Le détail, un fichier par texte. Seulement pour ceux que les listes
    # citent : publier les 708 dossiers qui ne font pas de loi n'aurait
    # aucun lecteur.
    details = 0
    for l in cx.execute(
            "SELECT * FROM dossier WHERE est_loi = 1 AND statut IN (?, ?)",
            (extraction.EN_COURS, extraction.PROMULGUE)):
        parcours = [dict(e) for e in cx.execute(
            "SELECT code, lecture, libelle, chambre, date, numero, conclusion, future"
            " FROM etape WHERE dossier_uid = ? ORDER BY date, rang", (l["uid"],))]
        details += ecrire(sortie / "textes" / f'{l["uid"]}.json',
                          {**dict(l), "parcours": parcours,
                           "votes": votes_du_texte(cx, l["uid"])})
    tailles["textes/*.json"] = details

    # La maquette devient la page d'accueil. Publiée à côté des données, elle
    # les lit par une adresse relative — et l'adresse racine sert enfin à
    # quelque chose au lieu de renvoyer une erreur.
    if MAQUETTE.exists():
        tailles["index.html"] = ecrire(sortie / "index.html", None,
                                       MAQUETTE.read_bytes())
    else:
        print(f"Maquette introuvable ({MAQUETTE}) : pas de page d'accueil.",
              file=sys.stderr)

    # GitHub Pages ne sert pas les dossiers dont le nom commence par un
    # tiret bas, et ajoute sa propre mise en page aux fichiers Markdown.
    # `.nojekyll` désactive tout ça : on veut nos fichiers, tels quels.
    (sortie / ".nojekyll").write_text("", encoding="utf-8")
    return tailles


def main() -> int:
    analyseur = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analyseur.add_argument("--base", type=pathlib.Path, default=BASE)
    analyseur.add_argument("--vers", type=pathlib.Path, default=SORTIE)
    options = analyseur.parse_args()

    if not options.base.exists():
        print(f"Base introuvable : {options.base}\nLancer d'abord ./recuperer.py",
              file=sys.stderr)
        return 1

    cx = sqlite3.connect(f"file:{options.base}?mode=ro", uri=True)
    cx.row_factory = sqlite3.Row
    tailles = publier(cx, options.vers)
    cx.close()

    fichiers = sum(1 for _ in options.vers.rglob("*") if _.is_file())
    print(f"Écrit dans {options.vers} — {fichiers} fichiers", file=sys.stderr)
    for nom, octets in tailles.items():
        print(f"   {octets:>10,} o   {nom}", file=sys.stderr)
    print(f"   {sum(tailles.values()):>10,} o   au total", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
