"""Lecture de l'open data de l'Assemblée : dossiers législatifs et leurs étapes.

Ce module ne fait que lire et classer. Il ne télécharge rien de sa propre
initiative, n'écrit dans aucune base et n'affiche rien : `recuperer.py` s'en
charge, et `../maquette/preparer_donnees.py` l'utilise aussi.

Le modèle est celui du §3.1 de `../docs/PLAN.md` : **un dossier, des étapes
datées, chacune rattachée à une chambre.** L'Assemblée publie le parcours dans
les deux chambres, y compris les étapes passées au Sénat — il n'y a donc aucun
rapprochement à faire entre les deux sources.

Source : https://data.assemblee-nationale.fr — Licence Ouverte (Etalab).
"""

from __future__ import annotations

import json
import pathlib
import urllib.request
import zipfile
from typing import Iterator

URL_ARCHIVE = (
    "https://data.assemblee-nationale.fr/static/openData/repository/17/loi/"
    "dossiers_legislatifs/Dossiers_Legislatifs.json.zip"
)
LEGISLATURE = "17"
PREFIXE_DOSSIER_AN = "https://www.assemblee-nationale.fr/dyn/17/dossiers/"

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

CHAMBRES = {"AN": "assemblee", "SN": "senat"}

EN_COURS, PROMULGUE, RETIRE, SANS_ACTE = "en_cours", "promulgue", "retire", "sans_acte"


def chambre_du_code(code: str) -> str | None:
    """« AN1-DEBATS-SEANCE » → « assemblee ». None pour CMP, CC, PROM."""
    return CHAMBRES.get(code[:2])


def libelle(acte: dict, court: bool = False) -> str:
    """Le libellé français que l'Assemblée attache elle-même à l'acte.

    `court=True` préfère `libelleCourt` : pour une étape de premier niveau,
    `nomCanonique` vaut « 1ère lecture (1ère assemblée saisie) », dont la
    parenthèse devient fausse quand le texte a commencé au Sénat.
    """
    etiquette = acte.get("libelleActe") or {}
    if court:
        return etiquette.get("libelleCourt") or etiquette.get("nomCanonique") or ""
    return etiquette.get("nomCanonique") or etiquette.get("libelleCourt") or ""


def aplatir(noeud: dict) -> list[dict]:
    """Les actes législatifs forment un arbre ; on en fait une liste."""
    resultat: list[dict] = []
    actes = noeud.get("acteLegislatif")
    if isinstance(actes, dict):
        actes = [actes]
    for acte in actes or []:
        resultat.append(acte)
        if acte.get("actesLegislatifs"):
            resultat += aplatir(acte["actesLegislatifs"])
    return resultat


def numero_etape(code: str, chambre_initiale: str | None) -> int:
    """Où se situe un acte, sur l'échelle des six étapes.

    Le point délicat est la commission. Un texte reçoit une « saisine de la
    commission » (`COM-…-SAISIE`) le jour même de son dépôt : c'est un renvoi
    automatique, pas un examen. Le compter comme « en commission » classerait
    1 815 textes sur 1 990 à cette étape, alors que la commission ne s'est
    jamais réunie sur la quasi-totalité d'entre eux. Il faut donc un acte de
    travail réel — nomination d'un rapporteur, réunion, ou rapport déposé.
    """
    sommet, _, reste = code.partition("-")
    chambre = chambre_du_code(sommet)

    if sommet == "CC":
        return 6
    if sommet in ("CMP", "ANLDEF", "SNLDEF"):
        return 5
    if sommet in ("AN2", "SN2", "AN3", "SN3", "ANNLEC", "SNNLEC"):
        return 4
    # Première lecture, mais chez l'autre chambre : le texte a franchi la
    # première et il est parti en navette.
    if chambre and chambre_initiale and chambre != chambre_initiale:
        return 4
    if reste.startswith("DEBATS"):
        return 3
    if reste.endswith(("NOMIN", "REUNION", "RAPPORT")) or reste == "RAPPORT":
        return 2
    return 1


def analyser(brut: dict, aujourdhui: str) -> dict:
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
        })
    etapes.sort(key=lambda e: (e["date"], e["rang"]))

    passees = [e for e in etapes if not e["future"]]
    promulgation = next((a for a in actes if (a.get("codeActe") or "") == "PROM-PUB"), None)
    retrait = any((a.get("codeActe") or "").endswith("RTRINI") for a in actes)

    if promulgation is not None:
        statut = PROMULGUE
    elif retrait:
        statut = RETIRE
    elif not passees:
        statut = SANS_ACTE
    else:
        statut = EN_COURS

    acte_courant = None
    date_mouvement = None
    if passees:
        # Où en est le texte : l'acte le plus avancé du jour le plus récent.
        #
        # Deux pièges obligent à cette formulation. D'abord, plusieurs actes
        # portent la même date : entre eux, on retient le plus avancé, puis le
        # dernier publié (voir `rang` ci-dessus). Ensuite, le parcours n'est
        # pas une ligne droite — après une commission mixte paritaire qui
        # échoue, le texte repart en nouvelle lecture. Prendre « l'étape la
        # plus avancée jamais atteinte » le laisserait affiché en sortie de
        # navette alors qu'il est reparti chez l'autre chambre.
        date_mouvement = passees[-1]["date"]
        acte_courant = max((e for e in passees if e["date"] == date_mouvement),
                           key=lambda e: (e["numero"], e["rang"]))

    info_jo = (promulgation or {}).get("infoJO") or {}
    chemin_senat = titres.get("senatChemin")
    chemin_an = titres.get("titreChemin")

    return {
        "uid": dossier.get("uid"),
        "legislature": dossier.get("legislature"),
        "titre": (titres.get("titre") or "").strip(),
        "titreChemin": chemin_an,
        "type": procedure,
        "estLoi": procedure in TYPES_DE_LOI,
        "chambreInitiale": chambre_initiale,
        "statut": statut,
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


def lire_archive(archive: pathlib.Path, legislature: str | None = LEGISLATURE) -> Iterator[dict]:
    """Parcourt l'archive et rend les dossiers bruts, sans tout charger en mémoire."""
    with zipfile.ZipFile(archive) as zf:
        for nom in zf.namelist():
            if "/dossierParlementaire/" not in nom or not nom.endswith(".json"):
                continue
            with zf.open(nom) as fichier:
                brut = json.load(fichier)
            if legislature and brut["dossierParlementaire"].get("legislature") != legislature:
                continue
            yield brut


def telecharger(destination: pathlib.Path, entetes: dict[str, str] | None = None) -> dict:
    """Télécharge l'archive. Rend un compte rendu, sans jamais lever d'exception HTTP 304.

    `entetes` sert au téléchargement conditionnel : en passant l'`ETag` ou le
    `Last-Modified` de la fois précédente, le serveur répond `304` si rien n'a
    changé et l'on économise 10 Mo.
    """
    requete = urllib.request.Request(
        URL_ARCHIVE,
        headers={"User-Agent": "AN-API/socle (recuperation open data)", **(entetes or {})},
    )
    try:
        with urllib.request.urlopen(requete, timeout=600) as reponse:
            contenu = reponse.read()
            destination.write_bytes(contenu)
            return {
                "modifie": True,
                "octets": len(contenu),
                "etag": reponse.headers.get("ETag"),
                "modifieLe": reponse.headers.get("Last-Modified"),
            }
    except urllib.error.HTTPError as erreur:
        if erreur.code == 304:
            return {"modifie": False, "octets": 0, "etag": entetes.get("If-None-Match"),
                    "modifieLe": entetes.get("If-Modified-Since")}
        raise
