"""Lire un document de l'Assemblée : le découper en articles, alinéa par alinéa — les seules règles dont `textes.db` garde le résultat, et que l'empreinte de lecture couvre.
"""
from __future__ import annotations

import functools
import hashlib
import html
import inspect
import re


# L'adresse d'un document. L'identifiant est celui de l'open data.
URL_DOCUMENT = "https://www.assemblee-nationale.fr/dyn/docs/{}.raw"


# On s'annonce : le site est public, les documents sont sous Licence Ouverte,
# et rien n'oblige à se cacher. Un appel par seconde reste en dessous de ce que
# fait un navigateur qui ouvre une seule page du même site.
ENTETES = {
    "User-Agent": ("AN-API/0.1 (maquette « Qui vote quoi » ; "
                   "https://github.com/yesno584/AN-API)"),
    "Accept-Encoding": "gzip",
}


# Un début d'article se reconnaît d'abord à la **classe** du paragraphe : c'est
# la source elle-même qui le dit. 139 documents sur 149 suffisent avec elle.
CLASSE_ARTICLE = "assnat9ArticleNum"


# À défaut de classe, le texte. Les « petites lois » des textes budgétaires
# suivent un autre gabarit Word, sans classes : le repère y est le mot.
DEBUT_ARTICLE = re.compile(r"^Articles?\s+(unique|premier|1er|\d+)", re.I)


# La note de bas de page porte la composition du groupe de l'auteur — jusqu'à
# 130 noms de députés — et se collait au dernier article, qui ressortait alors
# comme massivement supprimé par la commission. **La source la marque
# elle-même** : c'est la structure qui tranche, pas les mots.
FIN_DU_TEXTE = re.compile(r"^assnatEndnote", re.I)


# Les classes qui portent du texte de loi. Une classe inconnue n'est pas
# écartée : les gabarits varient d'un document à l'autre, et perdre un alinéa
# serait pire que d'en garder un de trop.
HORS_TEXTE = ("assnatHeader", "assnatFooter", "assnat1Tome", "assnat2Partie")


# **Le gabarit des projets de loi de finances** (`assnatFPF…`) n'a ni classe
# d'article ni paragraphe « Article » : le titre de l'article est une cellule
# de **tableau** (« ARTICLE 2 : Soutenir le travail… »), puis la source encadre
# elle-même le dispositif entre deux paragraphes vides, `assnatFPFdebutartexte`
# et `assnatFPFfinartexte`. Ce qui suit la fin est l'exposé des motifs de
# l'article, qui n'est pas du texte de loi. Mesuré le 2026-10-09 sur le projet
# de loi de finances pour 2027 : 90 titres, 90 débuts, 90 fins, et rien d'autre
# entre deux repères que le dispositif, ses tableaux et ses notes. Lu avec la
# règle générale, le même document rendait 69 articles vides sur 89 : le mot
# « ARTICLE » n'y apparaissait hors tableau que dans le **sommaire**.
DEBUT_DU_DISPOSITIF = "assnatFPFdebutartexte"


FIN_DU_DISPOSITIF = "assnatFPFfinartexte"


# Le repère de début manque parfois — l'article 4 de la loi de finances de fin
# de gestion pour 2025 n'en a pas, alors que sa fin est marquée : l'article
# commence donc aussi au premier alinéa du dispositif.
DISPOSITIF = (DEBUT_DU_DISPOSITIF, "assnatFPFprojetloiartexte")


# Le numéro d'alinéa, « (1) », imprimé dans la marge : ce n'est pas du texte,
# et le gabarit général ne l'imprime pas.
PASTILLE = "assnatPastille"


# Et ses alinéas sont des **éléments de liste** (`<li>`), dont la puce est le
# numéro d'alinéa. Le projet de loi de finances pour 2027 les écrit encore en
# paragraphes ; ceux de 2025 et de 2026, et les deux lois de finances
# rectificatives, en listes — lus sans elles, leurs articles sortaient vides
# (49 sur 64, 60 sur 81). Seul ce gabarit lit les listes : ajoutées à la règle
# générale, elles grossissaient trois autres documents budgétaires de texte qui
# n'était pas de la loi (mesuré sur les 28 versions des textes budgétaires).
BALISE_BUDGETAIRE = re.compile(r"<(p|h\d|table|li)([^>]*)>(.*?)</\1>", re.S)


# Un alinéa par ligne. Chaque paragraphe, élément de liste ou tableau de la
# source est un alinéa ; les recoller par une espace faisait de chaque article
# un seul bloc, où « I. – », « A. – », « 1° » et « a) » se suivaient sur la même
# ligne. La source ne marque aucun niveau de retrait — même classe, même style
# pour tous les alinéas d'un article — : on ne décale donc rien.
ALINEA = "\n"


BALISE = re.compile(r"<(p|h\d|table)([^>]*)>(.*?)</\1>", re.S)


CLASSE = re.compile(r'class="([^"]*)"')


def blocs(source: str, balise: re.Pattern = BALISE) -> list[tuple[str, str, str]]:
    """Le document, paragraphe par paragraphe : (classe, texte, balise)."""
    corps = source[source.index("<body"):] if "<body" in source else source
    sortie = []
    for m in balise.finditer(corps):
        classe = CLASSE.search(m.group(2))
        texte = re.sub(r"<[^>]+>", " ", m.group(3))
        texte = html.unescape(texte).replace(" ", " ")
        texte = re.sub(r"[ \t\r\n]+", " ", texte).strip()
        sortie.append((classe.group(1) if classe else "", texte, m.group(1)))
    return sortie


def articles(source: str) -> dict[str, str]:
    """Le dispositif : {titre de l'article: son texte}, dans l'ordre du texte.

    L'exposé des motifs, la page de garde et la note de fin n'en font pas
    partie : tout ce qui précède le premier titre d'article est ignoré. Le
    document dit lui-même son gabarit : un seul repère `assnatFPF…` suffit à
    le lire comme un projet de loi de finances.
    """
    tous = blocs(source)
    if any(classe.startswith(DEBUT_DU_DISPOSITIF) for classe, _, _ in tous):
        return articles_budgetaires(blocs(source, BALISE_BUDGETAIRE))
    trouves: dict[str, str] = {}
    titre, morceaux = None, []
    for classe, texte, balise in tous:
        if FIN_DU_TEXTE.match(classe):
            break
        debut = (classe.startswith(CLASSE_ARTICLE)
                 or (balise != "table" and DEBUT_ARTICLE.match(texte)))
        if debut:
            if titre is not None:
                trouves[titre] = ALINEA.join(x for x in morceaux if x).strip()
            titre, morceaux = texte, []
        elif titre is not None and not classe.startswith(HORS_TEXTE):
            morceaux.append(texte)
    if titre is not None:
        trouves[titre] = ALINEA.join(x for x in morceaux if x).strip()
    return trouves


def articles_budgetaires(tous: list[tuple[str, str, str]]) -> dict[str, str]:
    """Le dispositif d'un projet de loi de finances, entre les repères de la
    source : il commence au premier bloc du dispositif, son titre est le bloc
    non vide qui le précède, et il s'arrête au `…finartexte`. Le sommaire, les
    rapports et les exposés des motifs restent hors de tout article, quels que
    soient leurs mots."""
    trouves: dict[str, str] = {}
    titre, precedent, morceaux = None, None, []
    for classe, texte, _ in tous:
        if FIN_DU_TEXTE.match(classe):
            break
        if titre is None:
            if not (classe.startswith(DISPOSITIF) and precedent):
                if texte and not classe.startswith(HORS_TEXTE + (PASTILLE,)):
                    precedent = texte
                continue
            titre, morceaux = precedent, []
        if classe.startswith(FIN_DU_DISPOSITIF):
            trouves[titre] = ALINEA.join(x for x in morceaux if x).strip()
            titre, precedent = None, None
        elif not classe.startswith(HORS_TEXTE + (PASTILLE, DEBUT_DU_DISPOSITIF)):
            morceaux.append(texte)
    return trouves


@functools.lru_cache(maxsize=None)
def empreinte_de_lecture() -> str:
    """L'empreinte des règles qui découpent un document en articles — et
    d'elles seules.

    `textes.db` garde le **résultat** de la lecture, pas le document : quand
    ces règles changent, ce qui a été lu avant doit être relu. Chaque document
    porte donc l'empreinte des règles qui l'ont lu, et `recuperer_textes` relit
    peu à peu ceux dont l'empreinte a vieilli, **sans effacer leur lecture
    d'avant** en attendant. La comparaison, le numéro, les mentions se
    calculent à la publication et n'en font pas partie : les changer ne relit
    rien. C'est la règle de `extraction/` et `affichage.py`, appliquée ici.
    """
    regles = [inspect.getsource(f) for f in (blocs, articles, articles_budgetaires)]
    regles += [repr(x) for x in (CLASSE_ARTICLE, DEBUT_ARTICLE.pattern, FIN_DU_TEXTE.pattern,
                                 HORS_TEXTE, DEBUT_DU_DISPOSITIF, FIN_DU_DISPOSITIF,
                                 DISPOSITIF, PASTILLE, BALISE.pattern,
                                 BALISE_BUDGETAIRE.pattern, CLASSE.pattern, ALINEA)]
    return hashlib.sha256("\n".join(regles).encode("utf-8")).hexdigest()[:16]
