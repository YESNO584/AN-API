"""Un dossier législatif tel que publié → un dossier tel que la base le range : ses actes, ses étapes, son statut, et ce que le Sénat en dit.
"""
from __future__ import annotations

import csv
import json
import pathlib
import re
from typing import Iterable, Iterator
from extraction.archives import _lire
from extraction.sources import LEGISLATURE, PREFIXE_DOSSIER_AN


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


def textes_de_l_acte(acte: dict, documents: dict[str, dict] | None) -> dict:
    """Les textes que l'acte désigne : celui qu'il adopte, celui auquel il
    se rapporte — avec le numéro et le type que le référentiel leur donne."""
    d: dict = {}

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
    return d


def rapporteurs_de_l_acte(acte: dict, acteurs: dict[str, dict] | None) -> list[str]:
    """Les rapporteurs de l'acte, nommés tels que le référentiel les écrit."""
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
    return noms


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

    d.update(textes_de_l_acte(acte, documents))
    noms = rapporteurs_de_l_acte(acte, acteurs)
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
