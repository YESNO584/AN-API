"""Qui a déposé un texte, et son groupe quand on le connaît — une règle, partagée par le calendrier et les cartes des travaux.
"""
from __future__ import annotations

import sqlite3


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
