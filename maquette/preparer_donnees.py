#!/usr/bin/env python3
"""Prépare les données de la maquette à partir de l'open data de l'Assemblée.

Pourquoi ce script existe : ni `data.assemblee-nationale.fr` ni `data.senat.fr`
n'autorisent une page web à lire leurs fichiers directement (l'en-tête
`Access-Control-Allow-Origin` est absent — vérifié le 2026-08-31). Une page
HTML ne peut donc pas aller chercher les données au chargement. On les prépare
ici, une fois, et on les écrit dans `feed.html`, qui reste un fichier autonome.

Usage :
    ./preparer_donnees.py                 # télécharge, extrait, écrit feed.html
    ./preparer_donnees.py --zip fichier   # réutilise une archive déjà là
    ./preparer_donnees.py --garder-zip    # garde l'archive pour la prochaine fois

Source : https://data.assemblee-nationale.fr — Licence Ouverte (Etalab).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys
import tempfile
import urllib.request
import zipfile

RACINE = pathlib.Path(__file__).resolve().parent

URL_DOSSIERS = (
    "https://data.assemblee-nationale.fr/static/openData/repository/17/loi/"
    "dossiers_legislatifs/Dossiers_Legislatifs.json.zip"
)
LEGISLATURE = "17"
URL_DOSSIER_AN = "https://www.assemblee-nationale.fr/dyn/17/dossiers/"

# Seuls ces types de dossier fabriquent une loi. Les autres (résolutions,
# rapports d'information, missions, commissions d'enquête, allocutions…) sont
# des travaux de l'Assemblée qui n'aboutissent à aucun texte : 708 dossiers sur
# 2 859 le 2026-08-31. Les mélanger à un fil de lois le rendrait faux.
TYPES_DE_LOI = {
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
}

# Les six étapes du §3.1 de PLAN.md, dans l'ordre du parcours.
ETAPES = [
    (1, "Dépôt", "Le texte est déposé et renvoyé à une commission, mais personne "
                 "ne l'a encore examiné. C'est de loin le cas le plus fréquent : "
                 "la plupart des propositions de loi n'iront jamais plus loin."),
    (2, "Commission", "Une commission l'examine et l'amende."),
    (3, "Séance publique", "La chambre en débat et vote sur l'ensemble."),
    (4, "Navette", "Le texte est parti à l'autre chambre, qui recommence tout."),
    (5, "Sortie de navette", "Commission mixte paritaire, ou dernier mot à l'Assemblée."),
    (6, "Après le vote", "Contrôle du Conseil constitutionnel avant promulgation."),
]

CHAMBRES = {"AN": "assemblee", "SN": "senat"}


def chambre_du_code(code: str) -> str | None:
    """« AN1-DEBATS-SEANCE » → « assemblee ». None pour CMP, CC, PROM."""
    return CHAMBRES.get(code[:2])


def aplatir(noeud: dict) -> list[dict]:
    """Les actes législatifs forment un arbre ; on en fait une liste."""
    resultat = []
    actes = noeud.get("acteLegislatif")
    if isinstance(actes, dict):
        actes = [actes]
    for acte in actes or []:
        resultat.append(acte)
        if acte.get("actesLegislatifs"):
            resultat += aplatir(acte["actesLegislatifs"])
    return resultat


def numero_etape(code: str, chambre_initiale: str | None) -> int:
    """Où se situe un acte, sur l'échelle des six étapes du §3.1 de PLAN.md.

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


def telecharger(destination: pathlib.Path) -> pathlib.Path:
    print(f"Téléchargement de {URL_DOSSIERS}", file=sys.stderr)
    requete = urllib.request.Request(
        URL_DOSSIERS, headers={"User-Agent": "AN-API/maquette (preparation de donnees)"}
    )
    with urllib.request.urlopen(requete, timeout=300) as reponse:
        destination.write_bytes(reponse.read())
    print(f"  {destination.stat().st_size:,} octets", file=sys.stderr)
    return destination


def lire_dossiers(archive: pathlib.Path) -> list[dict]:
    with zipfile.ZipFile(archive) as zf:
        noms = [n for n in zf.namelist() if "/dossierParlementaire/" in n and n.endswith(".json")]
        print(f"  {len(noms)} dossiers dans l'archive", file=sys.stderr)
        for nom in noms:
            with zf.open(nom) as fichier:
                yield json.load(fichier)["dossierParlementaire"]


def extraire(archive: pathlib.Path, aujourdhui: str) -> tuple[list[dict], dict]:
    textes = []
    compte = {"total": 0, "hors_loi": 0, "promulgues": 0, "retires": 0, "sans_acte": 0}

    for dossier in lire_dossiers(archive):
        if dossier.get("legislature") != LEGISLATURE:
            continue
        compte["total"] += 1

        procedure = (dossier.get("procedureParlementaire") or {}).get("libelle") or ""
        if procedure not in TYPES_DE_LOI:
            compte["hors_loi"] += 1
            continue

        actes = aplatir(dossier.get("actesLegislatifs") or {})
        codes = {a.get("codeActe") or "" for a in actes}
        if "PROM-PUB" in codes:
            compte["promulgues"] += 1
            continue
        if any(c.endswith("RTRINI") for c in codes):
            compte["retires"] += 1
            continue

        # Le fichier contient des séances déjà programmées : leurs dates sont
        # dans le futur. Un texte ne doit pas être classé sur une étape qui
        # n'a pas eu lieu — on sépare donc le passé de l'à-venir.
        passes, futurs = [], []
        for acte in actes:
            date = (acte.get("dateActe") or "")[:10]
            if not date:
                continue
            (passes if date <= aujourdhui else futurs).append((date, acte))
        if not passes:
            compte["sans_acte"] += 1
            continue

        passes.sort(key=lambda p: p[0])
        futurs.sort(key=lambda p: p[0])

        depots = [a for a in actes if a.get("@xsi:type") == "DepotInitiative_Type"]
        chambre_initiale = (
            chambre_du_code((depots[0].get("codeActe") or "").partition("-")[0])
            if depots else chambre_du_code((passes[0][1].get("codeActe") or "")[:2])
        )

        # Où en est le texte : l'étape des actes du jour le plus récent.
        #
        # Deux pièges obligent à cette formulation. D'abord, plusieurs actes
        # portent la même date et leur ordre dans le fichier n'a pas de sens :
        # entre eux, on retient donc le plus avancé. Ensuite, le parcours n'est
        # pas une ligne droite — après une commission mixte paritaire qui
        # échoue, le texte repart en nouvelle lecture. Prendre « l'étape la plus
        # avancée jamais atteinte » le laisserait affiché en sortie de navette
        # alors qu'il est reparti chez l'autre chambre.
        date = passes[-1][0]
        du_jour = [a for d, a in passes if d == date]
        etape = max(numero_etape(a.get("codeActe") or "", chambre_initiale) for a in du_jour)
        dernier = [a for a in du_jour
                   if numero_etape(a.get("codeActe") or "", chambre_initiale) == etape][-1]
        code = dernier.get("codeActe") or ""
        chambre = chambre_du_code(code[:2])

        # Le libellé de la lecture en cours (« 1ère lecture », « Nouvelle
        # Lecture »…) vient de l'étape de premier niveau, pas de l'acte de
        # détail : « Renvoi en commission au fond » sous un titre « Dépôt »
        # serait contradictoire.
        sommet = code.partition("-")[0]
        englobante = next((a for a in actes if (a.get("codeActe") or "") == sommet), None)
        lecture = libelle(englobante, court=True) if englobante else ""

        conclusion = dernier.get("statutConclusion")
        titres = dossier.get("titreDossier") or {}
        chemin = titres.get("titreChemin")
        chemin_senat = titres.get("senatChemin")

        textes.append({
            "id": dossier.get("uid"),
            "titre": (titres.get("titre") or "").strip(),
            "type": procedure,
            "etape": etape,
            "lecture": lecture or code,
            "dernierActe": libelle(dernier),
            "chambre": chambre,
            "chambreInitiale": chambre_initiale,
            "date": date,
            "conclusion": (conclusion or {}).get("libelle") if isinstance(conclusion, dict) else None,
            "prochaine": (
                {"date": futurs[0][0], "quoi": libelle(futurs[0][1]) or futurs[0][1].get("codeActe")}
                if futurs else None
            ),
            "urlAN": URL_DOSSIER_AN + chemin if chemin else None,
            "urlSenat": chemin_senat if chemin_senat and chemin_senat != "None" else None,
        })

    textes.sort(key=lambda t: (t["etape"], t["date"]), reverse=True)
    return textes, compte


def injecter(page: pathlib.Path, textes: list[dict], meta: dict) -> None:
    debut = "// >>> DONNEES"
    fin = "// <<< FIN DONNEES"
    contenu = page.read_text(encoding="utf-8")
    bloc = (
        f"{debut} — écrit par preparer_donnees.py, ne pas modifier à la main\n"
        f"const META = {json.dumps(meta, ensure_ascii=False, indent=2)};\n"
        f"const TEXTES = {json.dumps(textes, ensure_ascii=False, separators=(',', ':'))};\n"
        f"{fin}"
    )
    motif = re.compile(re.escape(debut) + r".*?" + re.escape(fin), re.S)
    if not motif.search(contenu):
        sys.exit(f"Repères « {debut} » / « {fin} » introuvables dans {page}.")
    page.write_text(motif.sub(lambda _: bloc, contenu, count=1), encoding="utf-8")


def main() -> None:
    analyseur = argparse.ArgumentParser(description=__doc__,
                                        formatter_class=argparse.RawDescriptionHelpFormatter)
    analyseur.add_argument("--zip", type=pathlib.Path,
                           help="archive déjà téléchargée, au lieu de la reprendre sur le réseau")
    analyseur.add_argument("--garder-zip", action="store_true",
                           help="conserver l'archive téléchargée dans .cache/")
    analyseur.add_argument("--page", type=pathlib.Path, default=RACINE / "feed.html",
                           help="page à mettre à jour (défaut : feed.html)")
    options = analyseur.parse_args()

    aujourdhui = dt.date.today().isoformat()

    with tempfile.TemporaryDirectory() as travail:
        if options.zip:
            archive = options.zip
            if not archive.exists():
                sys.exit(f"Archive introuvable : {archive}")
            print(f"Archive réutilisée : {archive}", file=sys.stderr)
        elif options.garder_zip:
            cache = RACINE / ".cache"
            cache.mkdir(exist_ok=True)
            archive = telecharger(cache / "Dossiers_Legislatifs.json.zip")
        else:
            archive = telecharger(pathlib.Path(travail) / "dossiers.zip")

        textes, compte = extraire(archive, aujourdhui)

    par_etape = {}
    for numero, nom, _ in ETAPES:
        par_etape[str(numero)] = sum(1 for t in textes if t["etape"] == numero)

    meta = {
        "extraitLe": aujourdhui,
        "source": URL_DOSSIERS,
        "licence": "Licence Ouverte (Etalab)",
        "legislature": LEGISLATURE,
        "etapes": [{"n": n, "nom": nom, "quoi": quoi} for n, nom, quoi in ETAPES],
        "comptes": compte,
        "parEtape": par_etape,
        "enCours": len(textes),
    }

    injecter(options.page, textes, meta)

    print(f"\n{compte['total']} dossiers de la {LEGISLATURE}e législature", file=sys.stderr)
    print(f"  – {compte['hors_loi']} écartés : ne fabriquent pas de loi", file=sys.stderr)
    print(f"  – {compte['promulgues']} promulgués, {compte['retires']} retirés,"
          f" {compte['sans_acte']} sans acte passé", file=sys.stderr)
    print(f"  = {len(textes)} textes en cours écrits dans {options.page}", file=sys.stderr)
    for numero, nom, _ in ETAPES:
        print(f"        {par_etape[str(numero)]:5d}  {numero}. {nom}", file=sys.stderr)


if __name__ == "__main__":
    main()
