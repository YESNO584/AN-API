"""Le texte d'un projet ou d'une proposition de loi, version par version.

**Ce que ce module lit.** L'Assemblée publie le texte intégral de chaque
version d'un texte — celui qui est déposé, celui qui sort de la commission,
celui qui est adopté en séance — à une adresse qui se déduit de l'identifiant
du document :

    https://www.assemblee-nationale.fr/dyn/docs/PIONANR5L17B1794.raw

C'est le document Word de l'Assemblée converti en HTML. **Ce n'est pas du
JSON, et il n'en existe pas** : le JSON que publie l'Assemblée pour un document
est une fiche signalétique, dont le champ `divisions` est vide (mesuré le
2026-09-18 sur six documents de natures différentes). Mais ce HTML-ci est
*structuré*, ce qui est la seule chose qui compte : la classe du paragraphe dit
où commence un article, et les tableaux restent des tableaux.

**Les identifiants viennent de l'archive déjà téléchargée chaque matin.** Chaque
étape du parcours nomme le document qu'elle produit ou qu'elle examine
(`texteAssocie`, `texteAdopte`) : aucune devinette sur l'étape à laquelle
rattacher une version, et aucun appel réseau pour le savoir.

**Ce que ça couvre**, mesuré le 2026-09-18 sur les 2 219 textes de loi de la
législature : 1 749 ont au moins une version publiée par l'Assemblée — donc un
texte à lire — et **249 en ont au moins deux**, donc une comparaison possible.
Les 470 autres sont nés au Sénat, qui publie ses textes ailleurs.

**Les règles ci-dessous viennent toutes d'un défaut constaté**, jamais d'une
supposition. Voir `../docs/sources/textes-assemblee-html.md` pour les mesures.
"""

from __future__ import annotations

import collections
import html
import re

import legi

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

# « (Nouveau) », « (Supprimé) », « (Non modifié) » : la source annonce l'état
# de l'article, soit dans son titre, soit dans un paragraphe juste en dessous.
# Ce n'est pas du texte de loi — laissée dans le corps, la mention
# « (Non modifié) » s'affiche comme un ajout de la commission alors qu'elle dit
# exactement le contraire.
MENTION = re.compile(r"^\(\s*(non modifiés?|supprimés?|nouveaux?)[^)]*\)\s*", re.I)
MENTION_TITRE = re.compile(r"\(\s*(non modifiés?|supprimés?|nouveaux?)[^)]*\)", re.I)

BALISE = re.compile(r"<(p|h\d|table)([^>]*)>(.*?)</\1>", re.S)
CLASSE = re.compile(r'class="([^"]*)"')


def blocs(source: str) -> list[tuple[str, str, str]]:
    """Le document, paragraphe par paragraphe : (classe, texte, balise)."""
    corps = source[source.index("<body"):] if "<body" in source else source
    sortie = []
    for m in BALISE.finditer(corps):
        classe = CLASSE.search(m.group(2))
        texte = re.sub(r"<[^>]+>", " ", m.group(3))
        texte = html.unescape(texte).replace(" ", " ")
        texte = re.sub(r"[ \t\r\n]+", " ", texte).strip()
        sortie.append((classe.group(1) if classe else "", texte, m.group(1)))
    return sortie


def articles(source: str) -> dict[str, str]:
    """Le dispositif : {titre de l'article: son texte}, dans l'ordre du texte.

    L'exposé des motifs, la page de garde et la note de fin n'en font pas
    partie : tout ce qui précède le premier titre d'article est ignoré.
    """
    trouves: dict[str, str] = {}
    titre, morceaux = None, []
    for classe, texte, balise in blocs(source):
        if FIN_DU_TEXTE.match(classe):
            break
        debut = (classe.startswith(CLASSE_ARTICLE)
                 or (balise != "table" and DEBUT_ARTICLE.match(texte)))
        if debut:
            if titre is not None:
                trouves[titre] = " ".join(x for x in morceaux if x).strip()
            titre, morceaux = texte, []
        elif titre is not None and not classe.startswith(HORS_TEXTE):
            morceaux.append(texte)
    if titre is not None:
        trouves[titre] = " ".join(x for x in morceaux if x).strip()
    return trouves


def numero(titre: str | None) -> str:
    """« Article PREMIER bis (nouveau) » → « 1er bis ».

    Deux versions d'un texte ne s'apparient que par ce numéro : un document ne
    porte aucun identifiant stable d'une version à l'autre. Les amendements
    écrivent « Article PREMIER » là où le document écrit « Article 1er » —
    sans cette normalisation, 137 rapprochements sur 144 échouaient.
    """
    t = MENTION_TITRE.sub("", titre or "")
    t = re.sub(r"^Articles?\s+", "", t.strip(), flags=re.I)
    # Le document écrit « 1er » avec un « er » en exposant, qui ressort détaché.
    t = re.sub(r"\b1\s*(er|ᵉʳ)\b", "1er", t, flags=re.I)
    t = re.sub(r"^premier\b", "1er", t.strip(), flags=re.I)
    return re.sub(r"\s+", " ", t).strip().lower()


def racine(num: str) -> str:
    """« 1er bis a » → « 1er » : l'article auprès duquel un article est né.

    Un amendement qui crée un article se dépose « après l'article 1er » ; le
    document, lui, l'appellera « article 1er bis ». C'est le seul lien entre
    les deux.
    """
    m = re.match(r"^(\S+)", num or "")
    return m.group(1) if m else (num or "")


def etat(titre: str, texte: str) -> str | None:
    """« nouveau », « supprimé » ou « non modifié », si la source le dit.

    La mention est tantôt dans le titre — « Article 1er bis (nouveau) » —
    tantôt dans un paragraphe en tête de l'article — « (Non modifié) ».
    """
    m = MENTION_TITRE.search(titre or "") or MENTION.match((texte or "").strip())
    if not m:
        return None
    mot = m.group(1).lower()
    for debut, propre in (("non modifi", "non modifié"), ("supprim", "supprimé"),
                          ("nouveau", "nouveau"), ("nouveaux", "nouveau")):
        if mot.startswith(debut):
            return propre
    return mot


def sans_mention(texte: str) -> str:
    """Le texte de l'article, sa mention d'état retirée."""
    return MENTION.sub("", (texte or "").strip(), count=1).strip()


def comparer(avant: dict[str, str], apres: dict[str, str]) -> list[dict]:
    """Deux versions d'un texte → une ligne par article, avec ce qui a changé.

    Rend aussi les articles que la nouvelle version ne porte plus : un article
    supprimé en cours de route est un changement, pas une absence.
    """
    precedent = {numero(t): sans_mention(v) for t, v in avant.items()}
    lignes = []
    for titre, brut in apres.items():
        num, texte = numero(titre), sans_mention(brut)
        ancien = precedent.get(num)
        if ancien is None:
            quoi = "nouveau"
        elif ancien == texte:
            quoi = "identique"
        else:
            quoi = "modifie"
        lignes.append({
            "numero": num,
            "titre": titre,
            "quoi": quoi,
            "etat": etat(titre, brut),
            "texte": texte,
            "morceaux": legi.morceaux(ancien, texte) if quoi == "modifie" else [],
            "commun": legi.part_commune(ancien, texte) if quoi == "modifie" else None,
        })
    vus = {l["numero"] for l in lignes}
    for titre, brut in avant.items():
        num = numero(titre)
        if num in vus:
            continue
        lignes.append({"numero": num, "titre": titre, "quoi": "retire",
                       "etat": None, "texte": sans_mention(brut),
                       "morceaux": [], "commun": None})
    return lignes


def premiere_version(articles: dict[str, str]) -> list[dict]:
    """La version déposée : rien à comparer, seulement un texte à lire.

    Même forme que `comparer`, pour que l'écran n'ait qu'une façon de lire une
    version — celle-ci n'a simplement aucun morceau à colorer.
    """
    return [{"numero": numero(titre), "titre": titre, "quoi": "initial",
             "etat": etat(titre, brut), "texte": sans_mention(brut),
             "morceaux": [], "commun": None}
            for titre, brut in articles.items()]


def amendements_du_document(amendements) -> dict[tuple[str, str], list[dict]]:
    """Les amendements adoptés, rangés par (numéro d'article, position).

    La position est celle que donne la source : « A » sur l'article lui-même,
    « Après » ou « Avant » pour un amendement qui **crée** un article à côté.
    C'est ce champ qui explique les articles « bis (nouveau) » : ils ne
    viennent pas d'un amendement sur l'article X, mais d'un amendement déposé
    après lui.
    """
    index: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    for a in amendements:
        if (a.get("division") or {}).get("type") != "ARTICLE":
            continue
        cle = (numero((a.get("division") or {}).get("article")),
               (a.get("division") or {}).get("ou") or "A")
        index[cle].append(a)
    return dict(index)


def amendements_de_l_article(index: dict, ligne: dict) -> list[dict]:
    """Les amendements adoptés que la source relie à cet article.

    **Le rapprochement se fait par le numéro d'article, jamais par le texte.**
    On ne dira donc pas « ce mot vient de cet amendement » : il faudrait
    interpréter l'instruction de l'amendement pour le deviner, ce qui
    reviendrait à fabriquer du texte de loi.

    Mesuré le 2026-09-18 : 420 amendements adoptés sur 470 tombent sur un
    article qui a réellement changé, et 2 sur un article resté identique au mot
    près. Le rapprochement est donc presque toujours juste — et souvent
    incomplet : 31 % des changements n'ont aucun amendement adopté sur leur
    article, et l'écran doit le dire.
    """
    num = ligne["numero"]
    if ligne["quoi"] == "nouveau":
        # Un article apparu porte le numéro de son voisin : « 1er bis » naît
        # d'un amendement déposé après l'article 1er.
        base = racine(num)
        if base != num:
            return index.get((base, "Après"), []) + index.get((base, "Avant"), [])
    return index.get((num, "A"), [])


def resume(lignes: list[dict]) -> dict[str, int]:
    """Combien d'articles modifiés, nouveaux, retirés, inchangés."""
    compte = collections.Counter(l["quoi"] for l in lignes)
    return {"modifies": compte["modifie"], "nouveaux": compte["nouveau"],
            "retires": compte["retire"], "identiques": compte["identique"],
            # La version déposée n'a rien à quoi se comparer : ses articles
            # sont comptés à part, et non comme des ajouts de la commission.
            "initiaux": compte["initial"], "total": len(lignes)}
