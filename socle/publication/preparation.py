"""Ce que plusieurs étapes vont relire, lu une seule fois.

C'est le seul module du paquet qui connaisse les autres : il appelle les
lecteurs de chacun pour remplir le contexte, et c'est tout.
"""
from __future__ import annotations

import datetime as dt
import pathlib
import sqlite3

from publication.debats import lire_descriptions
from publication.debats import lire_resumes_debats
from publication.listes import resume_votes
from publication.loi import changements_par_loi
from publication.loi import ouvrir_legi
from publication.senat import ouvrir_senat
from publication.senat import themes_par_texte
from publication.senat import votes_du_senat
from publication.versions import articles_de_pure_forme
import affichage
import extraction
import senat as senat_mod
from publication.contexte import Publication


def preparer(cx: sqlite3.Connection, sortie: pathlib.Path) -> Publication:
    """Lit une fois ce que plusieurs étapes vont relire."""
    genere_le = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    votes = resume_votes(cx)
    descriptions = lire_descriptions()
    resumes_debats = lire_resumes_debats()
    legi_cx = ouvrir_legi()
    # Les articles dont seule la ponctuation a bougé : repérés une fois, puis
    # écartés des comptes et rangés à part.
    forme_seule = articles_de_pure_forme(legi_cx)
    change = changements_par_loi(legi_cx, forme_seule)
    # Où chaque texte en est **au Sénat**, selon les étapes que le Sénat
    # nomme lui-même. C'est ce qui range le fil de l'onglet « Sénat ». On
    # garde la **dernière** étape, celle qui dit où le texte en est — et sa
    # lecture, qui s'affiche à part parce qu'elle ne fait pas une colonne.
    # Le pont avec la base du Sénat : une seule colonne, publiée des deux
    # côtés. 730 de nos 731 textes passés au Sénat s'y retrouvent.
    senat_cx = ouvrir_senat()
    signets, titres = {}, {}
    for l in cx.execute("SELECT uid, titre, url_senat FROM dossier"
                        " WHERE est_loi = 1 AND url_senat IS NOT NULL"):
        sig = senat_mod.signet_de(l["url_senat"])
        if sig:
            signets[sig] = l["uid"]
            titres[l["uid"]] = l["titre"]
    votes_senat = votes_du_senat(senat_cx, signets)
    themes = themes_par_texte(senat_cx, signets)

    etape_senat = {}
    en_cours_au_senat = {l["uid"] for l in cx.execute(
        "SELECT uid FROM dossier WHERE est_loi = 1 AND statut = ?",
        (extraction.EN_COURS,))}
    for l in cx.execute(
            "SELECT dossier_uid, code, libelle, lecture, date, conclusion"
            " FROM etape WHERE chambre = 'senat' ORDER BY date, rang"):
        moment = affichage.moment_au_senat(l["code"])
        if not moment:
            continue
        etape_senat[l["dossier_uid"]] = {
            "moment": moment, "code": l["code"], "libelle": l["libelle"],
            "lecture": l["lecture"], "date": l["date"],
            "conclusion": l["conclusion"],
        }

    compte_amendements = {l["dossier_uid"]: l["n"] for l in cx.execute(
        "SELECT dossier_uid, COUNT(*) n FROM amendement GROUP BY dossier_uid")}
    # Combien de prises de parole par texte, pour que la carte du fil puisse
    # annoncer la rubrique sans charger le fichier.
    compte_paroles = {l["dossier_uid"]: l["n"] for l in cx.execute(
        "SELECT dossier_uid, COUNT(*) n FROM parole GROUP BY dossier_uid")}

    comptes = {l["statut"]: l["n"] for l in cx.execute(
        "SELECT statut, COUNT(*) n FROM dossier WHERE est_loi = 1 GROUP BY statut")}
    par_etape = {l["etape"]: l["n"] for l in cx.execute(
        "SELECT etape, COUNT(*) n FROM dossier"
        " WHERE statut='en_cours' AND est_loi=1 AND etape IS NOT NULL GROUP BY etape")}
    return Publication(
        cx=cx, sortie=sortie, genere_le=genere_le, tailles={},
        votes=votes, descriptions=descriptions, resumes_debats=resumes_debats,
        legi_cx=legi_cx, forme_seule=forme_seule, change=change,
        senat_cx=senat_cx, signets=signets, titres=titres,
        votes_senat=votes_senat, themes=themes, etape_senat=etape_senat,
        en_cours_au_senat=en_cours_au_senat,
        compte_amendements=compte_amendements, compte_paroles=compte_paroles,
        comptes=comptes, par_etape=par_etape)
