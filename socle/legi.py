"""Lecture du droit consolidé (jeu de données LEGI) : ce qu'une loi change.

Ce module ne fait que lire et comparer. Il ne télécharge rien de sa propre
initiative et n'écrit dans aucune base : `recuperer_legi.py` s'en charge.

**Ce qu'on cherche.** Quand une loi modifie un article de code, LEGI publie la
nouvelle rédaction *et* garde l'ancienne. On peut donc superposer les deux et
montrer exactement ce qui change. Le raccordement avec nos dossiers est direct :
chaque rédaction porte le numéro de la loi qui l'a produite.

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


def version_precedente(toutes: list[dict[str, str]], debut: str) -> str | None:
    """La rédaction d'« avant » : celle qui se termine quand la nôtre commence.

    C'est **la** règle du module, et la règle évidente est fausse. Prendre
    « celle d'avant dans la liste » désigne parfois une rédaction mort-née :
    sur l'article 6 de la loi n° 2004-575, elle renvoyait à une version datée
    du 22 février 2222, jamais appliquée. La comparaison tombait alors à 13 %
    de texte commun — un avant/après spectaculaire et faux. Avec la règle
    ci-dessous : 97 %, et rien ne change pour les six autres articles de la
    même loi (mesuré le 2026-09-01).
    """
    for version in toutes:
        if version.get("fin") == debut and not est_mort_ne(version.get("etat", "")):
            return version.get("id")
    return None


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
    toutes = versions(xml)
    return {
        "id": champ(champ(xml, "META_COMMUN"), "ID"),
        "numero": normaliser(champ(xml, "NUM")),
        "ou": ou_se_trouve(xml, debut),
        "etat": champ(xml, "ETAT"),
        "debut": debut,
        "fin": champ(xml, "DATE_FIN"),
        "texte": nettoyer(champ(xml, "BLOC_TEXTUEL")),
        "nota": nettoyer(champ(xml, "NOTA")),
        "precedent": version_precedente(toutes, debut),
        "changements": changements(xml),
    }


# ---------------------------------------------------------------------------
# Comparer deux rédactions
# ---------------------------------------------------------------------------

def morceaux(avant: str, apres: str) -> list[dict[str, str]]:
    """Le texte découpé en morceaux « égal », « retiré », « ajouté ».

    Comparaison mot à mot avec `difflib`, bibliothèque standard : aucun modèle
    de langage, aucun coût, et un résultat qui ne dépend que des deux textes.
    """
    a, b = normaliser(avant).split(), normaliser(apres).split()
    decoupe = []
    for operation, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if operation in ("equal", "delete"):
            decoupe.append({"role": "egal" if operation == "equal" else "retire",
                            "texte": " ".join(a[i1:i2])})
        if operation in ("insert", "replace"):
            if operation == "replace":
                decoupe.append({"role": "retire", "texte": " ".join(a[i1:i2])})
            decoupe.append({"role": "ajoute", "texte": " ".join(b[j1:j2])})
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
