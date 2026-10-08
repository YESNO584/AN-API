"""Le décor des tests de lecture : de quoi fabriquer un dossier, un acte, un scrutin, une séance — en quelques lignes chacun, sans réseau ni vraie archive.
"""
from __future__ import annotations

import extraction


AUJOURDHUI = "2026-08-31"


def acte(code, date=None, xsi=None, libelle_court=None, conclusion=None, **extra):
    a = {"codeActe": code, "uid": "u-" + code}
    if date:
        a["dateActe"] = date + "T00:00:00.000+02:00"
    if xsi:
        a["@xsi:type"] = xsi
    a["libelleActe"] = {"nomCanonique": libelle_court or code, "libelleCourt": libelle_court}
    if conclusion:
        a["statutConclusion"] = {"libelle": conclusion}
    a.update(extra)
    return a


def dossier(*actes, procedure="Proposition de loi ordinaire", senat=None, uid="D1"):
    return {"dossierParlementaire": {
        "uid": uid, "legislature": "17",
        "titreDossier": {"titre": "Un texte", "titreChemin": "un_texte", "senatChemin": senat},
        "procedureParlementaire": {"libelle": procedure},
        "actesLegislatifs": {"acteLegislatif": list(actes)},
    }}


def scrutin(objet, *, uid="V1", dossier=None, sort="adopté", date="2026-06-11",
            groupes=(), type_vote="scrutin public ordinaire",
            pour=0, contre=0, abstentions=0):
    ventilation = {"organe": {"organeRef": "PO838901", "groupes": {"groupe": [
        {"organeRef": ref, "nombreMembresGroupe": str(m),
         "vote": {"positionMajoritaire": annoncee,
                  "decompteVoix": {"pour": str(p), "contre": str(c),
                                   "abstentions": str(a), "nonVotants": "0"}}}
        for ref, m, annoncee, p, c, a in groupes]}}} if groupes else None
    return {"scrutin": {
        "uid": uid, "numero": "1", "dateScrutin": date + "T00:00:00.000+02:00",
        "typeVote": {"libelleTypeVote": type_vote},
        "sort": {"code": sort, "libelle": "l'Assemblée nationale a " + sort},
        "titre": objet,
        "objet": {"libelle": objet,
                  "dossierLegislatif": {"dossierRef": dossier} if dossier else None},
        "demandeur": {"texte": "Président du groupe X"},
        "syntheseVote": {"nombreVotants": "100", "nbrSuffragesRequis": "50",
                         "decompte": {"pour": str(pour), "contre": str(contre),
                                      "abstentions": str(abstentions), "nonVotants": "0"}},
        "ventilationVotes": ventilation,
    }}


NS = extraction.NS_DEBATS


def seance(corps: str, date: str = "20260225140000000",
           uid: str = "CRSANR5L17S2026O1N168"):
    """Un compte rendu minuscule, à la forme exacte de ceux de l'Assemblée."""
    import xml.etree.ElementTree as ET
    return ET.fromstring(
        f'<compteRendu xmlns="http://schemas.assemblee-nationale.fr/referentiel">'
        f"<uid>{uid}</uid>"
        f"<metadonnees><dateSeance>{date}</dateSeance></metadonnees>"
        f"<contenu>{corps}</contenu></compteRendu>")


def titre_de_texte(numeros: str = " (n[[o]]\u00a02406)"):
    return (f'<point nivpoint="1" code_grammaire="TITRE_TEXTE_DISCUSSION"'
            f' valeur="{numeros}"><orateurs/><texte>Droit à l\u2019aide à mourir</texte>'
            f"</point>")


def section(titre: str, paragraphes: str = ""):
    return (f'<point nivpoint="2" code_grammaire="DISC_ARTICLES_1_2">'
            f"<orateurs/><texte>{titre}</texte>{paragraphes}</point>")


def parole(nom: str, texte: str, acteur: str = "PA795100",
           code: str = "PAROLE_GENERIQUE", qualite: str = ""):
    return (f'<paragraphe code_grammaire="{code}" id_acteur="{acteur}">'
            f"<orateurs><orateur><nom>{nom}</nom><id>{acteur[2:]}</id>"
            f"<qualite>{qualite}</qualite></orateur></orateurs>"
            f"<texte>{texte}</texte></paragraphe>")


SIGLES = {"Dem", "RN", "SOC", "LFI-NFP", "EPR"}


def donne_la_parole(numero: str, adt: str = "") -> str:
    """La phrase par laquelle la présidence lance la défense d'un amendement."""
    return (f'<paragraphe code_grammaire="DISC_ARTICLES_3_1" adt="{adt}">'
            f"<orateurs><orateur><nom>M. le président</nom><id>719024</id>"
            f"<qualite/></orateur></orateurs>"
            f"<texte>La parole est à M. Untel, pour soutenir l’amendement "
            f"n<exposant>o</exposant> {numero}.</texte></paragraphe>")


def sort_annonce(numero: str, adopte: bool = True) -> str:
    """La ligne en italique qui clôt la discussion d'un amendement."""
    verbe = "est adopté" if adopte else "n’est pas adopté"
    return (f'<paragraphe code_grammaire="SCRUT_ADTS_1_9"><orateurs/><texte>'
            f"<italique>(L’amendement n<exposant>o</exposant> {numero} "
            f"{verbe}.)</italique></texte></paragraphe>")
