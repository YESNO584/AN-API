"""Un acte d'un dossier, tel que la source le publie : sa chambre, son libellé,
la précision de sa réunion, les textes et les rapporteurs qu'il désigne — et sa
place sur l'échelle des six étapes. Rien n'est rédigé ici : chaque valeur est
recopiée de l'open data ou d'un référentiel qu'il désigne.
"""
from __future__ import annotations

import json


CHAMBRES = {"AN": "assemblee", "SN": "senat"}


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
