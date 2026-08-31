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

import csv
import html
import http.client
import json
import pathlib
import re
import time
import urllib.request
import zipfile
from typing import Iterator

DEPOT = "https://data.assemblee-nationale.fr/static/openData/repository/17/"
URL_ARCHIVE = DEPOT + "loi/dossiers_legislatifs/Dossiers_Legislatifs.json.zip"
URL_SCRUTINS = DEPOT + "loi/scrutins/Scrutins.json.zip"
# Cette archive contient à la fois les groupes (organe/) et les députés
# (acteur/) : une seule source pour les deux.
URL_ORGANES = DEPOT + "amo/deputes_actifs_mandats_actifs_organes/AMO10_deputes_actifs_mandats_actifs_organes.json.zip"
URL_AMENDEMENTS = DEPOT + "loi/amendements_div_legis/Amendements.json.zip"
# L'agenda des réunions. Il ne sert qu'à une chose, mais elle est nécessaire :
# départager deux actes du même jour. Une commission qui se réunit à 9 h puis
# à 15 h, une séance publique qui est la « Deuxième » du jour — sans cette
# archive, les deux s'affichent à l'identique et passent pour un doublon.
URL_AGENDA = DEPOT + "vp/reunions/Agenda.json.zip"

# Les photos des députés. Elles ne sont pas dans l'open data : ce sont des
# fichiers du site de l'Assemblée, dont l'adresse se déduit de l'identifiant.
# Testées le 2026-08-31 sur douze députés tirés au hasard — dix réponses, deux
# coupures réseau, aucune absente.
PHOTO_DEPUTE = "https://www2.assemblee-nationale.fr/static/tribun/17/photos/{}.jpg"

# Le Sénat, pour une seule raison : il dit ce que l'Assemblée ne dit pas —
# qu'un texte est « non adopté », « caduc » ou « retiré ». Sans lui, 29 textes
# finis restent affichés comme en cours (mesuré le 2026-08-31).
URL_SENAT = "https://data.senat.fr/data/dosleg/dossiers-legislatifs.csv"
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

# Comment le dire à l'écran. **Aucune de ces phrases ne prétend qu'un texte
# est fini pour de bon** : la source ne le dit pas, nous non plus. Un texte
# rejeté ou non adopté peut être redéposé, et rien dans les données ne permet
# de l'exclure.
FINS = {
    PROMULGUE: ("Promulguée",
                "Le parcours est terminé : le texte est devenu une loi, signée et "
                "publiée au Journal officiel. C'est à partir de là qu'elle s'applique."),
    REJETE: ("Rejeté",
             "La dernière décision connue sur ce texte est un rejet. Cela ne veut pas "
             "dire qu'il ne reviendra jamais : un texte rejeté peut être redéposé, et "
             "la source ne se prononce pas là-dessus."),
    NON_ADOPTE: ("Non adopté",
                 "Le Sénat indique que ce texte n'a pas été adopté. C'est son propre "
                 "mot. Un texte non adopté peut être redéposé ; rien dans les données "
                 "ne dit s'il le sera."),
    CADUC: ("Caduc",
            "Le Sénat indique que ce texte est caduc : il n'a pas abouti avant la fin "
            "de la période où il pouvait être examiné. Pour repartir, il devrait être "
            "déposé à nouveau."),
    RETIRE: ("Retiré",
             "Le texte a été retiré par celui qui l'avait déposé. Ce n'est ni un rejet "
             "ni un échec de vote : son auteur a choisi de l'enlever."),
    EN_COURS: ("En cours d'examen",
               "Le texte est quelque part entre son dépôt et sa promulgation. Rien ne "
               "dit qu'il ira au bout : la plupart s'arrêtent en route."),
}


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


# Le quantième que l'Assemblée donne elle-même à ses séances. Ces quatre
# valeurs sont les seules relevées sur les 382 réunions à départager
# (2026-08-31) ; toute autre valeur est rendue telle quelle plutôt que perdue.
QUANTIEMES = {"Première": "1re séance", "Deuxième": "2e séance",
              "Troisième": "3e séance", "Quatrième": "4e séance"}


def precision_acte(acte: dict, reunions: dict[str, dict] | None = None) -> str | None:
    """Ce qui distingue cet acte d'un autre acte du même jour.

    Trois cas, mesurés sur les 385 groupes d'actes qui partagent un code et
    une date (2026-08-31) :

    - **100 groupes** portent des heures différentes : une commission qui
      siège le matin, l'après-midi et le soir. L'heure suffit.
    - **196 groupes** ont la même heure — la séance publique est datée à
      minuit — mais des réunions différentes. C'est l'agenda qui les nomme :
      « Deuxième séance ».
    - **89 groupes** n'ont rien qui les distingue : même réunion, deux points
      à l'ordre du jour. Ceux-là sont fusionnés, faute de quoi la fiche
      afficherait deux lignes identiques.

    Rend `None` pour le troisième cas, ce qui provoque la fusion.
    """
    reunion = (reunions or {}).get(acte.get("reunionRef") or "") or {}
    quantieme = reunion.get("quantieme")
    if quantieme:
        return QUANTIEMES.get(quantieme, quantieme)
    heure = (reunion.get("debut") or acte.get("dateActe") or "")[11:16]
    return f"{heure[:2]} h {heure[3:]}" if heure and heure != "00:00" else None


def details_acte(acte: dict, organes: dict[str, dict] | None = None,
                 documents: dict[str, dict] | None = None,
                 acteurs: dict[str, dict] | None = None) -> dict:
    """Ce que l'acte dit de lui-même, champ par champ.

    **Rien n'est rédigé ici.** Chaque valeur est recopiée de l'open data ou
    d'un référentiel qu'il désigne — le nom d'une commission, le numéro d'un
    texte, le motif d'une saisine. Une clé absente veut dire que la source
    ne dit rien, pas qu'il n'y a rien à dire.
    """
    d: dict = {}

    organe = (organes or {}).get(acte.get("organeRef") or "")
    if organe and organe.get("type") not in ("ASSEMBLEE", "SENAT"):
        d["organe"] = organe.get("libelle")

    def document(ref: str) -> dict:
        doc = (documents or {}).get(ref) or {}
        return {"ref": ref, "type": doc.get("type"), "numero": doc.get("numero"),
                "description": doc.get("description")}

    for cle in ("texteAdopte", "texteAssocie"):
        ref = acte.get(cle)
        if isinstance(ref, str):
            d[cle] = document(ref)

    # L'acte de décision ne dit pas « texteAdopte » : il liste ses textes
    # associés, dont celui que le vote vient de produire (`BTA`). C'est le
    # fait le plus concret de toute l'étape — ce qui sort du vote.
    associes = (acte.get("textesAssocies") or {}).get("texteAssocie")
    if isinstance(associes, dict):
        associes = [associes]
    for x in associes or []:
        if isinstance(x, dict) and x.get("typeTexte") == "BTA" and x.get("refTexteAssocie"):
            d["texteAdopte"] = document(x["refTexteAssocie"])
            break

    rapporteurs = (acte.get("rapporteurs") or {}).get("rapporteur")
    if isinstance(rapporteurs, dict):
        rapporteurs = [rapporteurs]
    noms = []
    for r in rapporteurs or []:
        ref = ((r.get("acteurRef") if isinstance(r, dict) else None)
               or ((r.get("acteur") or {}).get("acteurRef") if isinstance(r, dict) else None))
        personne = (acteurs or {}).get(ref or "")
        if personne:
            noms.append(f'{personne.get("prenom", "")} {personne.get("nom", "")}'.strip())
    if noms:
        d["rapporteurs"] = noms

    if acte.get("motif"):
        d["motif"] = acte["motif"]
    cas = acte.get("casSaisine")
    if isinstance(cas, dict) and cas.get("libelle"):
        d["saisine"] = cas["libelle"]
    if acte.get("provenance"):
        d["provenance"] = acte["provenance"]
    if acte.get("codeLoi"):
        d["loi"] = acte["codeLoi"]
    info = acte.get("infoJO")
    if isinstance(info, dict):
        for source, cible in (("numJO", "journalOfficiel"), ("dateJO", "dateJO")):
            if info.get(source):
                d[cible] = info[source]
    if acte.get("numDecision"):
        d["decision"] = f'{acte["numDecision"]}'
        if acte.get("anneeDecision"):
            d["decision"] = f'{acte["anneeDecision"]}-{acte["numDecision"]}'
    if acte.get("urlConclusion"):
        d["urlDecision"] = acte["urlConclusion"]
    return d


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


def fusionner_actes(etapes: list[dict]) -> list[dict]:
    """Supprime les actes que rien ne distingue les uns des autres.

    Le même texte peut figurer deux fois à l'ordre du jour d'une même réunion :
    l'open data publie alors deux actes identiques, à un identifiant près. Les
    afficher tous les deux ferait passer la donnée pour fautive. Deux actes ne
    sont fusionnés que si **tout ce que la fiche montre** est identique — le
    reste est conservé, avec ce qui le distingue (voir `precision_acte`).
    """
    vus, resultat = set(), []
    for e in etapes:
        empreinte = (e["code"], e["date"], e["precision"], e["libelle"],
                     e["lecture"], e["conclusion"], json.dumps(e["details"], sort_keys=True))
        if empreinte in vus:
            continue
        vus.add(empreinte)
        resultat.append(e)
    return resultat


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
    etapes = fusionner_actes(etapes)

    passees = [e for e in etapes if not e["future"]]
    promulgation = next((a for a in actes if (a.get("codeActe") or "") == "PROM-PUB"), None)
    retrait = any((a.get("codeActe") or "").endswith("RTRINI") for a in actes)

    if promulgation is not None:
        statut = PROMULGUE
    elif retrait:
        statut = RETIRE
    elif not passees:
        statut = SANS_ACTE
    elif est_rejete(passees):
        statut = REJETE
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


def _lire(archive: pathlib.Path, dossier: str) -> Iterator[dict]:
    """Parcourt une archive et rend ses objets, sans tout charger en mémoire."""
    with zipfile.ZipFile(archive) as zf:
        for nom in zf.namelist():
            if f"/{dossier}/" not in nom or not nom.endswith(".json"):
                continue
            with zf.open(nom) as fichier:
                yield json.load(fichier)


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


def lire_scrutins(archive: pathlib.Path) -> Iterator[dict]:
    """Les scrutins publics."""
    with zipfile.ZipFile(archive) as zf:
        for nom in zf.namelist():
            if not nom.endswith(".json"):
                continue
            with zf.open(nom) as fichier:
                yield json.load(fichier)


def lire_groupes(archive: pathlib.Path) -> dict[str, tuple[str, str]]:
    """Les groupes politiques : identifiant → (sigle, nom complet).

    Les scrutins ne nomment pas les groupes, ils y renvoient par un
    identifiant. Sans cette table, « PO845401 a voté contre » n'apprend rien
    à personne.
    """
    groupes = {}
    for brut in _lire(archive, "organe"):
        o = brut["organe"]
        if o.get("codeType") == "GP":
            groupes[o["uid"]] = (o.get("libelleAbrege") or o["uid"], o.get("libelle") or "")
    return groupes


def lire_organes(archive: pathlib.Path) -> dict[str, dict]:
    """Tous les organes : identifiant → nom. Pas seulement les groupes.

    Un acte ne dit pas « la commission des lois », il dit « PO59051 ». Sans
    cette table, une réunion de commission ne peut pas dire laquelle. Les
    7 126 organes de l'archive sont lus, commissions et assemblées comprises.
    """
    organes = {}
    for brut in _lire(archive, "organe"):
        o = brut["organe"]
        organes[o["uid"]] = {"libelle": o.get("libelle") or "",
                             "abrege": o.get("libelleAbrege") or "",
                             "type": o.get("codeType") or ""}
    return organes


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


# Une archive de 297 Mo ne traverse pas toujours le réseau d'un coup. Les deux
# publications du 2026-08-31 ont échoué ainsi : la connexion a été coupée après
# 2,6 Mo, puis après 51,7 Mo. Recommencer depuis le début n'y suffisait pas.
#
# Le serveur de l'Assemblée accepte les reprises — il répond « 206 Partial
# Content » et annonce « accept-ranges: bytes » (vérifié le 2026-08-31). On
# reprend donc là où le transfert s'est arrêté, au lieu de tout redemander.
# Tant que des octets arrivent, on continue : seule une tentative qui
# n'apporte rien consomme le budget. Sans cette nuance, six tentatives
# fructueuses mais courtes épuisaient les essais à 13 Mo sur 297.
ESSAIS_SANS_PROGRES = 6
MORCEAU = 1 << 20


def _taille_annoncee(entetes, deja_recu: int) -> int | None:
    """La taille totale que le serveur annonce, ou None s'il n'en annonce pas.

    Sur une reprise, `Content-Range: bytes 5-99/100` porte le total ; sinon
    c'est `Content-Length`, auquel s'ajoute ce qui est déjà sur le disque.
    """
    portee = entetes.get("Content-Range")
    if portee and "/" in portee:
        total = portee.rsplit("/", 1)[1].strip()
        if total.isdigit():
            return int(total)
    longueur = entetes.get("Content-Length")
    return deja_recu + int(longueur) if longueur and str(longueur).isdigit() else None


def _requete(url: str, entetes: dict[str, str]) -> urllib.request.Request:
    return urllib.request.Request(
        url, headers={"User-Agent": "AN-API/socle (recuperation open data)", **entetes})


def telecharger(destination: pathlib.Path, entetes: dict[str, str] | None = None,
                url: str = URL_ARCHIVE, essais: int = ESSAIS_SANS_PROGRES,
                patienter=None) -> dict:
    """Télécharge une archive. Rend un compte rendu, sans jamais lever d'exception HTTP 304.

    `entetes` sert au téléchargement conditionnel : en passant l'`ETag` ou le
    `Last-Modified` de la fois précédente, le serveur répond `304` si rien n'a
    changé et l'on économise le transfert.

    Un transfert coupé est **repris à l'octet où il s'est arrêté**, pas
    recommencé. Si l'archive a changé entre-temps, le serveur refuse la reprise
    et renvoie tout : on repart alors de zéro, ce qui est le comportement juste.
    Une réponse HTTP en bonne et due forme — 404, 500 — n'est pas réessayée.
    """
    if patienter is None:
        patienter = time.sleep
    recu, empreinte, compte_rendu = 0, None, None
    steriles = 0                      # tentatives d'affilée qui n'ont rien apporté
    with destination.open("wb") as fichier:
        while True:
            avant = recu
            demande = dict(entetes or {})
            if recu and empreinte:
                demande["Range"] = f"bytes={recu}-"
                demande["If-Range"] = empreinte
            try:
                with urllib.request.urlopen(_requete(url, demande), timeout=600) as reponse:
                    if reponse.status != 206 and recu:
                        # Reprise refusée : l'archive a changé, on recommence.
                        fichier.seek(0)
                        fichier.truncate()
                        recu = 0
                    empreinte = reponse.headers.get("ETag") or empreinte
                    compte_rendu = {
                        "modifie": True,
                        "etag": reponse.headers.get("ETag"),
                        "modifieLe": reponse.headers.get("Last-Modified"),
                    }
                    total = _taille_annoncee(reponse.headers, recu)
                    avant = recu
                    while morceau := reponse.read(MORCEAU):
                        fichier.write(morceau)
                        recu += len(morceau)
                # Lu par morceaux, un transfert coupé ne lève rien : la lecture
                # rend une chaîne vide et le fichier paraît complet. Il faut
                # donc comparer soi-même à la taille annoncée. C'est ce piège
                # qui a produit une archive de 4,7 Mo au lieu de 297, sans la
                # moindre erreur (constaté le 2026-08-31).
                if total is not None and recu < total:
                    raise http.client.IncompleteRead(b"", total - recu)
                return {**compte_rendu, "octets": recu}
            except urllib.error.HTTPError as erreur:
                if erreur.code == 304:
                    return {"modifie": False, "octets": 0,
                            "etag": (entetes or {}).get("If-None-Match"),
                            "modifieLe": (entetes or {}).get("If-Modified-Since")}
                raise
            except (http.client.IncompleteRead, urllib.error.URLError,
                    ConnectionError, TimeoutError):
                steriles = 0 if recu > avant else steriles + 1
                if steriles >= essais:
                    raise
                fichier.flush()
                patienter(min(2 ** steriles, 30))
    raise RuntimeError("inatteignable")  # pragma: no cover


# ---------------------------------------------------------------------------
# Les scrutins publics
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Les groupes politiques : leur place dans l'hémicycle, et leur couleur
# ---------------------------------------------------------------------------

# **L'ordre est mesuré, la couleur est une convention.**
#
# L'ordre : chaque vote publie le numéro de siège de chaque député. Sur 61 152
# numéros relevés le 2026-08-31, les groupes se rangent proprement — RN autour
# de la place 72, LFI autour de la 603. L'hémicycle est numéroté de la droite
# vers la gauche : lu à l'envers, il donne l'ordre gauche → droite. Rien n'est
# écrit à la main, donc rien ne se périme quand un groupe naît ou disparaît.
#
# La couleur : l'open data n'en publie aucune. Celles-ci sont une convention
# d'affichage, reprise de l'usage courant. **C'est le seul endroit à corriger**
# si un choix ne convient pas. Un groupe absent de cette table reçoit une
# couleur calculée sur sa position, du rouge à gauche au bleu à droite.
COULEURS_GROUPES = {
    "LFI-NFP": "#d0342c",   # La France insoumise
    "GDR": "#a3231d",       # Gauche démocrate et républicaine
    "EcoS": "#3f9e5a",      # Écologiste et social
    "SOC": "#e57ba0",       # Socialistes et apparentés
    "LIOT": "#c9a227",      # Libertés, Indépendants, Outre-mer et Territoires
    "NI": "#8d8d8d",        # Non inscrits — assis un peu partout
    "Dem": "#e08a3c",       # Les Démocrates
    "EPR": "#e8b33c",       # Ensemble pour la République
    "HOR": "#4aa3c4",       # Horizons & Indépendants
    "DR": "#2a6bb5",        # Droite Républicaine
    "UDR": "#1f4f8f",       # Union des droites pour la République
    "RN": "#12325c",        # Rassemblement National
}

# Le dégradé de repli, du plus à gauche au plus à droite.
DEGRADE = ("#d0342c", "#d8735e", "#c9a227", "#8fa85c", "#5a9ab5", "#2a6bb5", "#12325c")


def couleur_de_groupe(sigle: str, rang: int, total: int) -> str:
    """La couleur d'affichage d'un groupe. Convention, pas donnée publiée."""
    if sigle in COULEURS_GROUPES:
        return COULEURS_GROUPES[sigle]
    if total <= 1:
        return DEGRADE[len(DEGRADE) // 2]
    return DEGRADE[round(rang * (len(DEGRADE) - 1) / (total - 1))]


def mediane_depuis_histogramme(compte: dict[int, int]) -> float | None:
    """La médiane d'une distribution donnée en « valeur → effectif ».

    Les numéros de siège se comptent par millions sur une législature ; les
    empiler dans une liste pour les trier serait du gaspillage, alors qu'ils
    ne prennent qu'environ 650 valeurs distinctes.
    """
    total = sum(compte.values())
    if not total:
        return None
    milieu = total / 2
    cumul = 0
    for valeur in sorted(compte):
        cumul += compte[valeur]
        if cumul >= milieu:
            return float(valeur)
    return None


def places_du_scrutin(brut: dict) -> Iterator[tuple[str, int]]:
    """Rend les couples (groupe, numéro de siège) d'un scrutin."""
    s = brut["scrutin"]
    liste = (((s.get("ventilationVotes") or {}).get("organe") or {})
             .get("groupes") or {}).get("groupe")
    if isinstance(liste, dict):
        liste = [liste]
    for g in liste or []:
        ref = g.get("organeRef")
        nominatif = (g.get("vote") or {}).get("decompteNominatif") or {}
        for cle in ("pours", "contres", "abstentions", "nonVotants"):
            bloc = nominatif.get(cle)
            if not bloc:
                continue
            votants = bloc.get("votant")
            if isinstance(votants, dict):
                votants = [votants]
            for v in votants or []:
                place = v.get("numPlace")
                if ref and place and str(place).isdigit():
                    yield ref, int(place)


def ordonner_groupes(sieges: dict[str, dict[int, int]],
                     noms: dict[str, tuple[str, str]]) -> list[dict]:
    """Range les groupes de la gauche à la droite de l'hémicycle.

    L'hémicycle est numéroté de la droite vers la gauche : on trie donc par
    numéro de siège **décroissant** pour obtenir l'ordre politique habituel.
    """
    medianes = {}
    for ref, compte in sieges.items():
        m = mediane_depuis_histogramme(compte)
        if m is not None:
            medianes[ref] = m

    classement = sorted(medianes, key=lambda r: -medianes[r])
    total = len(classement)
    groupes = []
    for rang, ref in enumerate(classement):
        sigle, nom = noms.get(ref, (ref, ""))
        groupes.append({
            "ref": ref,
            "sigle": sigle,
            "nom": nom,
            "rang": rang,
            "siegeMedian": medianes[ref],
            "couleur": couleur_de_groupe(sigle, rang, total),
        })
    return groupes


# ---------------------------------------------------------------------------
# Qui écrit les textes : députés, documents, amendements
# ---------------------------------------------------------------------------

def lire_acteurs(archive: pathlib.Path) -> dict[str, dict]:
    """Les députés en exercice : identifiant → nom, civilité, photo, groupe."""
    acteurs = {}
    for brut in _lire(archive, "acteur"):
        a = brut["acteur"]
        uid = a["uid"]["#text"] if isinstance(a.get("uid"), dict) else a.get("uid")
        ident = (a.get("etatCivil") or {}).get("ident") or {}

        # Le groupe politique se lit dans les mandats : celui de type « GP »
        # encore ouvert. Un député peut en avoir changé au cours du mandat.
        groupe = None
        mandats = (a.get("mandats") or {}).get("mandat")
        if isinstance(mandats, dict):
            mandats = [mandats]
        for m in mandats or []:
            organes = (m.get("organes") or {}).get("organeRef")
            if isinstance(organes, str):
                organes = [organes]
            if m.get("typeOrgane") == "GP" and not (m.get("dateFin")):
                groupe = (organes or [None])[0]
        acteurs[uid] = {
            "ref": uid,
            "civilite": ident.get("civ"),
            "prenom": ident.get("prenom"),
            "nom": ident.get("nom"),
            "groupeRef": groupe,
            "photo": PHOTO_DEPUTE.format(uid[2:]) if uid and uid.startswith("PA") else None,
        }
    return acteurs


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


# ---------------------------------------------------------------------------
# Les amendements
# ---------------------------------------------------------------------------

# Un amendement n'est pas une différence entre deux textes : c'est une phrase
# d'instruction, écrite en français juridique.
#
#     « Compléter l'alinéa 7 par les mots : « , après avis simple des
#       organisations professionnelles représentant les exploitants agricoles ». »
#
# **On ne reconstitue donc jamais le texte modifié.** Il faudrait pour cela le
# texte original des articles — absent de l'open data, vérifié le 2026-08-31 —
# et un programme capable d'interpréter ces instructions. Le résultat serait
# un texte de loi fabriqué par nous, faux dans une proportion inconnue, et
# présenté comme officiel.
#
# Ce qu'on fait à la place : afficher l'instruction **mot pour mot**, et
# colorer ce que la source elle-même met entre guillemets. Rien n'est inventé.

AJOUT, RETRAIT, NEUTRE = "ajout", "retrait", "neutre"

# Le verbe qui gouverne l'instruction dit ce qu'il advient des passages cités.
# Ce classement est une aide de lecture, pas une vérité juridique : un
# amendement complexe peut mêler plusieurs opérations.
VERBES_RETRAIT = ("supprimer", "abroger")
VERBES_REMPLACEMENT = ("substituer", "remplacer", "rédiger ainsi", "rediger ainsi")


def _texte_brut(html_source: str) -> str:
    sans_balises = re.sub(r"<[^>]+>", " ", html_source or "")
    return re.sub(r"\s+", " ", html.unescape(sans_balises)).strip()


def colorer_dispositif(dispositif: str) -> list[dict]:
    """Découpe l'instruction en morceaux, en marquant les passages cités.

    Rend une liste de `{"texte": …, "role": ajout|retrait|neutre}`. Le texte
    hors guillemets reste neutre : c'est l'instruction elle-même. Les passages
    entre « … » sont ceux que l'amendement ajoute ou retire.

    Règle, volontairement simple et annoncée comme telle :
      — « supprimer », « abroger »            → tout ce qui est cité est retiré ;
      — « substituer », « remplacer »         → le premier cité est retiré,
                                                les suivants sont ajoutés ;
      — sinon (compléter, insérer, ajouter…)  → ce qui est cité est ajouté.
    """
    texte = _texte_brut(dispositif)
    if not texte:
        return []

    debut = texte[:60].lower()
    if any(v in debut for v in VERBES_RETRAIT):
        roles = lambda rang: RETRAIT                                    # noqa: E731
    elif any(v in debut for v in VERBES_REMPLACEMENT):
        roles = lambda rang: RETRAIT if rang == 0 else AJOUT            # noqa: E731
    else:
        roles = lambda rang: AJOUT                                      # noqa: E731

    morceaux, position, rang = [], 0, 0
    for citation in re.finditer(r"«\s*(.*?)\s*»", texte, re.S):
        avant = texte[position:citation.start()]
        if avant.strip():
            morceaux.append({"texte": avant, "role": NEUTRE})
        contenu = citation.group(1)
        if contenu:
            morceaux.append({"texte": contenu, "role": roles(rang)})
            rang += 1
        position = citation.end()
    reste = texte[position:]
    if reste.strip():
        morceaux.append({"texte": reste, "role": NEUTRE})
    return morceaux or [{"texte": texte, "role": NEUTRE}]


def analyser_amendement(brut: dict) -> dict:
    """Un amendement tel que publié → un amendement tel que la base le range."""
    a = brut["amendement"]
    identification = a.get("identification") or {}
    pointeur = a.get("pointeurFragmentTexte") or {}
    division = pointeur.get("division") or {}
    corps = (a.get("corps") or {}).get("contenuAuteur") or {}
    cycle = a.get("cycleDeVie") or {}
    traitements = (cycle.get("etatDesTraitements") or {})
    signataires = (a.get("signataires") or {}).get("auteur") or {}

    def mot(valeur):
        """Le format XML rend un champ vide par {'@xsi:nil': 'true'}, pas par
        `null`. Sans ce filtre, un dict finit dans une colonne de la base."""
        return valeur if isinstance(valeur, str) and valeur else None

    def nombre(valeur):
        try:
            return int(valeur)
        except (TypeError, ValueError):
            return None

    return {
        "uid": a["uid"],
        "dossier": None,                       # rempli par l'appelant, d'après le chemin
        "numero": mot(identification.get("numeroLong")),
        "ordre": nombre(identification.get("numeroOrdreDepot")),
        "article": mot(division.get("titre")) or mot(division.get("articleDesignationCourte")),
        "auteurRef": mot(signataires.get("acteurRef")),
        "groupeRef": mot(signataires.get("groupePolitiqueRef")),
        "typeAuteur": mot(signataires.get("typeAuteur")),
        "dateDepot": mot(cycle.get("dateDepot")),
        "etat": mot((traitements.get("etat") or {}).get("libelle")),
        "sort": mot((traitements.get("sousEtat") or {}).get("libelle")),
        "dispositif": _texte_brut(corps.get("dispositif")),
        "expose": _texte_brut(corps.get("exposeSommaire")),
        "morceaux": colorer_dispositif(corps.get("dispositif")),
    }


def lire_amendements(archive: pathlib.Path) -> Iterator[dict]:
    """Les amendements, avec le dossier auquel ils appartiennent.

    Le lien vers le dossier n'est pas dans le fichier : il est dans le chemin,
    `json/<dossier>/<texte>/<amendement>.json`.
    """
    with zipfile.ZipFile(archive) as zf:
        for nom in zf.namelist():
            if not nom.endswith(".json"):
                continue
            morceaux = nom.split("/")
            if len(morceaux) < 3:
                continue
            with zf.open(nom) as fichier:
                a = analyser_amendement(json.load(fichier))
            a["dossier"] = morceaux[1]
            yield a
