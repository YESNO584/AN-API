"""Les comptes rendus de séance : qui a parlé, de quel texte, dans quel groupe — et le débat de chaque amendement, compté sans être recopié.
"""
from __future__ import annotations

import pathlib
import re
import zipfile
from typing import Iterable, Iterator
from extraction.sources import LEGISLATURE, NS_DEBATS


# Les sections où l'on argumente. Ce sont des **intitulés de la source**, pas
# un classement de notre fait : l'Assemblée nomme elle-même ses sections, et
# c'est dans celles-ci qu'elle donne la parole à un orateur par groupe.
# Ailleurs — discussion des articles, rappels au règlement, questions au
# gouvernement — on parle d'autre chose que du texte dans son ensemble.
SECTIONS_ARGUMENTAIRE = ("Discussion générale", "Explications de vote",
                         "Explication de vote")


# Ce que la source appelle une prise de parole. Les autres codes désignent des
# interruptions (« Mais non ! » lancé depuis les bancs), des annonces de
# scrutin ou des changements de présidence : ce ne sont pas des argumentaires,
# et c'est la source elle-même qui les distingue.
PAROLE = "PAROLE_GENERIQUE"


INTERRUPTION = "INTERRUPTION_1_10"


# Le président de séance ne défend pas un texte : il donne la parole. La
# source le désigne toujours ainsi, sans nom propre.
PRESIDENCE = re.compile(r"^(M\.|Mme) l[ae] président(e)?$")


def _texte_du_noeud(noeud) -> str:
    """Tout le texte d'un nœud XML, italiques comprises, en une seule chaîne."""
    if noeud is None:
        return ""
    return re.sub(r"[ \t]*\s+", " ", "".join(noeud.itertext())).strip()


def est_la_presidence(nom: str | None) -> bool:
    return bool(PRESIDENCE.match((nom or "").strip()))


def sigle_d_orateur(nom: str | None, sigles: set[str]) -> str | None:
    """Le groupe de l'orateur, tel que le compte rendu l'imprime.

    « M. Éric Martineau (Dem) » — le sigle entre parenthèses est le groupe
    **du jour du débat**, ce qui vaut mieux que notre table `acteur`, qui ne
    connaît que le groupe d'aujourd'hui.

    Il faut le confronter à la liste des groupes : la même parenthèse sert à
    départager deux députés homonymes par leur département — « M. Untel
    (Alpes-Maritimes) » — et trois orateurs se sont ainsi vu attribuer un
    groupe qui n'existe pas.
    """
    trouve = re.search(r"\(([^()]+)\)\s*$", nom or "")
    return trouve.group(1) if trouve and trouve.group(1) in sigles else None


def numeros_de_texte(valeur: str | None) -> list[str]:
    """Les numéros de dépôt qu'un titre de section cite.

    L'attribut vaut « (n[[o]] 2406) », ou « (n[[os]] 2406, 2401) » quand deux
    textes sont discutés ensemble. 665 des 1 093 titres en portent un ; les
    autres ouvrent un débat sans texte — questions au gouvernement,
    déclaration du gouvernement, motion de censure.
    """
    return re.findall(r"\d{1,5}", valeur or "")


def prises_de_parole(racine, sigles: set[str]) -> Iterator[dict]:
    """Les argumentaires d'une séance, dans l'ordre où ils ont été prononcés.

    Une prise de parole est une **suite de paragraphes du même orateur** dans
    la même section : le compte rendu la découpe en paragraphes, et les
    interruptions venues des bancs la coupent en deux sans que l'orateur ait
    cédé la parole. On recolle donc, en sautant les interruptions.

    Rend des dictionnaires portant `numeros` — les numéros de dépôt du texte
    discuté — et non un identifiant de dossier : le rapprochement demande la
    liste des documents, que ce module ne charge pas.
    """
    contenu = racine.find(NS_DEBATS + "contenu")
    if contenu is None:
        return
    brut = racine.findtext(f"{NS_DEBATS}metadonnees/{NS_DEBATS}dateSeance") or ""
    jour = f"{brut[:4]}-{brut[4:6]}-{brut[6:8]}" if len(brut) >= 8 else None
    seance = racine.findtext(NS_DEBATS + "uid")

    numeros: list[str] = []
    section: str | None = None
    courante: dict | None = None
    rang = 0

    def clore() -> Iterator[dict]:
        nonlocal courante
        if courante and courante["texte"]:
            yield courante
        courante = None

    for point in contenu:
        if point.tag != NS_DEBATS + "point":
            continue
        niveau = point.get("nivpoint")
        titre = _texte_du_noeud(point.find(NS_DEBATS + "texte"))
        if niveau == "1":
            yield from clore()
            numeros, section = [], None
            if point.get("code_grammaire") == "TITRE_TEXTE_DISCUSSION":
                numeros = numeros_de_texte(point.get("valeur"))
        elif niveau == "2":
            yield from clore()
            section = titre if titre.startswith(SECTIONS_ARGUMENTAIRE) else None
        if not (numeros and section):
            continue

        for para in point.findall(NS_DEBATS + "paragraphe"):
            code = para.get("code_grammaire")
            if code == INTERRUPTION:
                # Elle ne rompt pas la prise de parole en cours : l'orateur
                # reprend son propos au paragraphe suivant.
                continue
            if code != PAROLE:
                yield from clore()
                continue
            orateurs = para.find(NS_DEBATS + "orateurs")
            noms = [o.findtext(NS_DEBATS + "nom") or ""
                    for o in (orateurs if orateurs is not None else [])]
            if any(est_la_presidence(n) for n in noms):
                yield from clore()
                continue
            corps = _texte_du_noeud(para.find(NS_DEBATS + "texte"))
            if not corps:
                continue
            ref = para.get("id_acteur")
            if courante and courante["acteur_ref"] == ref and courante["section"] == section:
                courante["texte"] += "\n\n" + corps
                continue
            yield from clore()
            qualite = next((o.findtext(NS_DEBATS + "qualite") or ""
                            for o in (orateurs if orateurs is not None else [])), "")
            rang += 1
            courante = {
                "seance": seance,
                "date": jour,
                "numeros": list(numeros),
                "section": section,
                "ordre": rang,
                "acteur_ref": ref,
                # Le nom tel que la source l'imprime, sigle compris. On le
                # nettoie du sigle pour l'affichage : il est rangé à part.
                "nom": re.sub(r"\s*\([^()]+\)\s*$", "", noms[0]).strip() if noms else "",
                "qualite": qualite,
                "sigle": next((s for s in (sigle_d_orateur(n, sigles) for n in noms) if s),
                              None),
                "texte": corps,
            }
    yield from clore()


def lire_debats(archive: pathlib.Path, sigles: set[str]) -> list[dict]:
    """Toutes les prises de parole de l'archive, le groupe de chacune rempli.

    Le sigle n'est imprimé qu'**au premier paragraphe** d'une prise de parole,
    quand la présidence vient de donner la parole : 8,7 % des paroles le
    portent. Les autres se rattrapent par l'orateur, vu sous son sigle dans
    une autre séance — ce qui porte l'attribution à 94,6 % (mesuré le
    2026-09-02 sur les 601 comptes rendus de la législature).

    Les 5,4 % qui restent sont des ministres, des rapporteurs et des députés
    non inscrits : ils s'affichent sous leur seul nom. On ne comble pas ce
    trou avec `acteur.groupe_ref`, qui donne le groupe d'aujourd'hui et non
    celui du jour du débat.
    """
    import xml.etree.ElementTree as ET

    paroles: list[dict] = []
    observes: list[tuple[str, str]] = []
    with zipfile.ZipFile(archive) as zf:
        for nom in zf.namelist():
            if not nom.endswith(".xml"):
                continue
            racine = ET.fromstring(zf.read(nom))
            paroles.extend(prises_de_parole(racine, sigles))
            observes.extend(sigles_nommes(racine, sigles))
    return completer_les_sigles(paroles, observes)


def sigles_nommes(racine, sigles: set[str]) -> Iterator[tuple[str, str]]:
    """Chaque orateur de la séance nommé avec son groupe, où qu'il ait parlé.

    Il faut ratisser **toute** la séance, pas seulement les sections
    d'argumentaire : M. Stéphane Lenormand y prend la parole 49 fois sans
    sigle, et les 8 fois où le compte rendu l'imprime « (LIOT) » sont toutes
    dans la discussion des articles. Chercher le sigle dans les seules
    sections retenues laissait 582 paroles sans groupe au lieu de 189.
    """
    for orateur in racine.iter(NS_DEBATS + "orateur"):
        sigle = sigle_d_orateur(orateur.findtext(NS_DEBATS + "nom"), sigles)
        identifiant = orateur.findtext(NS_DEBATS + "id")
        if sigle and identifiant:
            yield "PA" + identifiant, sigle


def completer_les_sigles(paroles: list[dict],
                         observes: Iterable[tuple[str, str]] = ()) -> list[dict]:
    """Donne à chaque orateur le sigle sous lequel la séance l'a nommé ailleurs.

    Trois orateurs sur 521 ont été vus sous plus d'un sigle — un changement de
    groupe en cours de législature. On retient le plus fréquent, faute de
    pouvoir dater le changement.
    """
    vus: dict[str, dict[str, int]] = {}
    paires = list(observes) or [(p["acteur_ref"], p["sigle"]) for p in paroles]
    for ref, sigle in paires:
        if ref and sigle:
            compte = vus.setdefault(ref, {})
            compte[sigle] = compte.get(sigle, 0) + 1
    connus = {ref: max(compte, key=compte.get) for ref, compte in vus.items()}
    for p in paroles:
        if not p["sigle"]:
            p["sigle"] = connus.get(p["acteur_ref"])
    return paroles


# ---------------------------------------------------------------------------
# Combien de monde a parlé d'un amendement
#
# L'onglet « Texte » montre déjà les amendements adoptés sur chaque article.
# Ce qui manquait est l'ampleur du débat : un amendement défendu, contesté par
# six groupes et adopté à deux voix près n'a rien d'un amendement de
# coordination, et rien ne le disait à l'écran.
#
# **On ne récolte qu'un compte, jamais le texte.** Les prises de parole de la
# discussion des articles ne sont pas publiées : les rapprocher d'un amendement
# demanderait de trancher des cas que la source ne tranche pas. Un nombre
# d'orateurs, lui, se compte sans rien interpréter.
#
# Trois règles, mesurées le 2026-09-20 sur les 601 comptes rendus :
#
# - **L'amendement se nomme dans la phrase de la présidence** — « La parole est
#   à M. le ministre, pour soutenir l'amendement n° 885 rectifié ». 14 930
#   occurrences. On ne se sert **pas** de l'attribut `adt` du paragraphe : il
#   traîne d'un amendement au suivant. Sur 13 665 annonces vérifiables, il en
#   contredit 837 et manque sur 1 590 — et sur l'amendement 885 de la loi
#   Ripost, il annonce 605.
# - **Une discussion commune ne se découpe pas.** 27 % des blocs portent
#   plusieurs amendements défendus à la suite avant qu'on ne vote : ce qui s'y
#   dit vaut pour l'ensemble, pas pour l'un d'eux. On les laisse de côté.
# - **Un bloc n'est gardé que si la séance a annoncé un sort.** Sans cette
#   clôture, un bloc court jusqu'à l'annonce suivante et avale ce qui ne le
#   concerne pas.
#
# Le nombre d'orateurs compte les **personnes distinctes**, présidence exclue,
# interruptions comprises : « Et l'alcool ? » lancé des bancs est quelqu'un qui
# prend part au débat. C'est ce qui distingue un échange d'un long monologue —
# l'amendement 885 a 15 orateurs pour 58 paragraphes, quand un autre du même
# texte en a 3 pour 36.
SOUTENIR_AMENDEMENT = re.compile(
    r"pour soutenir\s+"
    r"(?:l['’]amendement|les amendements identiques|le sous-amendement)s?"
    r"\s*n[^0-9]{0,12}(\d+)", re.IGNORECASE)


SORT_AMENDEMENT = re.compile(
    r"\(\s*(?:L['’]amendement|Les amendements identiques|Le sous-amendement)s?"
    r"\s*n[^0-9]{0,12}\d+[^)]*?(?:est|sont|n['’]est|ne sont)[^)]*\)",
    re.IGNORECASE)


def _nom_d_orateur(para) -> str | None:
    """Qui parle dans ce paragraphe, présidence exclue."""
    orateurs = para.find(NS_DEBATS + "orateurs")
    for orateur in (orateurs if orateurs is not None else []):
        nom = (orateur.findtext(NS_DEBATS + "nom") or "").strip()
        if nom and not est_la_presidence(nom):
            return nom
    return None


def debats_par_amendement(racine) -> Iterator[dict]:
    """Par amendement discuté seul dans cette séance : combien en ont parlé.

    Rend `numeros` — les numéros de dépôt du texte discuté, comme
    `prises_de_parole` — et non un identifiant de dossier : le rapprochement
    demande la liste des documents, que ce module ne charge pas.

    Le texte est celui qu'annonce le point de niveau 1, jamais l'attribut
    `bibard` du paragraphe, qui traîne comme `adt`.
    """
    contenu = racine.find(NS_DEBATS + "contenu")
    if contenu is None:
        return
    brut = racine.findtext(f"{NS_DEBATS}metadonnees/{NS_DEBATS}dateSeance") or ""
    jour = f"{brut[:4]}-{brut[4:6]}-{brut[6:8]}" if len(brut) >= 8 else None
    seance = racine.findtext(NS_DEBATS + "uid")

    numeros: list[str] = []
    bloc: dict | None = None

    def clore() -> Iterator[dict]:
        """Rend le bloc en cours s'il est exploitable, et le referme."""
        nonlocal bloc
        if bloc and bloc["ferme"] and len(bloc["amendements"]) == 1:
            yield {"seance": seance, "date": jour, "numeros": list(bloc["numeros"]),
                   "amendement": bloc["amendements"][0],
                   "orateurs": len(bloc["orateurs"]),
                   "paragraphes": bloc["paragraphes"]}
        bloc = None

    for point in contenu:
        if point.tag != NS_DEBATS + "point":
            continue
        if point.get("nivpoint") == "1":
            yield from clore()
            numeros = (numeros_de_texte(point.get("valeur"))
                       if point.get("code_grammaire") == "TITRE_TEXTE_DISCUSSION"
                       else [])
        if not numeros:
            continue
        # `iter` et non `findall` : dans la discussion des articles, les
        # paragraphes sont enfouis sous un point d'amendement et un
        # `interExtraction`, alors qu'ils sont posés à plat dans les sections
        # d'argumentaire.
        for para in point.iter(NS_DEBATS + "paragraphe"):
            corps = _texte_du_noeud(para.find(NS_DEBATS + "texte"))
            if not corps:
                continue
            annonce = SOUTENIR_AMENDEMENT.search(corps)
            if annonce:
                # Un sort a été annoncé depuis la dernière annonce : le bloc
                # précédent est clos, celui-ci commence.
                if bloc and bloc["ferme"]:
                    yield from clore()
                if bloc is None:
                    bloc = {"numeros": numeros, "amendements": [], "orateurs": set(),
                            "paragraphes": 0, "ferme": False}
                bloc["amendements"].append(annonce.group(1))
                continue
            if bloc is None:
                continue
            bloc["paragraphes"] += 1
            nom = _nom_d_orateur(para)
            if nom:
                bloc["orateurs"].add(nom)
            if SORT_AMENDEMENT.search(corps):
                bloc["ferme"] = True
    yield from clore()


def lire_debats_par_amendement(archive: pathlib.Path) -> list[dict]:
    """Le compte d'orateurs de chaque amendement discuté seul, dans l'archive.

    Deuxième lecture de la même archive de 55,8 Mo, et c'est assumé : la
    récolte des argumentaires marche par prise de parole, celle-ci par bloc de
    discussion, et mêler les deux machines ferait une fonction que personne ne
    pourrait plus modifier sans casser l'autre. Le coût mesuré est de douze
    secondes sur une récupération qui en prend soixante.
    """
    import xml.etree.ElementTree as ET

    blocs: list[dict] = []
    with zipfile.ZipFile(archive) as zf:
        for nom in zf.namelist():
            if not nom.endswith(".xml"):
                continue
            blocs.extend(debats_par_amendement(ET.fromstring(zf.read(nom))))
    return blocs


# Le préfixe d'identifiant des documents déposés à l'Assemblée pour cette
# législature. Il faut le poser : le même numéro de dépôt sert au Sénat et à
# nous. « n° 698 » désigne quatre documents dans l'archive — une proposition
# de l'Assemblée, son rapport, et deux propositions du Sénat.
PREFIXE_DOCUMENT_AN = f"ANR5L{LEGISLATURE}"


def documents_par_numero(documents: dict[str, dict]) -> dict[str, set[str]]:
    """Quel dossier porte le numéro de dépôt cité en séance.

    Un numéro peut en désigner deux : la proposition de loi et le rapport
    portent le même, et ils appartiennent d'ordinaire au même dossier — mais
    pas toujours. D'où un ensemble, que `dossier_des_numeros` départage.
    """
    par_numero: dict[str, set[str]] = {}
    for d in documents.values():
        if d["numero"] and d["dossier"] and PREFIXE_DOCUMENT_AN in d["uid"]:
            par_numero.setdefault(str(d["numero"]), set()).add(d["dossier"])
    return par_numero


def dossier_des_numeros(numeros: list[str], jour: str | None,
                        par_numero: dict[str, set[str]],
                        dates: dict[str, set[str]]) -> str | None:
    """Le dossier discuté, ou rien du tout.

    Deux textes discutés ensemble donnent deux numéros ; on ne rattache la
    parole qu'à un seul dossier, celui qui reste après la date. Mesuré le
    2026-09-02 : 614 des 693 numéros cités désignent un seul dossier,
    **aucun n'en désigne deux**, et les 79 restants appartiennent à des
    dossiers de la 16e législature, que le projet ne suit pas.

    La date fait tout le travail : sans elle, 97 numéros désignent deux à
    quatre dossiers. Un dossier discuté ce jour-là a forcément une étape
    datée de ce jour-là.
    """
    trouves: set[str] = set()
    for numero in numeros:
        trouves |= par_numero.get(numero, set())
    if len(trouves) > 1 and jour:
        trouves = {uid for uid in trouves if jour in dates.get(uid, ())}
    return next(iter(trouves)) if len(trouves) == 1 else None
