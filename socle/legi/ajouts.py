"""Ce qu'une loi écrit pour elle-même : reconnaître ses propres articles, et en retirer les renvois qui ne sont pas du droit.
"""
from __future__ import annotations

import re
from legi.balises import _TEXTE, attributs, champ, nettoyer, normaliser
from legi.etats import EN_COURS, TYPE_SANS_TEXTE


# La phrase par laquelle un article de loi annonce qu'il en amende un autre.
# Elle vient toujours seule dans son `<p>`, suivie d'un `<blockquote>` qui
# porte la liste des articles visés. Les cinq verbes sont ceux de Légifrance.
_ANNONCE_RENVOI = re.compile(
    r"\ba\s+(?:modifié|créé|abrogé|transféré|déplacé)\s+les\s+dispositions"
    r"\s+(?:suivantes|ci-après)", re.I)


# Le plus imbriqué d'abord : un `<blockquote>` en contient un autre, et une
# expression non gourmande s'arrêterait sur la fermeture de l'intérieur.
_BLOCKQUOTE = re.compile(r"<blockquote>(?:(?!<blockquote>).)*?</blockquote>", re.S)


def sans_les_renvois(bloc: str) -> str:
    """Le texte d'un article de loi, débarrassé de ce qui n'est pas à lire.

    Un article de loi mêle deux choses : des phrases de droit, et des
    **renvois** — « I. - A modifié les dispositions suivantes : - Code rural
    Art. L230-5-1 ». Le renvoi n'est pas du texte : c'est l'instruction, dont
    le résultat est déjà à l'écran sous forme de l'article de code modifié. Le
    garder afficherait deux fois la même chose, dont une fois en liste de
    références illisible.

    La source le dit par sa **structure**, et c'est ce qu'on suit : le renvoi
    est un `<p>` d'annonce suivi d'un `<blockquote>`. Une règle sur le texte
    seul se trompait — « I. A modifié… » ne commence pas par le verbe, et
    « les dispositions suivantes » peut apparaître dans une vraie phrase.

    Rend la chaîne vide quand il ne reste rien : l'article n'a alors rien à
    montrer. C'est ce qui écarte l'article 82 de la loi 2025-127, fait de dix
    renvois et de rien d'autre, tout en gardant le III de l'article 8 de la
    loi 2026-796, seule phrase de droit au milieu de trois renvois.

    **Ne s'applique qu'aux articles d'une loi.** Un article de code n'est
    jamais nettoyé : ce qu'on en montre sert à une comparaison, et en retirer
    un morceau la ferait mentir.
    """
    ancien = None
    while ancien != bloc:
        ancien, bloc = bloc, _BLOCKQUOTE.sub("", bloc)
    gardes = [propre for morceau in bloc.split("</p>")
              if (propre := nettoyer(morceau)) and not _ANNONCE_RENVOI.search(propre)]
    return normaliser(" ".join(gardes))


def support(xml: str) -> dict[str, str]:
    """Le texte qui **porte** cet article : sa nature, son numéro, son identifiant.

    C'est le seul endroit où un article dit à quelle loi il appartient :

        <TEXTE nature="LOI" num="2026-796" cid="JORFTEXT000054707007" …>

    Le renseignement est donc direct — aucun rapprochement par titre.
    """
    trouve = _TEXTE.search(champ(xml, "CONTEXTE"))
    return attributs(trouve.group(1)) if trouve else {}


def loi_qui_porte(xml: str) -> str | None:
    """Le numéro de la loi dont cet article est un article, s'il en est un.

    Deux précautions, nécessaires l'une et l'autre :

    - **la nature avant le numéro.** Un décret porte un numéro de la même forme
      qu'une loi — « Décret n°2005-850 du 27 juillet 2005 ». Se fier au seul
      numéro confondrait les deux ;
    - **les lois organiques comptent.** Leur nature est `LOI_ORGANIQUE`, d'où
      le préfixe plutôt qu'une égalité. Le projet en suit une (loi 2024-1177).

    Natures rencontrées le 2026-09-03 sur 8 274 articles : `CODE` 6 972,
    `LOI` 670, `ARRETE` 409, `DECRET` 171, `ORDONNANCE` 36, `CONSTITUTION` 14,
    `LOI_ORGANIQUE` 2.
    """
    porteur = support(xml)
    if not porteur.get("nature", "").startswith("LOI"):
        return None
    return porteur.get("num") or None


def est_un_ajout(xml: str, precedent: str | None) -> bool:
    """Cet article est-il l'un de ceux que sa loi a écrits, et y a-t-il à lire ?

    Deux conditions, et il faut les deux.

    **L'absence de rédaction d'avant.** Elle écarte les rédactions
    *ultérieures* du même article. Toutes les rédactions d'un article nomment
    le même porteur : sans ce garde-fou, la rédaction de l'article 156 de la
    loi de finances pour 2024 telle que **la loi de fin de gestion l'a
    modifiée** s'afficherait comme un article que la loi de finances a écrit —
    alors qu'elle ne l'a pas même produite. Un article de loi vient jusqu'à six
    rédactions successives (article 31 de la loi n° 78-17).

    **Du texte qui reste une fois les renvois retirés.** C'est le seul juge de
    ce qu'il y a à lire ; le `TYPE` annoncé par la source se trompe dans les
    deux sens (voir `TYPE_SANS_TEXTE`).

    **Sauf un cas, où le `TYPE` sait quelque chose de plus que le texte** : un
    article qui ne fera que des renvois, et dont la source n'a pas encore saisi
    le texte. On sait déjà qu'il n'y aura rien à lire.
    """
    if precedent:
        return False
    utile = sans_les_renvois(champ(xml, "BLOC_TEXTUEL"))
    if not utile:
        return False
    return not (est_en_attente(utile) and champ(xml, "TYPE") == TYPE_SANS_TEXTE)


# Au plus tant de caractères pour identifier un article que la source ne
# numérote pas. Assez pour reconnaître « ÉTAT A », pas assez pour recopier un
# tableau de recettes dans une liste.
INTITULE_MAX = 62


def intitule_de_secours(texte: str, maximum: int = INTITULE_MAX) -> str:
    """De quoi nommer un article auquel la source ne donne aucun numéro.

    Six rédactions sur 5 091 sont dans ce cas (mesuré le 2026-09-03), et ce ne
    sont pas des cas perdus : ce sont les **états et annexes** des lois de
    finances et de financement de la sécurité sociale — l'état A de la loi de
    fin de gestion pour 2024 en est un, et c'est le tableau des recettes.
    Écrire « Article » suivi de rien ne dit à personne ce qu'on ouvre.

    On recopie donc le début du texte, coupé à un mot entier. **Rien n'est
    rédigé** : la source écrit elle-même son titre en tête — « ÉTATS
    LÉGISLATIFS ANNEXÉS ÉTAT A (ARTICLE 3 DE LA LOI) ». Et on ne cherche pas à
    deviner où ce titre s'arrête : les capitales et la mise en page ne le
    disent pas de façon fiable d'une loi à l'autre. C'est un début de texte,
    présenté comme tel, pas un intitulé que nous aurions fabriqué.
    """
    propre = normaliser(texte or "")
    if len(propre) <= maximum:
        return propre
    coupe = propre[:maximum].rsplit(" ", 1)[0]
    return (coupe or propre[:maximum]) + "…"


def est_en_attente(texte: str | None) -> bool:
    """La source a publié l'article sans avoir encore saisi son texte.

    Mesuré le 2026-09-03 : **69 des 138 articles** de la loi 2026-798,
    promulguée la veille, portent « en cours de traitement » à la place de leur
    texte. Le dire vaut mieux que d'afficher cette phrase comme si c'était la
    loi, et mieux que de faire disparaître un article qui existe.
    """
    return (texte or "").strip().lower().startswith(EN_COURS)
