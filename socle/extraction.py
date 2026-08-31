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

DEPOT = "https://data.assemblee-nationale.fr/static/openData/repository/17/"
URL_ARCHIVE = DEPOT + "loi/dossiers_legislatifs/Dossiers_Legislatifs.json.zip"
URL_SCRUTINS = DEPOT + "loi/scrutins/Scrutins.json.zip"
URL_ORGANES = DEPOT + "amo/deputes_actifs_mandats_actifs_organes/AMO10_deputes_actifs_mandats_actifs_organes.json.zip"
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


def _lire(archive: pathlib.Path, dossier: str) -> Iterator[dict]:
    """Parcourt une archive et rend ses objets, sans tout charger en mémoire."""
    with zipfile.ZipFile(archive) as zf:
        for nom in zf.namelist():
            if f"/{dossier}/" not in nom or not nom.endswith(".json"):
                continue
            with zf.open(nom) as fichier:
                yield json.load(fichier)


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


def telecharger(destination: pathlib.Path, entetes: dict[str, str] | None = None,
                url: str = URL_ARCHIVE) -> dict:
    """Télécharge une archive. Rend un compte rendu, sans jamais lever d'exception HTTP 304.

    `entetes` sert au téléchargement conditionnel : en passant l'`ETag` ou le
    `Last-Modified` de la fois précédente, le serveur répond `304` si rien n'a
    changé et l'on économise le transfert.
    """
    requete = urllib.request.Request(
        url,
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
