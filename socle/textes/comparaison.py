"""Comparer deux versions d'un texte, article par article : le numéro, les mentions, les sauts d'alinéa, les amendements rapprochés, la version à jour — tout ce qui se calcule à la publication, et ne relit rien.
"""
from __future__ import annotations

import collections
import re
import legi


# « (Nouveau) », « (Supprimé) », « (Non modifié) », « (Conforme) » : la source
# annonce l'état de l'article, soit dans son titre, soit dans un paragraphe
# juste en dessous. Ce n'est pas du texte de loi — laissée dans le corps, la
# mention « (Non modifié) » s'affiche comme un ajout de la commission alors
# qu'elle dit exactement le contraire.
#
# **« Conforme » a été ajouté le 2026-09-21**, et son absence coûtait cher : la
# mention restait dans le corps de l'article, donc l'article s'affichait comme
# réduit à ce seul mot. Mesuré sur les deux textes lus ce jour-là, 8 articles
# sur 75 de la dernière version étaient dans ce cas.
MENTION = re.compile(
    r"^\(\s*(non modifiés?|supprimés?|nouveaux?|conformes?)[^)]*\)\s*", re.I)


MENTION_TITRE = re.compile(
    r"\(\s*(non modifiés?|supprimés?|nouveaux?|conformes?)[^)]*\)", re.I)


# Les mentions qui disent « cet article ne change pas, et je ne le réimprime
# pas ». Sa rédaction est celle de la version d'avant, et il faut aller la
# chercher là-bas : la comparer à un texte vide le montrerait entièrement
# supprimé, c'est-à-dire l'inverse de ce que la source dit.
NON_REPRODUIT = ("conforme", "non modifié")


# Où commence l'intitulé d'un article, après son numéro : aux deux-points, ou
# au premier mot qui commence par une capitale suivie de minuscules. « bis »,
# « A », « PREMIER » ne sont pas des intitulés ; « Rectification » en est un.
# La source oublie parfois les deux-points (« ARTICLE 23 Instauration… »).
INTITULE = re.compile(r"\s+(?::|(?=[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ’']))")


def numero(titre: str | None) -> str:
    """« Article PREMIER bis (nouveau) » → « 1er bis ».

    Deux versions d'un texte ne s'apparient que par ce numéro : un document ne
    porte aucun identifiant stable d'une version à l'autre. Les amendements
    écrivent « Article PREMIER » là où le document écrit « Article 1er » —
    sans cette normalisation, 137 rapprochements sur 144 échouaient.
    """
    t = MENTION_TITRE.sub("", titre or "")
    t = re.sub(r"^Articles?\s+", "", t.strip(), flags=re.I)
    # Les textes budgétaires nomment leurs articles : « ARTICLE 2 : Soutenir le
    # travail… », « Article 2 Rectification de l’ONDAM ». Le numéro s'arrête à
    # l'intitulé — les amendements, eux, écrivent « Article 2 ».
    t = INTITULE.split(t, maxsplit=1)[0]
    # Le document écrit « 1er » avec un « er » en exposant, qui ressort détaché.
    t = re.sub(r"\b1\s*(er|ᵉʳ)\b", "1er", t, flags=re.I)
    t = re.sub(r"^premier\b", "1er", t.strip(), flags=re.I)
    # Le gabarit des lois de finances écrit « ARTICLE 1 », et leurs amendements
    # « Article 1 », là où les versions suivantes écrivent « Article 1er » :
    # sans cela, l'article 1 sortait « retiré » et « nouveau » à la fois.
    t = re.sub(r"^1(?=\s|$)", "1er", t)
    return re.sub(r"\s+", " ", t).strip().lower()


def titre_propre(titre: str) -> str:
    """« Article 1 er » → « Article 1er ».

    Le « er » est en exposant dans le document ; il ressort détaché quand on
    aplatit le HTML. Le recoller n'est pas une réécriture : c'est restituer ce
    que la source imprime.
    """
    return re.sub(r"\b1\s+(er|ᵉʳ)\b", "1er", titre or "", flags=re.I)


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
                          ("nouveau", "nouveau"), ("nouveaux", "nouveau"),
                          ("conforme", "conforme")):
        if mot.startswith(debut):
            return propre
    return mot


def sans_mention(texte: str) -> str:
    """Le texte de l'article, sa mention d'état retirée."""
    return MENTION.sub("", (texte or "").strip(), count=1).strip()


def _espaces_de_saut(texte: str) -> tuple[str, set[int]]:
    """Le texte tel que `legi.morceaux` le compare — ses mots séparés par une
    espace — et la position des espaces qui, dans l'original, étaient un saut
    d'alinéa."""
    mots, sauts, pos, fin = [], set(), 0, 0
    for m in re.finditer(r"\S+", texte):
        if mots:
            if "\n" in texte[fin:m.start()]:
                sauts.add(pos)
            pos += 1
        mots.append(m.group(0))
        pos += len(m.group(0))
        fin = m.end()
    return " ".join(mots), sauts


def avec_les_alineas(decoupe: list[dict], avant: str, apres: str) -> list[dict]:
    """Les sauts d'alinéa remis dans une comparaison qui les ignore.

    `legi.morceaux` compare mot à mot, et c'est voulu : un alinéa coupé
    autrement n'est pas un changement de fond, et la comparaison du droit
    consolidé reste celle qu'elle était. Mais l'écran perdait les sauts de
    ligne. On les replace ici **sans rien changer à la comparaison** : chaque
    morceau est un extrait, dans l'ordre, du texte d'avant (un retrait), du
    texte d'après (un ajout) ou des deux (un passage égal) ; on le suit
    caractère par caractère, et une espace redevient un saut là où l'original
    en portait un — celui d'après pour un passage égal. `saut` dit qu'un
    morceau ouvre un alinéa.
    """
    cotes = {"avant": _espaces_de_saut(avant), "apres": _espaces_de_saut(apres)}
    lu = {"avant": 0, "apres": 0}
    dette: set[str] = set()
    sortie = []
    for m in decoupe:
        m = dict(m)
        lus = (("avant", "apres") if m["role"] == "egal"
               else ("avant",) if m["role"] == "retire" else ("apres",))
        ref = lus[-1]
        texte, sauts = cotes[ref]
        # Entre deux groupes de morceaux, la comparaison a mangé l'espace qui
        # séparait leurs mots — **de chaque côté**, et chaque côté la doit à
        # la première lecture qu'il fait dans le groupe : une retouche au
        # caractère peut commencer par un retrait, que suit un ajout collé.
        if not m.get("colle"):
            dette = {"avant", "apres"}
        for cote in lus:
            if cote in dette:
                dette.discard(cote)
                if lu[cote] and cotes[cote][0][lu[cote]:lu[cote] + 1] == " ":
                    if cote == ref and lu[cote] in sauts and not m.get("colle"):
                        m["saut"] = True
                    lu[cote] += 1
        debut = lu[ref]
        m["texte"] = "".join("\n" if debut + k in sauts else c
                             for k, c in enumerate(m["texte"]))
        for cote in lus:
            lu[cote] += len(m["texte"])
        sortie.append(m)
    return sortie


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
        elif ancien.split() == texte.split():
            # Les mots, pas les espaces : un document relu par les règles d'un
            # alinéa par ligne, comparé à un document qui ne l'est pas encore,
            # ne diffère que par ses sauts de ligne — ce n'est pas un changement.
            quoi = "identique"
        else:
            quoi = "modifie"
        lignes.append({
            "numero": num,
            "titre": titre_propre(titre),
            "quoi": quoi,
            "etat": etat(titre, brut),
            "texte": texte,
            "morceaux": (avec_les_alineas(legi.morceaux(ancien, texte), ancien, texte)
                         if quoi == "modifie" else []),
            "commun": legi.part_commune(ancien, texte) if quoi == "modifie" else None,
        })
    vus = {l["numero"] for l in lignes}
    for titre, brut in avant.items():
        num = numero(titre)
        if num in vus:
            continue
        lignes.append({"numero": num, "titre": titre_propre(titre), "quoi": "retire",
                       "etat": None, "texte": sans_mention(brut),
                       "morceaux": [], "commun": None})
    return lignes


def premiere_version(articles: dict[str, str]) -> list[dict]:
    """La version déposée : rien à comparer, seulement un texte à lire.

    Même forme que `comparer`, pour que l'écran n'ait qu'une façon de lire une
    version — celle-ci n'a simplement aucun morceau à colorer.
    """
    return [{"numero": numero(titre), "titre": titre_propre(titre), "quoi": "initial",
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


def version_a_jour(suite: list[dict[str, str]]) -> dict[str, str]:
    """Le texte de chaque article tel qu'il se lit après la dernière étape.

    `suite` est la liste des versions dans l'ordre du parcours, chacune étant
    un dictionnaire `{titre: texte}`.

    **Une version tardive ne réimprime pas les articles déjà accordés** : elle
    imprime « (Conforme) » ou « (Non modifié) » à leur place. Les comparer au
    texte déposé les montrerait entièrement supprimés, ce qui est le contraire
    de ce que la source dit. On reprend donc leur rédaction **à la dernière
    version qui les imprime**. Ce n'est pas reconstituer du texte : c'est
    suivre l'instruction que la source écrit noir sur blanc.

    Mesuré le 2026-09-21 : 23 articles sur 75 de la dernière version étaient
    vides ou réduits à leur mention.

    Un article « (Supprimé) » est bien supprimé : sa rédaction ne revient pas.
    Un article qu'une version tardive ne cite plus du tout non plus — il n'est
    pas dans le résultat, et `comparer` le dira retiré.
    """
    if not suite:
        return {}
    ancien: dict[str, str] = {}
    for articles in suite[:-1]:
        for titre, brut in articles.items():
            if sans_mention(brut).strip():
                ancien[numero(titre)] = brut
    a_jour = {}
    for titre, brut in suite[-1].items():
        repris = ancien.get(numero(titre))
        if (etat(titre, brut) in NON_REPRODUIT
                and not sans_mention(brut).strip() and repris):
            # Le titre reste celui de la dernière version — c'est lui qui
            # numérote l'article aujourd'hui — mais le corps vient d'avant.
            a_jour[titre] = sans_mention(repris)
        else:
            a_jour[titre] = brut
    return a_jour


def amendements_du_parcours(etapes: list[dict], ligne: dict) -> list[dict]:
    """Tous les amendements adoptés sur cet article, d'un bout à l'autre.

    `etapes` est une liste de `{"quand": …, "index": …}`, dans l'ordre du
    parcours : `index` est celui qu'a construit `amendements_du_document` pour
    le document amendé à cette étape, et `quand` dit **qui** l'a amendé — la
    commission ou la séance.

    Le rapprochement reste celui de `amendements_de_l_article` : **par le
    numéro d'article, à chaque étape, jamais par le texte.** Il porte donc une
    hypothèse de plus que la comparaison d'une seule étape — qu'un numéro
    désigne le même article du dépôt à la fin. Chaque amendement part avec
    l'étape où il a été adopté, pour que l'écran puisse le dire au lieu de
    laisser croire à un changement d'un seul coup.

    Un même amendement ne peut pas apparaître deux fois : deux étapes ne
    partagent aucun document amendé.
    """
    trouves = []
    for etape in etapes:
        for a in amendements_de_l_article(etape["index"], ligne):
            trouves.append({**a, "quand": etape["quand"]})
    return trouves


def resume(lignes: list[dict]) -> dict[str, int]:
    """Combien d'articles modifiés, nouveaux, retirés, inchangés."""
    compte = collections.Counter(l["quoi"] for l in lignes)
    return {"modifies": compte["modifie"], "nouveaux": compte["nouveau"],
            "retires": compte["retire"], "identiques": compte["identique"],
            # La version déposée n'a rien à quoi se comparer : ses articles
            # sont comptés à part, et non comme des ajouts de la commission.
            "initiaux": compte["initial"], "total": len(lignes)}
