"""Lecture du droit consolidé (jeu de données LEGI) : ce qu'une loi change.

Ce module ne fait que lire et comparer. Il ne télécharge rien de sa propre
initiative et n'écrit dans aucune base : `recuperer_legi.py` s'en charge.

**Ce qu'on cherche.** Quand une loi modifie un article de code, LEGI publie la
nouvelle rédaction *et* garde l'ancienne. On peut donc superposer les deux et
montrer exactement ce qui change. Le raccordement avec nos dossiers est direct :
chaque rédaction porte le numéro de la loi qui l'a produite.

**Ce qu'on cherche aussi, depuis le 2026-09-03 : ce qu'une loi ajoute.** Ses
propres articles. Ils n'ont pas d'« avant » — il n'y a donc rien à superposer —
mais ils sont du droit nouveau, et les taire donnait une réponse absurde : une
loi de finances de fin de gestion, dont presque toute la matière est dans ses
propres articles, s'affichait comme ne changeant que deux articles. La source
les publie, avec leur texte ; c'est le rapprochement qui manquait. Voir
`AJOUTE`, `loi_qui_porte` et `est_un_ajout`.

**Ce qu'on ne cherche pas.** Les liens `CITATION` : la loi cite l'article sans y
toucher. Ils sont deux fois plus nombreux que les vraies modifications (5 520
contre 2 711, mesuré le 2026-09-01) — les compter ferait dire n'importe quoi à
l'application.

Source : https://echanges.dila.gouv.fr/OPENDATA/LEGI/ — Licence Ouverte (Etalab).
"""

from __future__ import annotations

import difflib
import html as _html
import re
import tarfile
from typing import BinaryIO, Iterator

DEPOT_LEGI = "https://echanges.dila.gouv.fr/OPENDATA/LEGI/"

# Ce qu'une loi peut faire à un article. `CITATION` n'y est pas, exprès.
CHANGEMENTS = ("MODIFIE", "CREE", "ABROGE", "TRANSFERE", "DEPLACE")

# Ce qu'une loi **ajoute** : ses propres articles. `AJOUTE` est notre mot, pas
# celui de LEGI — et c'est précisément pourquoi on ratait ces articles.
#
# Un lien de changement est porté par l'article **visé**, à la forme verbale
# (`MODIFIE`, `CREE`) et avec le numéro de la loi qui a agi. Un article de loi
# n'en porte jamais : rien n'a agi sur lui, c'est lui qui agit. Ce qu'il porte,
# c'est la forme *nominale* (`MODIFICATION`, `CREATION`) sans numéro de texte.
# La source ne relie donc pas un article à sa propre loi par un lien : elle le
# **range dedans**, et cela se lit dans `CONTEXTE` (voir `loi_qui_porte`).
#
# Mesuré le 2026-09-03 sur deux archives quotidiennes : 642 articles hors code,
# **aucun** portant un lien de changement venant de sa propre loi.
AJOUTE = "AJOUTE"

# Ce que la source annonce d'un article de loi (balise `TYPE`) : `AUTONOME`,
# `PARTIELLEMENT_MODIF`, `ENTIEREMENT_MODIF`. Mesuré le 2026-09-03 sur 667
# articles de loi : 48 %, 16 % et 36 %.
#
# **Ce `TYPE` ne décide de rien, et s'y fier était une erreur — deux fois.**
# Un `PARTIELLEMENT_MODIF` peut n'être fait que de renvois (8 des 87 premiers
# articles retenus n'affichaient qu'une liste de références : article 82 de la
# loi 2025-127, article 44 de la loi 2026-725). Et un `ENTIEREMENT_MODIF` peut
# porter du droit bien réel : l'article 32 de la loi 2026-201 est annoncé comme
# n'amendant que d'autres textes, et 92 % de son contenu est une servitude au
# profit des jeux Olympiques d'hiver. Le seul juge est donc le **texte**, une
# fois les renvois retirés — voir `sans_les_renvois`.
#
# Il reste une chose que le `TYPE` sait et que le texte ne dit pas : qu'un
# article *fera* des renvois et rien d'autre. Utile pour les seuls articles
# dont la source n'a pas encore saisi le texte — les annoncer aujourd'hui pour
# les voir disparaître demain ne rendrait service à personne.
TYPE_SANS_TEXTE = "ENTIEREMENT_MODIF"

# La phrase par laquelle la source remplace un texte qu'elle n'a pas encore
# saisi. Voir `est_en_attente`.
EN_COURS = "en cours de traitement"

# LEGI marque la fin des rédactions en vigueur par une date sentinelle.
SANS_FIN = "2999-01-01"
# Et par une autre — le 22 février 2222 — les dates **non encore fixées** :
# la loi prévoit qu'un article entrera en vigueur ou sera abrogé, mais renvoie
# à un décret qui n'est pas paru. 73 changements sur 2 261 sont dans ce cas
# (mesuré le 2026-09-02), presque tous à l'état VIGUEUR_DIFF ou ABROGE_DIFF.
# C'est une information à dire, pas une date à afficher.
SANS_DATE = "2222-02-22"

_BALISE = re.compile(r"<(\w+)\b([^>]*)/?>")
_ATTRIBUT = re.compile(r'(\w+)="([^"]*)"')
_LIEN_ART = re.compile(r"<LIEN_ART\b[^>]*>")
_LIEN = re.compile(r"<LIEN\b[^>]*>")
_TITRE_TXT = re.compile(r"<TITRE_TXT\b([^>]*)>")
_TEXTE = re.compile(r"<TEXTE\b([^>]*)>")


# ---------------------------------------------------------------------------
# Lire le dépôt
# ---------------------------------------------------------------------------

def archives_du_depot(page: str) -> tuple[str | None, list[str]]:
    """Le socle et les archives quotidiennes, lus dans la page d'index du dépôt.

    Le socle (`Freemium_legi_global_…`) contient **toute l'histoire du droit**,
    pas seulement ce qui est en vigueur : vérifié le 2026-09-01, la plus
    ancienne rédaction rencontrée commence en 1866. Les quotidiennes
    (`LEGI_…`) ne portent que ce qui a changé ce jour-là.
    """
    noms = re.findall(r'href="([^"]+\.tar\.gz)"', page)
    socles = sorted(n for n in noms if n.startswith("Freemium_legi_global_"))
    quotidiennes = sorted(n for n in noms if n.startswith("LEGI_"))
    return (socles[-1] if socles else None), quotidiennes


def parcourir_archive(flux: BinaryIO) -> Iterator[tuple[str, bytes]]:
    """Les fichiers d'articles d'une archive, lus **en flux**, sans rien déplier.

    Le socle pèse 9,5 Go déplié, en 2,5 millions de fichiers minuscules — plus
    pénible pour un disque que son volume. Chronométré le 2026-09-01 : une
    passe complète en flux prend 15,7 minutes et n'écrit rien.
    """
    with tarfile.open(fileobj=flux, mode="r|gz") as archive:
        for membre in archive:
            if membre.isfile() and "/article/" in membre.name:
                contenu = archive.extractfile(membre)
                if contenu is not None:
                    yield membre.name, contenu.read()


# ---------------------------------------------------------------------------
# Lire un fichier d'article
# ---------------------------------------------------------------------------

def attributs(balise: str) -> dict[str, str]:
    """Les attributs d'une balise XML, sans dépendre de leur ordre.

    L'ordre varie d'un fichier à l'autre : une expression régulière qui exige
    `typelien` avant `numtexte` ne trouve rien alors que le lien est là.
    """
    return dict(_ATTRIBUT.findall(balise))


def champ(xml: str, nom: str) -> str:
    """Le contenu d'une balise, tel quel, ou la chaîne vide si elle manque."""
    trouve = re.search(f"<{nom}>(.*?)</{nom}>", xml, re.S)
    return trouve.group(1) if trouve else ""


def nettoyer(fragment: str) -> str:
    """Le texte lisible d'un bloc HTML : balises retirées, espaces normalisés."""
    return normaliser(_html.unescape(re.sub(r"<[^>]+>", " ", fragment)))


def normaliser(texte: str) -> str:
    """Des espaces réguliers, pour que la comparaison ne signale que le fond.

    Légifrance retouche la typographie : « 222-33,222-33-2 » devient
    « 222-33, 222-33-2 ». Sans cette normalisation, ce bruit masque la seule
    vraie modification (mesuré le 2026-08-31 sur l'article 131-35-1 du code
    pénal).
    """
    return re.sub(r"\s+", " ", texte.replace(" ", " ")).strip()


def versions(xml: str) -> list[dict[str, str]]:
    """Toutes les rédactions de l'article, telles que le fichier les liste.

    **La liste n'est pas dans l'ordre chronologique** et contient des rédactions
    qui ne sont jamais entrées en vigueur.
    """
    return [attributs(balise) for balise in _LIEN_ART.findall(champ(xml, "VERSIONS"))]


def est_mort_ne(etat: str) -> bool:
    """Une rédaction votée mais jamais appliquée (`MODIFIE_MORT_NE`, `ABROGE_MORT_NE`)."""
    return etat.endswith("MORT_NE")


def version_precedente(toutes: list[dict[str, str]], debut: str,
                       soi: str | None = None) -> str | None:
    """La rédaction d'« avant » : celle qui se termine quand la nôtre commence.

    C'est **la** règle du module, et la règle évidente est fausse. Prendre
    « celle d'avant dans la liste » désigne parfois une rédaction mort-née :
    sur l'article 6 de la loi n° 2004-575, elle renvoyait à une version datée
    du 22 février 2222, jamais appliquée. La comparaison tombait alors à 13 %
    de texte commun — un avant/après spectaculaire et faux. Avec la règle
    ci-dessous : 97 %, et rien ne change pour les six autres articles de la
    même loi (mesuré le 2026-09-01).

    Deux autres pièges, trouvés le 2026-09-03 en cherchant les articles propres
    des lois. Les deux viennent de la date sentinelle `2999-01-01` :

    - **elle n'est pas une frontière.** Un article dont l'entrée en vigueur
      n'est pas encore fixée la porte en `debut` *et* en `fin`. « Celle qui
      finit quand la nôtre commence » désigne alors n'importe quelle rédaction
      encore en vigueur — or une rédaction qui n'a pas commencé n'a pas d'avant ;
    - **un article n'est pas sa propre rédaction d'avant.** Dans ce même cas,
      la liste des versions contient l'article lui-même, avec `fin == debut`.
      Sans le contrôle `soi`, **61 des 130 articles** des lois d'août 2026 se
      donnaient eux-mêmes pour leur « avant ».

    `soi` est l'identifiant de l'article dont on cherche l'avant. Il est
    facultatif pour ne pas casser les appels qui ne l'ont pas, mais
    `lire_article` le passe toujours.
    """
    if debut == SANS_FIN:
        return None
    for version in toutes:
        if (version.get("fin") == debut and version.get("id") != soi
                and not est_mort_ne(version.get("etat", ""))):
            return version.get("id")
    return None


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


def changements(xml: str) -> list[dict[str, str]]:
    """Les textes qui ont agi sur cet article, et ce qu'ils lui ont fait.

    Seuls les liens `sens="cible"` disent « ce texte a agi sur moi » ; les
    liens `sens="source"` disent l'inverse et ne nous concernent pas.
    """
    trouves = []
    for balise in _LIEN.findall(champ(xml, "LIENS")):
        lien = attributs(balise)
        if (lien.get("sens") == "cible" and lien.get("typelien") in CHANGEMENTS
                and lien.get("numtexte")):
            trouves.append({"loi": lien["numtexte"], "quoi": lien["typelien"],
                            "article_loi": lien.get("num", "")})
    return trouves


def ou_se_trouve(xml: str, debut: str) -> str:
    """Le code ou la loi qui porte cet article, en clair (« Code de l'éducation »).

    Le fichier propose plusieurs intitulés, valables sur des périodes
    différentes, dont un daté de la sentinelle `2999-01-01` qui n'est pas le
    bon. On garde celui qui couvre la date d'entrée en vigueur.
    """
    titres = [attributs(balise) for balise in _TITRE_TXT.findall(champ(xml, "CONTEXTE"))]
    for titre in titres:
        if titre.get("debut", SANS_FIN) <= debut < titre.get("fin", SANS_FIN):
            return titre.get("c_titre_court", "")
    return titres[-1].get("c_titre_court", "") if titres else ""


def lire_article(xml: str) -> dict:
    """Tout ce qu'on retient d'une rédaction d'article."""
    debut = champ(xml, "DATE_DEBUT")
    identifiant = champ(champ(xml, "META_COMMUN"), "ID")
    precedent = version_precedente(versions(xml), debut, identifiant)
    bloc = champ(xml, "BLOC_TEXTUEL")
    ajout = est_un_ajout(xml, precedent)
    return {
        "id": identifiant,
        "numero": normaliser(champ(xml, "NUM")),
        "ou": ou_se_trouve(xml, debut),
        "etat": champ(xml, "ETAT"),
        "debut": debut,
        "fin": champ(xml, "DATE_FIN"),
        # Un article que la loi a écrit se montre sans ses renvois ; un article
        # de code se montre entier, parce qu'il sera comparé.
        "texte": sans_les_renvois(bloc) if ajout else nettoyer(bloc),
        "nota": nettoyer(champ(xml, "NOTA")),
        "precedent": precedent,
        "changements": changements(xml),
        # La loi dont cet article **est** un article — à ne pas confondre avec
        # celles qui l'ont changé, qui sont dans `changements`.
        "loi_porteuse": loi_qui_porte(xml),
        "ajout": ajout,
    }


# ---------------------------------------------------------------------------
# Comparer deux rédactions
# ---------------------------------------------------------------------------

# Ce qui ne fait pas le fond d'un texte de loi. Le tiret en fait partie, à la
# demande de l'utilisateur : Légifrance passe de « 222-33,222-33-2 » à
# « 222-33, 222-33-2 » sans que rien du droit n'ait bougé. Attention, le tiret
# **à l'intérieur d'un mot** ne compte pas pour autant : « 222-33 » contient
# des chiffres, donc ce morceau-là n'est pas de pure forme.
PONCTUATION = set(" \t\n\u00a0\u202f.,;:!?…«»\"'’‘“”()[]{}-–—/\\*·•")


def sans_forme(texte: str) -> str:
    """Le texte débarrassé de tout ce qui n'en fait pas le fond."""
    return "".join(c for c in texte if c not in PONCTUATION)


def est_de_forme(texte: str) -> bool:
    """Ce morceau n'est-il que de la ponctuation et des espaces ?

    Sert aux ajouts et aux suppressions isolés : une virgule qui apparaît, une
    espace qui disparaît. Il suffit d'**un seul** caractère porteur de sens —
    une lettre, un chiffre — pour que le morceau compte.
    """
    return texte != "" and sans_forme(texte) == ""


def remplacement_de_forme(avant: str, apres: str) -> bool:
    """Ce remplacement ne change-t-il que la ponctuation ou les espaces ?

    C'est **le** cas qu'il fallait attraper, et le juger morceau par morceau ne
    suffit pas. La comparaison se fait mot à mot : « 222-33,222-33-2 » devenu
    « 222-33, 222-33-2 » est un seul remplacement, d'un mot par deux, et le
    morceau contient des chiffres — donc il ne serait pas « de pure forme ».

    Il faut donc comparer les deux côtés **une fois la forme retirée** : si le
    fond est identique, seule la typographie a bougé.
    """
    return sans_forme(avant) == sans_forme(apres)


def changement_de_fond(decoupe: list[dict[str, str]]) -> bool:
    """Y a-t-il au moins un changement qui ne soit pas de pure forme ?"""
    return any(m["role"] != "egal" and not m["forme"] for m in decoupe)


def au_caractere(avant: str, apres: str) -> list[dict]:
    """Une retouche de forme, montrée **une seule fois**, caractère par caractère.

    Montrer « ~~I-Sont~~ **I- Sont** » oblige à lire le mot deux fois pour
    trouver une espace. On descend donc au caractère et on écrit le mot une
    fois, en ne marquant que ce qui bouge :

        « I-Sont » → « I- Sont »   donne   I-[espace ajoutée]Sont
        « 222-33 » → « 22233 »     donne   222[tiret retiré]33

    `colle` dit que le morceau se rattache au précédent sans espace : sans lui,
    l'affichage insérerait des espaces au milieu des mots.
    """
    decoupe = []
    for operation, i1, i2, j1, j2 in difflib.SequenceMatcher(None, avant, apres).get_opcodes():
        if operation in ("equal", "delete", "replace") and avant[i1:i2]:
            decoupe.append({"role": "egal" if operation == "equal" else "retire",
                            "texte": avant[i1:i2], "forme": operation != "equal",
                            "colle": bool(decoupe)})
        if operation in ("insert", "replace") and apres[j1:j2]:
            decoupe.append({"role": "ajoute", "texte": apres[j1:j2],
                            "forme": True, "colle": bool(decoupe)})
    return decoupe


def morceaux(avant: str, apres: str) -> list[dict]:
    """Le texte découpé en morceaux « égal », « retiré », « ajouté ».

    Comparaison mot à mot avec `difflib`, bibliothèque standard : aucun modèle
    de langage, aucun coût, et un résultat qui ne dépend que des deux textes.

    Une exception : un remplacement qui ne touche que la ponctuation ou les
    espaces descend au caractère (voir `au_caractere`), pour que le lecteur
    n'ait pas à comparer deux fois le même mot.
    """
    a, b = normaliser(avant).split(), normaliser(apres).split()
    decoupe = []
    for operation, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        cote_a, cote_b = " ".join(a[i1:i2]), " ".join(b[j1:j2])
        if operation == "equal":
            decoupe.append({"role": "egal", "texte": cote_a, "forme": False,
                            "colle": False})
            continue
        # Le jugement « de pure forme » porte sur l'opération entière, pas sur
        # chaque morceau : un remplacement se juge en comparant ses deux côtés.
        forme = (remplacement_de_forme(cote_a, cote_b) if operation == "replace"
                 else est_de_forme(cote_a or cote_b))
        if operation == "replace" and forme:
            decoupe.extend(au_caractere(cote_a, cote_b))
            continue
        if operation in ("delete", "replace") and cote_a:
            decoupe.append({"role": "retire", "texte": cote_a, "forme": forme,
                            "colle": False})
        if operation in ("insert", "replace") and cote_b:
            decoupe.append({"role": "ajoute", "texte": cote_b, "forme": forme,
                            "colle": False})
    return [m for m in decoupe if m["texte"]]


def part_commune(avant: str, apres: str) -> int:
    """La part de texte inchangée, en pourcentage — 100 quand rien ne bouge."""
    a, b = normaliser(avant).split(), normaliser(apres).split()
    if not a and not b:
        return 100
    return round(100 * difflib.SequenceMatcher(None, a, b).ratio())


def date_d_effet(quoi: str, debut: str | None, fin: str | None) -> str | None:
    """Quand ce changement prend effet — la date qui intéresse le lecteur.

    Ce n'est pas la même selon ce que la loi fait. Une modification crée une
    rédaction, et c'est son **début** qui compte. Une abrogation, elle, ne crée
    rien : elle met **fin** à une rédaction, et c'est cette fin qui est la date
    de l'abrogation.

    Prendre le début dans les deux cas donnait des absurdités : l'article 1700
    du code général des impôts, abrogé par la loi de finances de 2025,
    s'affichait comme entrant en vigueur le 1er juillet **1979** — la date à
    laquelle le texte abrogé avait commencé à s'appliquer.

    Avec cette règle, sur 2 261 changements datés, seuls 34 (1,5 %) prennent
    effet avant la promulgation de leur loi — et ce sont de vraies
    rétroactivités : une loi de finances votée en février abroge des taxes au
    1er janvier. C'est un fait à montrer, pas une anomalie à masquer.

    Rend `None` quand la date n'est **pas encore fixée** (`SANS_DATE`) : la loi
    renvoie à un décret qui n'est pas paru. Afficher « 22 février 2222 » serait
    absurde ; le dire est utile.
    """
    date = fin if quoi == "ABROGE" else debut
    return None if not date or date in (SANS_DATE, SANS_FIN) else date


def etat_du_precedent(precedent: str | None, texte_avant: str | None) -> str:
    """Dit **pourquoi** il n'y a pas de comparaison, quand il n'y en a pas.

    Trois cas, qu'il serait malhonnête de confondre :

    - `connu` — on a la rédaction d'avant, on peut superposer ;
    - `aucun` — l'article n'en avait pas : la loi vient de le créer ;
    - `manquant` — il en avait une, et nous ne l'avons pas retrouvée dans les
      archives lues. C'est un trou dans nos données, pas un fait sur la loi,
      et l'afficher comme un « texte nouveau » ferait mentir l'application.
    """
    if texte_avant:
        return "connu"
    return "manquant" if precedent else "aucun"


def url_legifrance(identifiant: str) -> str:
    """L'adresse publique d'une rédaction, pour qui veut lire la source.

    Légifrance refuse les robots (403, pare-feu Cloudflare, mesuré le
    2026-09-01), mais un lecteur qui clique passe sans difficulté.
    """
    return f"https://www.legifrance.gouv.fr/codes/article_lc/{identifiant}"
