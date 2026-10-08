"""Les moments où le Parlement se réunit et décide, rangés par mois.
"""
from __future__ import annotations

import sqlite3
import affichage
from publication.auteurs import auteurs_des_textes
from publication.commun import ecrire
from publication.contexte import Publication


def votes_qui_decident(cx: sqlite3.Connection) -> dict[tuple[str, str], dict]:
    """Les votes sur l'ensemble, indexés par (texte, date) : une décision les
    récupère pour afficher le résultat chiffré sur la même ligne."""
    votes: dict[tuple[str, str], dict] = {}
    trous = ",".join("?" * len(affichage.VOTES_AU_CALENDRIER))
    for l in cx.execute(
            f"SELECT dossier_uid, date, sort, pour, contre, abstentions, portee, objet"
            f" FROM vote WHERE dossier_uid IS NOT NULL AND portee IN ({trous})"
            " ORDER BY date", tuple(affichage.VOTES_AU_CALENDRIER)):
        votes[(l["dossier_uid"], l["date"])] = {
            "sort": l["sort"], "pour": l["pour"], "contre": l["contre"],
            "abstentions": l["abstentions"], "portee": l["portee"],
        }
    return votes


def points_d_agenda(cx: sqlite3.Connection) -> list[dict]:
    """Les questions au Gouvernement, les débats et les votes solennels, tels
    que l'agenda les publie. Absents d'une base construite avant eux."""
    colonnes = {c[1] for c in cx.execute("PRAGMA table_info(point_agenda)")}
    if not colonnes:
        return []
    dossier = "dossier" if "dossier" in colonnes else "NULL"
    points = []
    for l in cx.execute(f"SELECT date, heure, genre, objet, {dossier} dossier"
                        " FROM point_agenda ORDER BY date, heure"):
        e = {"date": l["date"], "genre": l["genre"], "quoi": l["objet"],
             "chambre": "assemblee"}
        if l["heure"]:
            e["heure"] = l["heure"]
        if l["dossier"]:
            e["texte"] = l["dossier"]
        points.append(e)
    return points


def ajouter_les_points(par_mois: dict, points: list[dict]) -> None:
    """Les points d'agenda au calendrier. **Un vote solennel déjà passé ne
    s'ajoute pas** quand la décision ou le scrutin du même jour est déjà là pour
    le même texte, avec son résultat chiffré : l'annonce ferait doublon. Il ne
    reste donc, en pratique, que les votes à venir et ceux dont le résultat
    n'est pas enregistré."""
    decides = {(e["texte"], e["date"]) for mois in par_mois.values() for e in mois
               if e.get("texte") and e["genre"] in ("decision", "vote")}
    for e in points:
        if e["genre"] == "vote_solennel" and (e.get("texte"), e["date"]) in decides:
            continue
        par_mois.setdefault(e["date"][:7], []).append(e)


def evenement_de_l_etape(l, genre: str, votes: dict) -> dict:
    """Une ligne du calendrier, avec son vote quand c'est une décision."""
    evenement = {
        "date": l["date"], "genre": genre, "texte": l["dossier_uid"],
        "quoi": l["libelle"], "chambre": l["chambre"],
    }
    for champ, valeur in (("heure", l["precision"]), ("lecture", l["lecture"]),
                          ("conclusion", l["conclusion"])):
        if valeur:
            evenement[champ] = valeur
    vote = votes.get((l["dossier_uid"], l["date"]))
    if vote and genre == "decision":
        evenement["vote"] = vote
    return evenement


def signer(par_mois: dict, auteurs: dict) -> None:
    """Chaque ligne qui porte un texte reçoit son auteur, quand on le connaît."""
    for mois in par_mois.values():
        for e in mois:
            if e.get("texte") in auteurs:
                e["auteur"] = auteurs[e["texte"]]


def votes_sans_decision(par_mois: dict, votes: dict) -> None:
    """Les votes qui décident sans qu'une « décision » soit enregistrée le
    même jour : sans eux, un scrutin public disparaîtrait du calendrier."""
    dates_vues = {(e["texte"], e["date"]) for mois in par_mois.values() for e in mois}
    for (uid, date), vote in votes.items():
        if (uid, date) in dates_vues:
            continue
        par_mois.setdefault(date[:7], []).append({
            "date": date, "genre": "vote", "texte": uid, "vote": vote,
            "quoi": "Scrutin public", "chambre": None,
        })


def calendrier(cx: sqlite3.Connection) -> dict[str, list[dict]]:
    """Les moments où le Parlement se réunit et décide, rangés par mois.

    Un mois par fichier : le calendrier n'affiche qu'un mois à la fois, et
    charger deux ans d'un coup pour en montrer trente jours serait absurde.

    Chaque événement porte l'identifiant de son texte, jamais son titre : la
    liste des textes est déjà chargée par l'application, qui sait donc le
    retrouver toute seule.
    """
    par_mois: dict[str, list[dict]] = {}
    votes = votes_qui_decident(cx)

    vus: set[tuple] = set()
    trous = ",".join("?" * len(affichage.RESOLUTIONS))
    for l in cx.execute(
            "SELECT e.dossier_uid, e.code, e.date, e.libelle, e.chambre, e.lecture,"
            " e.conclusion, e.precision"
            " FROM etape e JOIN dossier d ON d.uid = e.dossier_uid"
            f" WHERE (d.est_loi = 1 OR d.type IN ({trous}))"
            " AND e.date IS NOT NULL AND e.date != ''"
            " ORDER BY e.date, e.rang", tuple(affichage.RESOLUTIONS)):
        genre = affichage.genre_d_evenement(l["code"])
        if not genre:
            continue
        # Deux actes du même jour, au même endroit, pour le même texte, ne font
        # qu'une ligne : le calendrier n'est pas le parcours détaillé.
        cle = (l["dossier_uid"], l["date"], genre, l["precision"])
        if cle in vus:
            continue
        vus.add(cle)
        par_mois.setdefault(l["date"][:7], []).append(
            evenement_de_l_etape(l, genre, votes))

    votes_sans_decision(par_mois, votes)
    ajouter_les_points(par_mois, points_d_agenda(cx))
    signer(par_mois, auteurs_des_textes(cx))
    for mois in par_mois.values():
        mois.sort(key=lambda e: (e["date"], e.get("heure") or "", e["genre"]))
    return par_mois


def ecrire_calendrier(p: Publication) -> None:
    """Un fichier par mois, et un index qui dit lesquels existent."""
    cx, sortie, genere_le, tailles = p.cx, p.sortie, p.genere_le, p.tailles
    # Le calendrier : un fichier par mois, plus un index qui dit lesquels
    # existent. Le calendrier n'affiche qu'un mois à la fois ; charger deux ans
    # pour en montrer trente jours serait absurde.
    mois = calendrier(cx)
    if mois:
        octets = 0
        for nom, evenements in mois.items():
            octets += ecrire(sortie / "calendrier" / f"{nom}.json",
                             {"genereLe": genere_le, "mois": nom,
                              "total": len(evenements), "evenements": evenements})
        tailles["calendrier/*.json"] = octets
        genres = {}
        for evenements in mois.values():
            for e in evenements:
                genres[e["genre"]] = genres.get(e["genre"], 0) + 1
        tailles["calendrier.json"] = ecrire(sortie / "calendrier.json", {
            "genereLe": genere_le,
            "total": sum(len(e) for e in mois.values()),
            "genres": genres,
            # Les mois qui portent quelque chose, et combien : le calendrier
            # sait ainsi où il peut aller et ce qu'il y trouvera.
            "mois": [{"mois": nom, "evenements": len(evenements)}
                     for nom, evenements in sorted(mois.items())],
        })
