"""Ce qu'une loi promulguée change au droit en vigueur : les articles touchés, ajoutés, retouchés, et leur texte comparé.
"""
from __future__ import annotations

import re
import sqlite3
import legi
from publication.commun import BASE_LEGI
from publication.commun import ecrire
import extraction
import sys
from publication.contexte import Publication


# Ce qu'une loi fait à un article, dit en clair. La clé est le mot de LEGI ;
# rien n'est reformulé, seulement traduit une fois pour toutes.
ACTIONS = {"MODIFIE": "modifié", "CREE": "créé", "ABROGE": "abrogé",
           "TRANSFERE": "transféré", "DEPLACE": "déplacé",
           # Un article que la loi a écrit pour elle-même. « créé » est déjà
           # pris par un article créé dans un code — les deux ne se rangent
           # pas au même endroit à l'écran, ils ne portent pas le même mot.
           legi.AJOUTE: "nouveau"}


# Du plus parlant au moins parlant, quand une loi en fait plusieurs au même
# article : ce que le lecteur retient, c'est que le contenu a changé.
PRIORITE = ("MODIFIE", "CREE", "ABROGE", "TRANSFERE", "DEPLACE")


def action_retenue(actions: list[str]) -> str:
    """Le mot à écrire sur la pastille, quand une loi en fait plusieurs.

    `AJOUTE` passe avant tout le reste : un article que la loi a écrit se range
    dans une autre liste que les articles changés, et les deux ne peuvent pas
    porter le même mot. Le cas ne devrait pas se présenter — un ajout n'a pas de
    rédaction d'avant, donc rien n'a pu le modifier — mais l'écrire évite que
    l'affichage dépende de ce raisonnement.
    """
    if legi.AJOUTE in actions:
        return legi.AJOUTE
    return min(actions, key=lambda a: PRIORITE.index(a) if a in PRIORITE
                                      else len(PRIORITE))


def ouvrir_legi() -> sqlite3.Connection | None:
    """La base du droit consolidé, si elle a été construite.

    Elle est facultative : sans elle, tout le reste se publie normalement et
    l'application n'affiche simplement pas ce que les lois changent. Une passe
    de quinze minutes ne doit pas pouvoir empêcher la publication du matin.
    """
    if not BASE_LEGI.exists():
        return None
    cx = sqlite3.connect(f"file:{BASE_LEGI}?mode=ro", uri=True, timeout=30)
    cx.row_factory = sqlite3.Row
    return cx


def changements_par_loi(legi_cx: sqlite3.Connection | None,
                        forme_seule: set[str] | None = None) -> dict[str, dict]:
    """Pour chaque loi, de quoi remplir sa carte : combien d'articles, et quand.

    « Quand » est la question qui manquait : une loi promulguée peut ne
    s'appliquer que plus tard, et parfois en plusieurs fois. On publie donc les
    dates d'entrée en vigueur telles quelles, sans les interpréter.
    """
    if legi_cx is None:
        return {}
    ecartes = forme_seule or set()
    resume: dict[str, dict] = {}
    # Le total compte les **articles**, pas les liens : une même loi peut à la
    # fois modifier et déplacer un article, ce qui ferait deux liens et un seul
    # article. « Voir les 7 articles » doit dire vrai. Et il ne compte pas les
    # articles dont seule la ponctuation a bougé.
    par_loi_articles: dict[str, set[str]] = {}
    par_loi_actions: dict[str, dict[str, set[str]]] = {}
    par_loi_dates: dict[str, dict[str, set[str]]] = {}
    retouches: dict[str, set[str]] = {}
    ajouts: dict[str, set[str]] = {}
    for ligne in legi_cx.execute(
            "SELECT c.loi, c.quoi, c.redaction_id, r.debut, r.fin"
            " FROM changement c JOIN redaction r ON r.id = c.redaction_id"):
        loi, article = ligne["loi"], ligne["redaction_id"]
        # Ce que la loi ajoute est compté à part, et n'entre ni dans `total`,
        # ni dans `actions`, ni dans `dates`. Ces trois champs disent depuis
        # toujours « ce qu'elle change dans le droit d'avant » ; y verser des
        # articles neufs changerait le sens d'un chiffre déjà publié.
        if ligne["quoi"] == legi.AJOUTE:
            ajouts.setdefault(loi, set()).add(article)
            continue
        if article in ecartes:
            retouches.setdefault(loi, set()).add(article)
            continue
        par_loi_articles.setdefault(loi, set()).add(article)
        par_loi_actions.setdefault(loi, {}).setdefault(ligne["quoi"], set()).add(article)
        effet = legi.date_d_effet(ligne["quoi"], ligne["debut"], ligne["fin"])
        if effet:
            par_loi_dates.setdefault(loi, {}).setdefault(effet, set()).add(article)

    for loi in set(par_loi_articles) | set(retouches) | set(ajouts):
        resume[loi] = {
            "total": len(par_loi_articles.get(loi, ())),
            "actions": {q: len(s) for q, s in par_loi_actions.get(loi, {}).items()},
            "dates": [{"date": d, "articles": len(s)}
                      for d, s in sorted(par_loi_dates.get(loi, {}).items())],
            # Comptés à part, et dits à part : ce sont des articles que la loi
            # touche sans rien changer au fond.
            "retouches": len(retouches.get(loi, ())),
            # Ses propres articles : du droit nouveau, sans avant/après.
            "ajouts": len(ajouts.get(loi, ())),
        }
    return resume


def par_numero_d_article(numero: str | None) -> tuple:
    """De quoi ranger « 1, 2, 10 » dans cet ordre, et non « 1, 10, 2 ».

    Les articles d'une loi se numérotent simplement, mais en base dix : un tri
    alphabétique met l'article 10 avant l'article 2. Les suffixes existent
    (« 3-1 », « 12 bis »), d'où le découpage en morceaux plutôt qu'un `int`.
    """
    morceaux = re.split(r"(\d+)", numero or "")
    return tuple((1, int(m)) if m.isdigit() else (0, m) for m in morceaux if m)


def article_publie(ligne, quoi: str, actions: list[str]) -> dict:
    """Ce qu'on publie d'un article dans la liste d'une loi : de quoi choisir,
    jamais le texte lui-même."""
    avant, apres = ligne["avant"], ligne["texte"] or ""
    return {
        "id": ligne["id"], "numero": ligne["numero"], "quoi": quoi,
        "action": ACTIONS.get(quoi, quoi),
        "actions": [ACTIONS.get(a, a) for a in actions] if len(actions) > 1 else None,
        "effet": legi.date_d_effet(quoi, ligne["debut"], ligne["fin"]),
        "mots": len(apres.split()),
        "commun": legi.part_commune(avant, apres) if avant else None,
        "avant": legi.etat_du_precedent(ligne["precedent"], ligne["avant"]),
        # Six rédactions sur 5 091 n'ont aucun numéro : les états et
        # annexes des lois de finances. On leur donne pour nom le début de
        # leur propre texte — c'est la liste qui, sinon, afficherait
        # « Article » suivi de rien. Écrit seulement dans ce cas.
        **({"intitule": legi.intitule_de_secours(apres)}
           if not ligne["numero"] else {}),
        # La source publie parfois l'article avant d'en avoir saisi le
        # texte. Le drapeau ne s'écrit que dans ce cas — rare — pour ne pas
        # ajouter un « false » à chacun des 5 880 articles publiés.
        #
        # **Il vaut pour tous les articles, pas seulement les nouveaux.**
        # Si la source livrait ainsi une rédaction *modifiée*, la
        # comparaison opposerait le texte d'avant à cette phrase d'attente
        # et annoncerait un article entièrement réécrit. Jamais vu — 0 sur
        # 605 rédactions changées, mesuré le 2026-09-03 — et c'est
        # exactement le genre de cas qu'il ne faut pas laisser dépendre
        # d'une mesure sur deux archives.
        **({"enAttente": True} if legi.est_en_attente(apres) else {}),
    }


def articles_de_la_loi(legi_cx: sqlite3.Connection, numero: str,
                       forme_seule: set[str] | None = None
                       ) -> tuple[list[dict], list[dict], list[dict]]:
    """Ce qu'une loi change, ce qu'elle ajoute, et ce qu'elle a seulement retouché.

    **Trois listes, et non une seule.** Ce qu'elle change dans le droit d'avant
    se montre en superposant les deux rédactions ; ce qu'elle ajoute — ses
    propres articles — n'a pas d'avant, donc rien à superposer. Les mélanger
    obligerait à afficher une « part de texte changé » qui n'a aucun sens pour
    un article neuf.

    Aucune des listes ne porte de texte : elles servent à choisir. Le texte
    entier et sa comparaison sont dans un fichier par article, chargé au clic.
    Sans cette séparation, la loi de finances pour 2025 — 1 053 articles —
    ferait un fichier de plusieurs méga-octets pour un écran de téléphone.
    """
    ecartes = forme_seule or set()
    groupes: dict[str, list] = {}
    retouches: list[dict] = []
    ajouts: list[dict] = []
    for ligne in legi_cx.execute(
            "SELECT r.id, r.numero, r.ou, r.debut, r.fin, r.texte, r.precedent,"
            " GROUP_CONCAT(DISTINCT c.quoi) actions,"
            " (SELECT texte FROM redaction WHERE id = r.precedent) avant"
            " FROM changement c JOIN redaction r ON r.id = c.redaction_id"
            " WHERE c.loi = ? GROUP BY r.id ORDER BY r.ou, r.numero", (numero,)):
        avant, apres = ligne["avant"], ligne["texte"] or ""
        # Une loi peut faire deux choses au même article — le modifier et le
        # déplacer. Un seul mot tient sur la pastille : on garde le plus
        # parlant, et l'ordre de PRIORITE dit lequel.
        actions = (ligne["actions"] or "").split(",")
        quoi = action_retenue(actions)
        article = article_publie(ligne, quoi, actions)
        if legi.AJOUTE in actions:
            ajouts.append({**article, "ou": ligne["ou"] or "Textes non codifiés"})
        elif ligne["id"] in ecartes:
            retouches.append({**article, "ou": ligne["ou"] or "Textes non codifiés"})
        else:
            groupes.setdefault(ligne["ou"] or "Textes non codifiés", []).append(article)
    ajouts.sort(key=lambda a: par_numero_d_article(a["numero"]))
    return ([{"ou": ou, "articles": articles} for ou, articles in groupes.items()],
            retouches, ajouts)


def article_compare(legi_cx: sqlite3.Connection, identifiant: str) -> dict:
    """Un article : son texte entier, découpé en morceaux égaux, retirés, ajoutés."""
    ligne = legi_cx.execute(
        "SELECT r.*, (SELECT texte FROM redaction WHERE id = r.precedent) avant,"
        " (SELECT GROUP_CONCAT(DISTINCT quoi) FROM changement"
        "  WHERE redaction_id = r.id) actions"
        " FROM redaction r WHERE r.id = ?", (identifiant,)).fetchone()
    avant, apres = ligne["avant"], ligne["texte"] or ""
    actions = (ligne["actions"] or "").split(",")
    quoi = action_retenue(actions)
    return {
        "id": ligne["id"], "numero": ligne["numero"], "ou": ligne["ou"],
        "quoi": quoi, "action": ACTIONS.get(quoi, quoi),
        "effet": legi.date_d_effet(quoi, ligne["debut"], ligne["fin"]),
        "debut": ligne["debut"], "fin": ligne["fin"], "etat": ligne["etat"],
        "nota": ligne["nota"] or None,
        "commun": legi.part_commune(avant, apres) if avant else None,
        # Sans rédaction d'avant, il n'y a rien à comparer : le texte est d'un
        # seul tenant. Le champ `forme` reste présent pour que l'affichage
        # n'ait pas à se demander s'il existe.
        "morceaux": legi.morceaux(avant, apres) if avant
                    else [{"role": "ajoute" if not ligne["precedent"] else "egal",
                           "texte": apres, "forme": False}],
        "avant": legi.etat_du_precedent(ligne["precedent"], ligne["avant"]),
        # Voir `articles_de_la_loi` : les deux ne s'écrivent qu'au besoin.
        **({"intitule": legi.intitule_de_secours(apres)}
           if not ligne["numero"] else {}),
        **({"enAttente": True} if legi.est_en_attente(apres) else {}),
        "source": legi.url_legifrance(ligne["id"]),
    }


def ecrire_changements(p: Publication) -> None:
    """Ce que chaque loi change au droit : une liste par loi, un fichier par article."""
    cx = p.cx
    sortie = p.sortie
    genere_le = p.genere_le
    tailles = p.tailles
    legi_cx = p.legi_cx
    forme_seule = p.forme_seule
    change = p.change
    # Ce que chaque loi change au droit. Deux niveaux : la liste des articles,
    # qui ne porte aucun texte et sert à choisir ; puis un fichier par article,
    # chargé au clic. Sans cette séparation, la loi de finances pour 2025 — 574
    # articles — ferait plusieurs méga-octets pour un seul écran.
    if legi_cx is not None:
        listes, fiches, lois_couvertes = 0, 0, 0
        for l in cx.execute(
                "SELECT uid, loi_numero FROM dossier"
                " WHERE statut = ? AND loi_numero IS NOT NULL AND loi_numero != ''",
                (extraction.PROMULGUE,)):
            groupes, retouches, ajouts = articles_de_la_loi(
                legi_cx, l["loi_numero"], forme_seule)
            if not groupes and not retouches and not ajouts:
                continue
            lois_couvertes += 1
            listes += ecrire(sortie / "changements" / f'{l["uid"]}.json', {
                "genereLe": genere_le, "loi": l["loi_numero"],
                **change.get(l["loi_numero"], {}),
                "groupes": groupes,
                # Les articles retouchés sans changement de fond : listés à
                # part, consultables, mais hors du compte des modifications.
                "articlesRetouches": retouches,
                # Ce que la loi ajoute : ses propres articles. Une liste à
                # part, parce qu'ils n'ont pas d'avant — il n'y a rien à
                # superposer, seulement un texte à lire.
                "articlesAjoutes": ajouts,
            })
            for article in ([a for g in groupes for a in g["articles"]]
                            + retouches + ajouts):
                fiches += ecrire(
                    sortie / "changements" / l["uid"] / f'{article["id"]}.json',
                    article_compare(legi_cx, article["id"]))
        if listes:
            tailles["changements/*.json"] = listes
            tailles["changements/<loi>/*.json"] = fiches
        if lois_couvertes != len(change):
            print(f"{len(change) - lois_couvertes} lois du droit consolidé sans "
                  "dossier correspondant : la base du Parlement est-elle à jour ?",
                  file=sys.stderr)
