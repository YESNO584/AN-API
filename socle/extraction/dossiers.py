"""Un dossier législatif tel que publié → un dossier tel que la base le range : ses étapes, son statut, et ce que le Sénat en dit. Ce que chaque acte dit de lui-même est dans `actes`.
"""
from __future__ import annotations

import csv
import pathlib
import re
from typing import Iterable, Iterator
from extraction.archives import _lire
from extraction.sources import LEGISLATURE, PREFIXE_DOSSIER_AN
from extraction.actes import aplatir, chambre_du_code, details_acte, fusionner_actes, libelle, numero_etape, precision_acte


# Seuls ces types de dossier fabriquent une loi. Les autres — résolutions,
# rapports d'information, missions, commissions d'enquête, allocutions — sont
# des travaux de l'Assemblée qui n'aboutissent à aucun texte : 708 dossiers sur
# 2 859 le 2026-08-31. La base les garde, marqués `est_loi = 0`, pour que le
# chiffre reste vérifiable ; c'est à l'affichage de les écarter.
TYPES_DE_LOI = frozenset({
    "Proposition de loi ordinaire",
    "Projet de loi ordinaire",
    "Projet ou proposition de loi constitutionnelle",
    "Projet ou proposition de loi organique",
    "Projet de ratification des traités et conventions",
    "Projet de loi de finances de l'année",
    "Projet de loi de finances rectificative",
    "Projet de loi de financement de la sécurité sociale",
    "Projet de loi relative aux résultats de la gestion et portant approbation des comptes",
    "Proposition de loi présentée en application de l'article 11 de la Constitution",
})


# Les six étapes du parcours, §3.1 du plan.
ETAPES = (
    (1, "Dépôt",
     "Le texte est déposé et renvoyé à une commission, mais personne ne l'a "
     "encore examiné. C'est de loin le cas le plus fréquent : la plupart des "
     "propositions de loi n'iront jamais plus loin."),
    (2, "Commission",
     "Une commission l'examine et l'amende."),
    (3, "Séance publique",
     "La chambre en débat et vote sur l'ensemble."),
    (4, "Navette",
     "Le texte est parti à l'autre chambre, qui recommence tout."),
    (5, "Sortie de navette",
     "Commission mixte paritaire, ou dernier mot à l'Assemblée."),
    (6, "Après le vote",
     "Contrôle du Conseil constitutionnel avant promulgation."),
)


EN_COURS, PROMULGUE, RETIRE, SANS_ACTE, REJETE, NON_ADOPTE, CADUC = (
    "en_cours", "promulgue", "retire", "sans_acte", "rejete", "non_adopte", "caduc")


# Ce que le Sénat écrit dans « État du dossier », et ce que nous en faisons.
# On ne traduit pas, on ne déduit pas : ces mots sont les siens.
FINS_SENAT = {
    "non adopté": NON_ADOPTE,
    "caduc": CADUC,
    "retiré": RETIRE,
    "Non conforme à la constitution": NON_ADOPTE,
}


def statut_final(statut: str, etat_senat: str | None) -> str:
    """Le Sénat peut savoir qu'un texte est fini quand l'Assemblée l'ignore.

    29 textes que l'Assemblée laisse en cours sont dits « non adopté »,
    « retiré » ou « caduc » par le Sénat (mesuré le 2026-08-31). Son avis ne
    prime que pour annoncer une fin : une promulgation ou un retrait déjà
    constatés côté Assemblée ne se discutent pas.
    """
    if statut in (PROMULGUE, RETIRE):
        return statut
    return FINS_SENAT.get((etat_senat or "").strip(), statut)


def etapes_du_dossier(actes: list[dict], aujourdhui: str, chambre_initiale: str | None,
                      reunions: dict[str, dict] | None, organes: dict[str, dict] | None,
                      documents: dict[str, dict] | None, acteurs: dict[str, dict] | None
                      ) -> list[dict]:
    """Chaque acte daté du dossier, placé sur l'échelle des six étapes et
    rangé dans l'ordre où il a eu lieu."""
    # Le fichier contient des séances déjà programmées : leurs dates sont dans
    # le futur. Un texte ne doit pas être classé sur une étape qui n'a pas eu
    # lieu — on garde les deux, en les distinguant.
    # `rang` est la position de l'acte dans le fichier source. Ce n'est pas un
    # détail : l'Assemblée range les lectures dans l'ordre où elles ont eu
    # lieu (par exemple `SN1, AN1, SN2` pour un texte parti du Sénat). C'est
    # le seul moyen de départager deux actes du même jour à la même étape —
    # une décision à l'Assemblée et le dépôt au Sénat qui suit le même jour.
    etapes = []
    for rang, acte in enumerate(actes):
        date = (acte.get("dateActe") or "")[:10]
        if not date:
            continue
        code = acte.get("codeActe") or ""
        sommet = code.partition("-")[0]
        englobante = next((a for a in actes if (a.get("codeActe") or "") == sommet), None)
        conclusion = acte.get("statutConclusion")
        etapes.append({
            "uid": acte.get("uid"),
            "code": code,
            "lecture": libelle(englobante, court=True) if englobante else "",
            "libelle": libelle(acte),
            "chambre": chambre_du_code(code),
            "date": date,
            "rang": rang,
            "numero": numero_etape(code, chambre_initiale),
            "conclusion": conclusion.get("libelle") if isinstance(conclusion, dict) else None,
            "future": date > aujourdhui,
            "precision": precision_acte(acte, reunions),
            "details": details_acte(acte, organes, documents, acteurs),
        })
    etapes.sort(key=lambda e: (e["date"], e["rang"]))
    return fusionner_actes(etapes)


def statut_des_actes(actes: list[dict], passees: list[dict],
                     promulgation: dict | None) -> str:
    """Où en est le texte, d'après ses actes : promulgué, retiré, rejeté, en
    cours — ou sans aucun acte passé."""
    retrait = any((a.get("codeActe") or "").endswith("RTRINI") for a in actes)
    if promulgation is not None:
        return PROMULGUE
    if retrait:
        return RETIRE
    if not passees:
        return SANS_ACTE
    if est_rejete(passees):
        return REJETE
    return EN_COURS


def acte_le_plus_avance(passees: list[dict]) -> dict | None:
    """Où en est le texte : l'acte le plus avancé du jour le plus récent.

    Deux pièges obligent à cette formulation. D'abord, plusieurs actes
    portent la même date : entre eux, on retient le plus avancé, puis le
    dernier publié (voir `rang` dans `etapes_du_dossier`). Ensuite, le
    parcours n'est pas une ligne droite — après une commission mixte
    paritaire qui échoue, le texte repart en nouvelle lecture. Prendre
    « l'étape la plus avancée jamais atteinte » le laisserait affiché en
    sortie de navette alors qu'il est reparti chez l'autre chambre.
    """
    if not passees:
        return None
    dernier_jour = passees[-1]["date"]
    return max((e for e in passees if e["date"] == dernier_jour),
               key=lambda e: (e["numero"], e["rang"]))


def analyser(brut: dict, aujourdhui: str, etats_senat: dict[str, str] | None = None,
             reunions: dict[str, dict] | None = None,
             organes: dict[str, dict] | None = None,
             documents: dict[str, dict] | None = None,
             acteurs: dict[str, dict] | None = None) -> dict:
    """Un dossier tel que publié → un dossier tel que la base le range.

    Rend toujours un résultat, même pour un dossier qui ne fabrique pas de loi
    ou déjà promulgué : c'est `statut` et `est_loi` qui le disent. Trier est
    le travail de l'affichage, pas celui du socle.
    """
    dossier = brut["dossierParlementaire"]
    titres = dossier.get("titreDossier") or {}
    procedure = (dossier.get("procedureParlementaire") or {}).get("libelle") or ""
    actes = aplatir(dossier.get("actesLegislatifs") or {})

    depots = [a for a in actes if a.get("@xsi:type") == "DepotInitiative_Type"]
    chambre_initiale = (
        chambre_du_code((depots[0].get("codeActe") or "").partition("-")[0])
        if depots else None
    )

    etapes = etapes_du_dossier(actes, aujourdhui, chambre_initiale,
                               reunions, organes, documents, acteurs)

    passees = [e for e in etapes if not e["future"]]
    promulgation = next((a for a in actes if (a.get("codeActe") or "") == "PROM-PUB"), None)
    statut = statut_des_actes(actes, passees, promulgation)
    acte_courant = acte_le_plus_avance(passees)
    date_mouvement = passees[-1]["date"] if passees else None

    info_jo = (promulgation or {}).get("infoJO") or {}
    chemin_senat = titres.get("senatChemin")
    chemin_an = titres.get("titreChemin")

    etat_senat = (etats_senat or {}).get(cle_senat(chemin_senat))
    statut = statut_final(statut, etat_senat)

    return {
        "uid": dossier.get("uid"),
        "legislature": dossier.get("legislature"),
        "titre": (titres.get("titre") or "").strip(),
        "titreChemin": chemin_an,
        "type": procedure,
        "estLoi": procedure in TYPES_DE_LOI,
        "chambreInitiale": chambre_initiale,
        "statut": statut,
        "etatSenat": etat_senat,
        "etape": acte_courant["numero"] if acte_courant else None,
        "etapeCourante": acte_courant,
        "dateDernierMouvement": date_mouvement,
        "urlAN": PREFIXE_DOSSIER_AN + chemin_an if chemin_an else None,
        "urlSenat": chemin_senat if chemin_senat and chemin_senat != "None" else None,
        "loiNumero": (promulgation or {}).get("codeLoi"),
        "loiDate": ((promulgation or {}).get("dateActe") or "")[:10] or None,
        "loiUrlJO": info_jo.get("urlLegifrance"),
        "etapes": etapes,
    }


def est_rejete(passees: list[dict]) -> bool:
    """Le dernier acte connu du texte est-il un rejet ?

    Nuance importante : un rejet n'est pas une fin. Sur les 27 textes de la
    législature ayant connu un rejet, **19 ont continué leur parcours**
    (mesuré le 2026-08-31). On ne retient donc que ceux dont plus rien n'a
    suivi — et même là, on ne dit pas que c'est terminé, seulement que la
    dernière décision connue est un rejet.
    """
    if not passees:
        return False
    dernier_jour = passees[-1]["date"]
    return any(e["conclusion"] and "rejet" in e["conclusion"].lower()
               for e in passees if e["date"] == dernier_jour)


def lire_senat(chemin: pathlib.Path) -> dict[str, str]:
    """L'état de chaque dossier selon le Sénat : adresse → « État du dossier ».

    Le Sénat dit ce que l'Assemblée ne dit pas — qu'un texte est « non
    adopté », « caduc » ou « retiré ». C'est son propre vocabulaire, repris
    tel quel.

    Deux pièges vérifiés : le fichier est en **latin-1**, pas en UTF-8 ; et
    l'adresse existe sous deux formes, `/dossier-legislatif/` et l'ancienne
    `/dossierleg/`, qu'il faut ramener à la même clé.
    """
    etats = {}
    with chemin.open(encoding="latin-1", newline="") as fichier:
        for ligne in csv.DictReader(fichier, delimiter=";"):
            cle = cle_senat(ligne.get("URL du dossier"))
            etat = (ligne.get("État du dossier") or "").strip()
            if cle and etat:
                etats[cle] = etat
    return etats


def cle_senat(url: str | None) -> str | None:
    """« http://www.senat.fr/dossierleg/ppl00-074.html » → « ppl00-074.html »."""
    if not url:
        return None
    reste = re.sub(r"^https?://(www\.)?senat\.fr/dossier-?leg(islatif)?/", "",
                   url.strip(), flags=re.I)
    return reste.lower() or None


def lire_archive(archive: pathlib.Path, legislature: str | None = LEGISLATURE) -> Iterator[dict]:
    """Les dossiers législatifs."""
    for brut in _lire(archive, "dossierParlementaire"):
        if legislature and brut["dossierParlementaire"].get("legislature") != legislature:
            continue
        yield brut


def lire_reunions(archive: pathlib.Path) -> dict[str, dict]:
    """Les réunions et séances : leur heure, et le rang que l'Assemblée leur donne.

    Sert uniquement à départager deux actes du même jour — voir
    `precision_acte`. Mesuré le 2026-08-31 : sur les 382 réunions à
    départager, **382 sont dans cette archive**, toutes avec leur heure de
    début, 369 avec leur quantième.
    """
    reunions = {}
    for brut in _lire(archive, "reunion"):
        r = brut["reunion"]
        reunions[r["uid"]] = {
            "debut": (r.get("timeStampDebut") or "")[:16],
            "quantieme": (r.get("identifiants") or {}).get("quantieme"),
            "lieu": (r.get("lieu") or {}).get("libelleLong"),
        }
    return reunions


def lire_documents(archive: pathlib.Path) -> dict[str, dict]:
    """Les documents parlementaires : de quoi décrire un texte et le signer.

    `notice.formule` est la description du texte en une phrase — « visant à
    instaurer un dispositif de sanction contraventionnelle pour… ». 7 029 des
    7 070 documents en ont une.
    """
    documents = {}
    for brut in _lire(archive, "document"):
        d = brut["document"]
        auteurs, cosignataires = [], []
        liste = (d.get("auteurs") or {}).get("auteur")
        if isinstance(liste, dict):
            liste = [liste]
        for x in liste or []:
            acteur = x.get("acteur") or {}
            ref, qualite = acteur.get("acteurRef"), acteur.get("qualite")
            if not ref:
                continue
            (cosignataires if qualite == "cosignataire" else auteurs).append(
                {"ref": ref, "qualite": qualite})
        cosign = (d.get("coSignataires") or {}).get("coSignataire")
        if isinstance(cosign, dict):
            cosign = [cosign]
        for x in cosign or []:
            ref = ((x.get("acteur") or {}).get("acteurRef")
                   if isinstance(x.get("acteur"), dict) else None)
            if ref:
                cosignataires.append({"ref": ref, "qualite": "cosignataire"})

        documents[d["uid"]] = {
            "uid": d["uid"],
            "type": d.get("denominationStructurelle"),
            "numero": (d.get("notice") or {}).get("numNotice"),
            "titre": (d.get("titres") or {}).get("titrePrincipal"),
            "description": (d.get("notice") or {}).get("formule"),
            "dossier": d.get("dossierRef"),
            "auteurs": auteurs,
            "cosignataires": cosignataires,
        }
    return documents
