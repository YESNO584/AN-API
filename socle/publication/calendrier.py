"""Les moments où le Parlement se réunit et décide, rangés par mois.
"""
from __future__ import annotations

import sqlite3
import affichage
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


def auteur_du_texte(l) -> dict | None:
    """Qui a déposé le texte, et son groupe quand on le connaît.

    **Un projet de loi est celui du Gouvernement**, même quand le Premier
    ministre qui le signe siège aujourd'hui à l'Assemblée : 15 projets ont un
    signataire qui a un groupe (13 de Michel Barnier, DR ; 2 de Gabriel Attal,
    EPR), et ce groupe ne les a pas déposés. Le type du document tranche, pas
    celui du dossier — « Projet ou proposition de loi organique » ne dit pas
    lequel des deux.

    Le groupe est celui de l'auteur **aujourd'hui** : la source ne garde pas
    celui du jour du dépôt. Un sénateur, un ancien député, un député sans
    groupe a son nom sans groupe — rien n'est rapproché par le nom.
    """
    projet = l["type_document"] or ("Projet de loi" if (l["type"] or "").startswith(
        "Projet de loi") else "")
    if projet.startswith("Projet de loi"):
        return {"gouvernement": True}
    if not l["nom"]:
        return None
    auteur = {"nom": " ".join(x for x in (l["prenom"], l["nom"]) if x)}
    if l["sigle"]:
        auteur.update(sigle=l["sigle"], groupe=l["nom_groupe"], couleur=l["couleur"])
    return auteur


def auteurs_des_textes(cx: sqlite3.Connection) -> dict[str, dict]:
    """L'auteur de chaque texte qui peut paraître au calendrier."""
    auteurs = {}
    for l in cx.execute(
            "SELECT d.uid, d.type, d.type_document, a.prenom, a.nom,"
            " g.sigle, g.nom nom_groupe, g.couleur"
            " FROM dossier d LEFT JOIN acteur a ON a.ref = d.auteur_ref"
            " LEFT JOIN groupe g ON g.ref = a.groupe_ref"):
        auteur = auteur_du_texte(l)
        if auteur:
            auteurs[l["uid"]] = auteur
    return auteurs


def points_d_agenda(cx: sqlite3.Connection) -> list[dict]:
    """Les questions au Gouvernement et les débats : des moments de séance
    qu'aucun texte ne porte. Absents d'une base construite avant eux."""
    if not cx.execute("SELECT 1 FROM sqlite_master WHERE name = 'point_agenda'").fetchone():
        return []
    return [{"date": l["date"], "genre": l["genre"], "quoi": l["objet"],
             "chambre": "assemblee", **({"heure": l["heure"]} if l["heure"] else {})}
            for l in cx.execute(
                "SELECT date, heure, genre, objet FROM point_agenda ORDER BY date, heure")]


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
    signer(par_mois, auteurs_des_textes(cx))
    for e in points_d_agenda(cx):
        par_mois.setdefault(e["date"][:7], []).append(e)
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
