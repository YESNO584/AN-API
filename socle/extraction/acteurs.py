"""Les députés et leurs groupes : qui siège où, et l'ordre des groupes de la gauche à la droite, mesuré sur les sièges.
"""
from __future__ import annotations

import pathlib
from typing import Iterable, Iterator
from extraction.archives import _lire
from extraction.sources import PHOTO_DEPUTE


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


def mandats_en_cours(a: dict) -> tuple[str | None, str | None, str | None, str | None]:
    """Le groupe, le département, la circonscription et le siège d'un acteur,
    lus dans ses mandats encore ouverts.

    Le groupe politique se lit dans les mandats : celui de type « GP »
    encore ouvert. Un député peut en avoir changé au cours du mandat.

    La circonscription se lit dans le mandat de type « ASSEMBLEE », lui
    aussi encore ouvert : c'est le mandat de député, et lui seul porte le
    lieu d'élection. **Un mandat fini ne compte pas** — un député battu
    puis revenu par une élection partielle porte les deux, et le
    précédent nommerait l'ancienne circonscription.
    """
    groupe = departement = circo = siege = None
    mandats = (a.get("mandats") or {}).get("mandat")
    if isinstance(mandats, dict):
        mandats = [mandats]
    for m in mandats or []:
        if m.get("dateFin"):
            continue
        if m.get("typeOrgane") == "GP":
            organes = (m.get("organes") or {}).get("organeRef")
            if isinstance(organes, str):
                organes = [organes]
            groupe = (organes or [None])[0]
        elif m.get("typeOrgane") == "ASSEMBLEE":
            lieu = ((m.get("election") or {}).get("lieu")) or {}
            departement = lieu.get("departement")
            circo = lieu.get("numCirco")
            # Le numéro de siège dans l'hémicycle. La source l'écrit sur
            # trois chiffres (« 077 ») ; on garde le nombre, l'affichage
            # n'a pas à recopier un zéro de remplissage. C'est **la même
            # numérotation que celle des scrutins**, sur laquelle l'ordre
            # des groupes est calculé : vérifié le 2026-09-19, les médianes
            # par groupe concordent à quelques places près (RN 72 contre 72,
            # LFI-NFP 603 contre 604).
            place = (m.get("mandature") or {}).get("placeHemicycle")
            siege = str(int(place)) if (place or "").strip().isdigit() else None
    return groupe, departement, circo, siege


def lire_acteurs(archive: pathlib.Path, groupe_et_photo: bool = True) -> dict[str, dict]:
    """Un acteur : nom, civilité, photo, groupe, circonscription, siège.

    `groupe_et_photo` distingue les deux archives. Celle des **députés en
    exercice** porte le groupe politique et donne droit à une photo. Celle des
    **députés, sénateurs et ministres** ne sert qu'à nommer : un sénateur n'a
    pas de groupe à l'Assemblée, et l'adresse des photos ne vaut que pour les
    députés — la réclamer pour un ministre renverrait une image manquante.
    """
    acteurs = {}
    for brut in _lire(archive, "acteur"):
        a = brut["acteur"]
        uid = a["uid"]["#text"] if isinstance(a.get("uid"), dict) else a.get("uid")
        ident = (a.get("etatCivil") or {}).get("ident") or {}

        groupe, departement, circo, siege = mandats_en_cours(a)
        acteurs[uid] = {
            "ref": uid,
            "civilite": ident.get("civ"),
            "prenom": ident.get("prenom"),
            "nom": ident.get("nom"),
            "groupeRef": groupe if groupe_et_photo else None,
            # La circonscription ne vaut, comme le groupe, que pour l'archive
            # des députés en exercice : un sénateur ou un ministre n'en a pas.
            "departement": departement if groupe_et_photo else None,
            "circo": circo if groupe_et_photo else None,
            # Mesuré le 2026-09-19 : 576 députés sur 577 en ont un, aucun
            # numéro n'est partagé, et ils vont de 1 à 650 — la salle compte
            # plus de sièges que de députés. Le 577e n'en a pas : l'affichage
            # n'en montre alors aucun plutôt que d'en inventer.
            "siege": siege if groupe_et_photo else None,
            "photo": (PHOTO_DEPUTE.format(uid[2:])
                      if groupe_et_photo and uid and uid.startswith("PA") else None),
        }
    return acteurs
