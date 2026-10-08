"""Les versions successives d'un texte et ce qui change de l'une à l'autre — et depuis le dépôt.
"""
from __future__ import annotations

import sqlite3
import sys
import legi
import recuperer_textes
import textes as textes_mod
from publication.amendements import amendements_adoptes, debats_par_amendement, votes_par_amendement
from publication.commun import RACINE


# Les trois formes qu'une version prend, et le nom qu'on leur donne à l'écran.
# **Ces trois libellés sont de nous** : la source nomme le document
# « Proposition de loi » à chaque étape, ce qui ne distinguerait pas les
# versions entre elles. Voir `../docs/CE-QUE-L-ON-ECRIT.md`.
NOM_DE_VERSION = (("BTC", "Texte de la commission"),
                  ("BTA", "Texte adopté par l'Assemblée"),
                  ("B", "Texte déposé"))


# Qui a amendé le texte pour produire cette version. C'est la **forme du
# document** qui le dit, et elle seule : un texte de commission sort d'une
# commission, un texte adopté sort d'une séance.
QUI_A_AMENDE = (("BTC", "en commission"), ("BTA", "en séance"))


def nom_de_version(ref: str) -> str:
    sans_numero = ref.rstrip("0123456789")
    for forme, nom in NOM_DE_VERSION:
        if sans_numero.endswith(forme):
            return nom
    return "Texte"


def qui_a_amende(ref: str) -> str:
    """« en commission » ou « en séance », d'après la version produite."""
    sans_numero = ref.rstrip("0123456789")
    for forme, quand in QUI_A_AMENDE:
        if sans_numero.endswith(forme):
            return quand
    return "en cours de parcours"


def ouvrir_textes() -> sqlite3.Connection | None:
    """La base du texte des versions, si la lecture a déjà tourné.

    Facultative, comme le droit consolidé : sans elle, les fiches se publient
    sans leurs versions, et l'application le dit plutôt que de laisser croire
    qu'un texte n'en a qu'une.
    """
    chemin = RACINE / "textes.db"
    if not chemin.exists():
        print("Pas de textes.db : les versions des textes ne seront pas publiées.",
              file=sys.stderr)
        return None
    cx = sqlite3.connect(f"file:{chemin}?mode=ro", uri=True)
    cx.row_factory = sqlite3.Row
    return cx


def versions_du_texte(cx: sqlite3.Connection, textes_cx: sqlite3.Connection | None,
                      parcours: list[dict]) -> list[dict]:
    """Les versions successives d'un texte, dans l'ordre du parcours.

    Chacune porte l'étape qui l'a produite — c'est la source qui les relie,
    par `texteAssocie` et `texteAdopte` — et le compte de ce qui a changé
    depuis la précédente. Une version dont le texte n'a pas encore été lu
    n'est pas publiée : l'écran n'affiche que ce qui existe.
    """
    if textes_cx is None:
        return []
    suite = []
    for etape in parcours:
        details = etape.get("details") or {}
        for cle in ("texteAssocie", "texteAdopte"):
            ref = (details.get(cle) or {}).get("ref")
            if not ref or not recuperer_textes.est_une_version(ref):
                continue
            if any(v["ref"] == ref for v in suite):
                continue
            articles = recuperer_textes.articles_du_document(textes_cx, ref)
            if not articles:
                continue
            suite.append({"ref": ref, "nom": nom_de_version(ref), "date": etape["date"],
                          "etape": etape["code"], "articles": articles})
    return suite


def comparaison_d_une_etape(cx: sqlite3.Connection, suite: list[dict], rang: int,
                            votes: dict, debats: dict, etapes: list[dict]) -> dict:
    """Cette version comparée à la précédente — et la trace de l'étape, pour
    le parcours entier, ajoutée à `etapes` au passage."""
    version = suite[rang]
    avant = suite[rang - 1] if rang else None
    lignes = (textes_mod.comparer(avant["articles"], version["articles"])
              if avant else textes_mod.premiere_version(version["articles"]))
    # Les amendements sont déposés sur la version **précédente** : ce sont
    # eux qui l'ont transformée en celle-ci.
    # La fenêtre pendant laquelle ce document-là a été amendé : de son
    # adoption à celle de la version qui en est sortie.
    index = (amendements_adoptes(cx, avant["ref"], votes, debats,
                                 (avant["date"], version["date"]))
             if avant else {})
    if avant:
        etapes.append({"quand": qui_a_amende(version["ref"]), "index": index,
                       "date": version["date"]})
    for ligne in lignes:
        ligne["amendements"] = textes_mod.amendements_de_l_article(index, ligne)
    return {
        "ref": version["ref"], "nom": version["nom"], "date": version["date"],
        "etape": version["etape"],
        "precedent": ({"ref": avant["ref"], "nom": avant["nom"], "date": avant["date"]}
                      if avant else None),
        "resume": textes_mod.resume(lignes),
        "articles": lignes,
    }


def comparaison_du_parcours(suite: list[dict], etapes: list[dict]) -> dict:
    """Le texte déposé comparé au texte à jour — la question qu'on se pose
    en ouvrant une fiche."""
    depose, jour = suite[0], suite[-1]
    # **Le texte à jour n'est pas celui du dernier document.** Une version
    # tardive ne réimprime pas les articles déjà accordés : elle écrit
    # « (Conforme) ». Voir `textes.version_a_jour`.
    articles_a_jour = textes_mod.version_a_jour([v["articles"] for v in suite])
    lignes = textes_mod.comparer(depose["articles"], articles_a_jour)
    for ligne in lignes:
        ligne["amendements"] = textes_mod.amendements_du_parcours(etapes, ligne)
    parcours = {
        "ref": jour["ref"], "nom": jour["nom"], "date": jour["date"],
        "etape": jour["etape"],
        "precedent": {"ref": depose["ref"], "nom": depose["nom"],
                      "date": depose["date"]},
        "etapes": [{"quand": e["quand"], "date": e["date"]} for e in etapes],
        "resume": textes_mod.resume(lignes),
        "articles": lignes,
    }
    return parcours


def comparaison_des_versions(cx: sqlite3.Connection, suite: list[dict],
                             dossier_uid: str,
                             votes: dict[str, list[dict]] | None = None,
                             debats: dict[tuple, dict] | None = None,
                             ) -> tuple[list[dict], dict | None]:
    """Chaque version comparée à la précédente, **et** le parcours entier.

    Deux comparaisons, et elles ne répondent pas à la même question. Celle
    d'une étape dit ce que cette réunion-là a changé ; celle du parcours dit ce
    que le texte déposé est devenu — ce qu'on veut savoir quand on ouvre une
    fiche. Le premier écran de la maquette montrait la dernière étape, qui pour
    une loi arrivée au bout est la commission mixte paritaire : 4 amendements
    sur la loi Ripost, quand le texte en a vu 245 adoptés depuis son dépôt.

    La seconde est `None` quand le texte n'a qu'une version : il n'y a alors
    aucun parcours à raconter. Dès deux versions elle existe, même quand elle
    ressemble à l'unique étape — elle porte en plus le **texte à jour** des
    articles que la dernière version ne réimprime pas.

    `votes` et `debats` sont cherchés une fois par texte ; l'appelant les
    passe quand il s'en sert aussi pour la fiche des amendements.
    """
    votes = votes or votes_par_amendement(cx, dossier_uid)
    debats = debats if debats is not None else debats_par_amendement(cx, dossier_uid)
    etapes: list[dict] = []
    sortie = [comparaison_d_une_etape(cx, suite, rang, votes, debats, etapes)
              for rang in range(len(suite))]
    if len(suite) < 2:
        return sortie, None
    return sortie, comparaison_du_parcours(suite, etapes)


def articles_de_pure_forme(legi_cx: sqlite3.Connection | None) -> set[str]:
    """Les articles dont **rien du fond** n'a bougé : une virgule, une espace.

    Ils sortent du compte des articles modifiés — les annoncer comme modifiés
    ferait dire à l'application qu'une loi a changé quelque chose là où elle
    n'a rien changé. Ils ne disparaissent pas pour autant : l'écran les range
    à part, sous « articles retouchés sans changement de fond ».

    Mesuré le 2026-09-02 : 5 articles sur 4 431 comparables (0,1 %). Rare,
    mais chacun est un article qu'on annonçait modifié à tort.
    """
    if legi_cx is None:
        return set()
    forme_seule = set()
    for ligne in legi_cx.execute(
            "SELECT r.id, r.texte,"
            " (SELECT texte FROM redaction WHERE id = r.precedent) avant"
            " FROM redaction r"
            " WHERE EXISTS (SELECT 1 FROM changement c WHERE c.redaction_id = r.id)"
            "   AND r.precedent IS NOT NULL"):
        if not ligne["avant"]:
            continue
        decoupe = legi.morceaux(ligne["avant"], ligne["texte"] or "")
        change = [m for m in decoupe if m["role"] != "egal"]
        if change and not legi.changement_de_fond(decoupe):
            forme_seule.add(ligne["id"])
    return forme_seule
