"""Un scrutin public tel que publié → un scrutin tel que la base le range : sur quoi il porte, qui a voté quoi.
"""
from __future__ import annotations

import json
import pathlib
import zipfile
from typing import Iterable, Iterator
from extraction.dossiers import aplatir, libelle


def lire_scrutins(archive: pathlib.Path) -> Iterator[dict]:
    """Les scrutins publics."""
    with zipfile.ZipFile(archive) as zf:
        for nom in zf.namelist():
            if not nom.endswith(".json"):
                continue
            with zf.open(nom) as fichier:
                yield json.load(fichier)


# Sur quoi porte le vote. La distinction n'est pas cosmétique : 7 216 des
# 8 434 scrutins de la législature portent sur un amendement, et 212 seulement
# sur un texte entier. Les confondre donnerait à croire qu'un texte a été
# « adopté » alors qu'un seul de ses amendements l'a été.
ENSEMBLE, ARTICLE, AMENDEMENT, MOTION, AUTRE = (
    "ensemble", "article", "amendement", "motion", "autre")


PORTEES = {
    ENSEMBLE: ("Vote sur le texte entier",
               "La chambre s'est prononcée sur l'ensemble du texte. C'est le vote "
               "qui décide si le texte poursuit son chemin ou s'arrête là."),
    ARTICLE: ("Vote sur un article",
              "La chambre s'est prononcée sur un seul article du texte, pas sur "
              "l'ensemble."),
    AMENDEMENT: ("Vote sur un amendement",
                 "La chambre s'est prononcée sur une modification proposée au texte. "
                 "C'est de loin le cas le plus fréquent : un texte débattu donne lieu "
                 "à des centaines de ces votes."),
    MOTION: ("Vote sur une motion",
             "Un vote de procédure : rejeter le texte avant de l'examiner, le "
             "renvoyer en commission, ou censurer le Gouvernement."),
    AUTRE: ("Autre vote",
            "Un vote qui ne porte ni sur le texte entier, ni sur un article, ni sur "
            "un amendement — une demande de suspension de séance, par exemple."),
}


def classer_portee(libelle: str) -> str:
    """Sur quoi porte un scrutin, d'après la façon dont l'Assemblée l'intitule."""
    debut = (libelle or "").strip().lower()[:60]
    if debut.startswith("l'ensemble"):
        return ENSEMBLE
    if "motion" in debut or "censure" in debut:
        return MOTION
    if "amendement" in debut:
        return AMENDEMENT
    if debut.startswith(("l'article", "les articles", "la première partie",
                         "la deuxième partie", "la seconde partie")):
        return ARTICLE
    return AUTRE


def analyser_scrutin(brut: dict, groupes: dict[str, tuple[str, str]] | None = None) -> dict:
    """Un scrutin tel que publié → un scrutin tel que la base le range."""
    s = brut["scrutin"]
    objet = s.get("objet") or {}
    libelle = (objet.get("libelle") or s.get("titre") or "").strip()

    reference = objet.get("dossierLegislatif")
    dossier = reference.get("dossierRef") if isinstance(reference, dict) else None

    synthese = s.get("syntheseVote") or {}
    decompte = synthese.get("decompte") or {}
    demandeur = s.get("demandeur") or {}

    def entier(valeur):
        try:
            return int(valeur)
        except (TypeError, ValueError):
            return None

    vote = {
        "uid": s["uid"],
        "dossier": dossier,
        "date": (s.get("dateScrutin") or "")[:10],
        "numero": entier(s.get("numero")),
        "type": (s.get("typeVote") or {}).get("libelleTypeVote"),
        "portee": classer_portee(libelle),
        "objet": libelle,
        "sort": (s.get("sort") or {}).get("code"),
        "annonce": (s.get("sort") or {}).get("libelle") or synthese.get("annonce"),
        "demandeur": demandeur.get("texte"),
        "votants": entier(synthese.get("nombreVotants")),
        "requis": entier(synthese.get("nbrSuffragesRequis")),
        "pour": entier(decompte.get("pour")),
        "contre": entier(decompte.get("contre")),
        "abstentions": entier(decompte.get("abstentions")),
        "nonVotants": entier(decompte.get("nonVotants")),
        "groupes": [],
    }

    liste = (((s.get("ventilationVotes") or {}).get("organe") or {})
             .get("groupes") or {}).get("groupe")
    if isinstance(liste, dict):
        liste = [liste]
    for g in liste or []:
        detail = (g.get("vote") or {}).get("decompteVoix") or {}
        sigle, nom = (groupes or {}).get(g.get("organeRef"), (g.get("organeRef"), ""))
        pour = entier(detail.get("pour")) or 0
        contre = entier(detail.get("contre")) or 0
        abstentions = entier(detail.get("abstentions")) or 0
        vote["groupes"].append({
            "ref": g.get("organeRef"),
            "sigle": sigle,
            "nom": nom,
            "membres": entier(g.get("nombreMembresGroupe")),
            "position": position_dominante(pour, contre, abstentions),
            "pour": pour,
            "contre": contre,
            "abstentions": abstentions,
            "nonVotants": entier(detail.get("nonVotants")),
        })
    return vote


def position_dominante(pour: int, contre: int, abstentions: int) -> str | None:
    """Ce qu'a fait la majorité d'un groupe, calculé sur son décompte.

    **La position annoncée par la source n'est pas utilisée**, parce qu'elle
    contredit son propre décompte trop souvent : sur 101 208 positions de
    groupe examinées le 2026-08-31, **3 033 (3 %) sont en désaccord** avec les
    voix qu'elles résument. Un cas réel : un groupe annoncé « pour » dont 2
    membres ont voté pour et 16 contre. L'afficher reviendrait à écrire une
    contrevérité à l'écran, alors que le décompte, lui, ne ment pas.
    """
    compte = {"pour": pour, "contre": contre, "abstention": abstentions}
    maxi = max(compte.values())
    if maxi == 0:
        return None                       # personne n'a voté : rien à dire
    gagnants = [k for k, n in compte.items() if n == maxi]
    return gagnants[0] if len(gagnants) == 1 else "partagé"


def refs_de_vote(dossier: dict) -> set[str]:
    """Les scrutins qu'un dossier cite lui-même.

    Les deux sens du lien sont nécessaires et se complètent : 34 des textes en
    cours sont retrouvés parce que le scrutin nomme son dossier, 68 parce que
    le dossier cite son scrutin, et 71 en réunissant les deux (mesuré le
    2026-08-31). Ne suivre qu'un seul sens en perdrait la moitié.
    """
    refs = set()
    for acte in aplatir(dossier.get("actesLegislatifs") or {}):
        v = acte.get("voteRefs")
        if not v:
            continue
        r = v.get("voteRef")
        refs.update([r] if isinstance(r, str) else (r or []))
    return refs
