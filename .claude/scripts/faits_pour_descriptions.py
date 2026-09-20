#!/usr/bin/env python3
"""Ce que chaque loi décide, tiré du texte réel de ses articles.

Écrire la description d'une loi à partir de son titre donne une phrase creuse :
« Projet de loi portant diverses dispositions d'adaptation au droit de l'Union
européenne » ne dit rien. La matière est un niveau plus bas — dans le texte des
articles — et les fichiers publiés la portent :

    changements/<uid>.json          la liste des articles, sans texte
    changements/<uid>/<id>.json     un article, avec son texte découpé en
                                    morceaux « égal », « retiré », « ajouté »

**Les morceaux « ajouté » sont l'or de ce fichier** : ce sont, mot pour mot,
les phrases que la loi écrit dans le droit. Un article que la loi a écrit pour
elle-même n'a pas d'avant : tout son texte est nouveau.

Ce programme rassemble ces extraits, une loi par fichier, pour qu'une
description soit écrite à partir de ce que la loi dit et non de son intitulé.
Il ne rédige rien : il récolte.

    ./faits_pour_descriptions.py --sortie /tmp/faits [--lois 2026-813,2025-127]
    ./faits_pour_descriptions.py --sortie /tmp/faits --avec-paroles

**Trois choses sont à écrire, et la matière des trois est ici.** L'accroche et
les mesures viennent du texte des articles. Le **contexte** — ce qui se passait
avant — vient de deux endroits, et de nulle part ailleurs : les morceaux
« retiré » des articles, qui sont **la rédaction d'avant, mot pour mot**, et ce
que les orateurs ont dit en séance (`--avec-paroles`). Le **nom d'usage** ne se
trouve que dans les paroles : « la loi Ripost » n'est écrite nulle part dans la
source. Rien ne doit être écrit de mémoire : assembler_descriptions.py refuse
un nom d'usage qu'il ne retrouve pas dans les publiés, mais il ne peut pas
contrôler une phrase — c'est à la rédaction de s'y tenir.

Comment il échantillonne une grande loi — la loi de finances pour 2025 touche
1 053 articles, qu'on ne lit pas :
  — d'abord les articles que la loi a écrits elle-même, les plus longs en tête,
    parce qu'ils portent son droit propre ;
  — puis les articles de code les plus réécrits (part commune la plus faible),
    parce qu'un article changé à 80 % dit un vrai changement, là où un article
    changé à 2 % est souvent une référence corrigée.
Le fichier de sortie dit toujours combien d'articles ont été lus sur combien.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.error
import urllib.request

SOCLE = "https://yesno584.github.io/AN-API"
# Assez d'articles pour reconnaître ce que fait une loi, assez peu pour qu'une
# loi de finances ne noie pas les autres.
ARTICLES_MAX = 10
# De quoi lire une disposition entière sans recopier un tableau de recettes.
# Relevé à 2 000 après la première rédaction : à 1 200, plusieurs articles
# étaient coupés en cours de phrase, et les mesures concernées ont été
# abandonnées faute de savoir ce qu'elles visaient — « une ligne tracée à
# quarante ki », « Le s'applique : a) Aux ; b) Aux ». Une coupure au milieu
# d'une phrase ne se voit pas : elle se lit comme une phrase complète et
# absurde.
EXTRAIT_MAX = 2000
# De quoi reconnaître de quoi parlait la séance, sans recopier un discours.
# Les paroles entières restent affichées dans l'application, mot pour mot.
PAROLE_MAX = 900
PAROLES_MAX = 12


def lire(url: str):
    with urllib.request.urlopen(url, timeout=60) as reponse:
        return json.load(reponse)


def lire_ou_rien(url: str):
    try:
        return lire(url)
    except (urllib.error.URLError, json.JSONDecodeError):
        return None


def parcours(uid: str) -> dict:
    """Le peu du dossier qui aide à situer un texte : sa formule et ses dates.

    Le titre dit ce que le texte vise ; la formule de la source le redit
    souvent autrement, et les dates disent en combien de temps il est passé.
    """
    d = lire_ou_rien(f"{SOCLE}/textes/{uid}.json") or {}
    return {
        "formule": d.get("formule"),
        "chambreInitiale": d.get("chambre_initiale"),
        "procedureAcceleree": d.get("procedureAcceleree"),
        "etapes": [{"date": e.get("date"), "libelle": e.get("libelle"),
                    "lecture": e.get("lecture"), "chambre": e.get("chambre"),
                    "conclusion": e.get("conclusion")}
                   for e in (d.get("parcours") or [])],
    }


def paroles_du_texte(uid: str) -> list[dict]:
    """Un échantillon des prises de parole, pour le contexte et le nom d'usage.

    Les plus longues d'abord : une intervention de dix lignes pose le problème,
    une de deux lignes répond à une question de procédure.
    """
    d = lire_ou_rien(f"{SOCLE}/paroles/{uid}.json") or {}
    dites = sorted((d.get("paroles") or []),
                   key=lambda p: -len(p.get("texte") or ""))[:PAROLES_MAX]
    return [{"nom": p.get("nom"), "sigle": p.get("sigle"),
             "section": p.get("section"),
             "texte": (p.get("texte") or "")[:PAROLE_MAX]} for p in dites]


def a_retenir(liste: dict) -> list[dict]:
    """Les articles à lire, les plus porteurs de sens d'abord."""
    ajouts = sorted(liste.get("articlesAjoutes") or [],
                    key=lambda a: -(a.get("mots") or 0))
    changes = [a for g in (liste.get("groupes") or []) for a in g["articles"]]
    # `commun` est la part de texte inchangée : plus elle est basse, plus la
    # loi a réécrit. None veut dire « pas de rédaction d'avant » — donc neuf.
    changes.sort(key=lambda a: (a.get("commun") if a.get("commun") is not None else -1,
                                -(a.get("mots") or 0)))
    # Moitié-moitié, et chaque moitié rend ce qu'elle n'utilise pas. Prendre
    # tous les articles propres d'abord paraissait juste, mais la loi 2026-813
    # l'a démenti : ses deux articles propres ne disent que « entre en vigueur
    # à la rentrée » et « déclaré non conforme », pendant que la vraie mesure
    # est dans un article du code de l'éducation réécrit à 19 %.
    moitie = ARTICLES_MAX // 2
    pris_ajouts = ajouts[:max(moitie, ARTICLES_MAX - len(changes))]
    pris_changes = changes[:ARTICLES_MAX - len(pris_ajouts)]
    retenus, vus = [], set()
    for a in pris_ajouts + pris_changes:
        if a["id"] in vus:
            continue
        vus.add(a["id"])
        retenus.append(a)
    return retenus


def extrait(article: dict) -> dict:
    """Ce qu'un article apporte, en clair : le texte neuf, et ce qu'il retire."""
    morceaux = article.get("morceaux") or []
    fond = [m for m in morceaux if not m.get("forme")]
    ajoute = " ".join(m["texte"] for m in fond if m["role"] == "ajoute")
    retire = " ".join(m["texte"] for m in fond if m["role"] == "retire")
    entier = " ".join(m["texte"] for m in morceaux if m["role"] != "retire")
    return {
        "ou": article.get("ou"),
        "numero": article.get("numero"),
        "action": article.get("action"),
        "effet": article.get("effet"),
        "partChangee": (100 - article["commun"]) if article.get("commun") is not None else None,
        # Un article neuf n'a pas de « texte ajouté » distinct de lui-même.
        "ajoute": (ajoute or entier)[:EXTRAIT_MAX],
        "retire": retire[:EXTRAIT_MAX] or None,
        "nota": (article.get("nota") or None),
    }


# Combien d'articles d'une version on garde, et quelle longueur. Une version
# pèse jusqu'à 2,8 Mo (le projet de loi de finances pour 2026) : on n'en lit
# pas 276 en entier. Les plus longs d'abord — un article de deux lignes dit
# souvent « la présente loi entre en vigueur le… ».
ARTICLES_VERSION = 12
EXTRAIT_VERSION = 1800


def faits_du_texte_en_cours(uid: str, texte: dict) -> dict | None:
    """Ce qu'un texte en cours décide, dans sa **dernière version publiée**.

    Pas le texte déposé : un texte réécrit en commission ne dit plus ce qu'il
    disait au dépôt, et le décrire au dépôt serait décrire un texte qui
    n'existe plus. C'est la version que l'onglet « Texte » de la fiche montre
    sous « Version à jour », et le même fichier publié.
    """
    versions = texte.get("versions") or []
    if not versions:
        return None
    derniere = versions[-1]
    d = lire_ou_rien(f"{SOCLE}/versions/{uid}/{derniere['ref']}.json")
    if not d:
        return None
    # **Un article `retire` porte l'ANCIENNE rédaction, pas la nouvelle.** Une
    # version liste aussi ce qu'elle a supprimé, pour que la comparaison puisse
    # l'afficher barré. Le garder ici faisait décrire un texte qui n'existe
    # plus : trouvé le 2026-09-20 sur un texte dont la commission avait vidé
    # les trois premiers articles, et qui arrivait au rédacteur avec ces
    # articles pleins de substance.
    tous = [a for a in (d.get("articles") or []) if a.get("quoi") != "retire"]
    # **`quoi: retire` ne veut pas dire « supprimé ».** Il dit seulement que
    # l'article n'est plus imprimé dans cette version, ce qui recouvre quatre
    # cas très différents : une vraie suppression, un article éclaté et
    # renuméroté, des articles adoptés « (Conformes) » regroupés en un bloc, et
    # le bloc de signature de la version précédente. Le compter faisait croire
    # à un texte qui maigrit là où il grossissait.
    #
    # Ce qui dit la suppression est `etat`, sur un article **présent** : la
    # source imprime alors « Article 3 — (Supprimé) ».
    supprimes = sum(1 for a in tous if a.get("etat") == "supprimé")
    # La source publie parfois un article sans son texte : « Article 1er »,
    # « (Supprimé) », « (Conforme) » et rien d'autre. Mesuré le 2026-09-20 :
    # 73 articles sur 1 163 récoltés, et 8 textes dont la moitié ou plus sont
    # dans ce cas. Les compter comme « lus » faisait annoncer « 7 sur 7 » là où
    # 4 étaient vides, donc surestimer la matière d'une description.
    porteurs = [a for a in tous if (a.get("texte") or "").strip()]
    articles = sorted(porteurs, key=lambda a: -len(a["texte"]))[:ARTICLES_VERSION]
    return {
        "uid": uid,
        "titre": texte.get("titre"),
        "type": texte.get("type"),
        "aEcrire": A_ECRIRE,
        "quelleVersion": {"nom": derniere.get("nom"), "date": derniere.get("date"),
                          "ref": derniere["ref"], "surCombien": len(versions)},
        "dossier": parcours(uid),
        "articlesEnTout": len(tous),
        "articlesLus": len(articles),
        # Ce que la source ne publie pas : le dire, pour qu'une description ne
        # se croie pas complète quand elle ne l'est pas.
        **({"articlesSansTexte": len(tous) - len(porteurs)}
           if len(porteurs) < len(tous) else {}),
        # Combien d'articles cette version a vidés — le texte a vraiment maigri.
        **({"articlesSupprimes": supprimes} if supprimes else {}),
        # `etat` vaut « supprimé », « nouveau », ou rien : sans lui, un
        # rédacteur ne peut pas savoir si un article vide a été vidé par cette
        # version ou simplement publié sans son texte.
        "articles": [{"numero": a.get("numero"), "titre": a.get("titre"),
                      **({"etat": a["etat"]} if a.get("etat") else {}),
                      "texte": a["texte"][:EXTRAIT_VERSION]}
                     for a in articles],
    }


A_ECRIRE = ("un contexte d'un paragraphe au plus — ce qui se passait avant,"
            " tiré des morceaux « retire » et des paroles, jamais de mémoire ;"
            " une accroche d'une phrase ; au plus 8 mesures ; et le nom d'usage"
            " du texte s'il en a un, tel qu'il est prononcé en séance")


def faits_d_une_loi(uid: str, entete: dict, avec_paroles: bool = False) -> dict:
    liste = lire(f"{SOCLE}/changements/{uid}.json")
    retenus = a_retenir(liste)
    articles = []
    for a in retenus:
        try:
            articles.append(extrait(lire(f"{SOCLE}/changements/{uid}/{a['id']}.json")))
        except (urllib.error.URLError, json.JSONDecodeError) as erreur:
            print(f"  {uid}/{a['id']} illisible : {erreur}", file=sys.stderr)
    total = len(liste.get("articlesAjoutes") or []) + sum(
        len(g["articles"]) for g in (liste.get("groupes") or []))
    return {
        **entete,
        "aEcrire": A_ECRIRE,
        "loi": liste.get("loi"),
        "dossier": parcours(uid),
        "articlesEnTout": total,
        "articlesLus": len(articles),
        "codesTouches": [{"ou": g["ou"], "articles": len(g["articles"])}
                         for g in (liste.get("groupes") or [])],
        "articles": articles,
        **({"paroles": paroles_du_texte(uid)} if avec_paroles else {}),
    }


def main() -> int:
    global SOCLE
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sortie", required=True, type=pathlib.Path)
    ap.add_argument("--lois", help="numéros de loi, séparés par des virgules ;"
                                   " par défaut, toutes les lois promulguées")
    ap.add_argument("--socle", default=SOCLE)
    ap.add_argument("--avec-paroles", action="store_true",
                    help="joindre un échantillon des prises de parole en séance :"
                         " la seule matière d'un nom d'usage, et la meilleure"
                         " d'un contexte. Les fichiers y gagnent 10 Ko environ")
    ap.add_argument("--textes", help="identifiants de dossier séparés par des"
                                     " virgules, ou un fichier qui en porte un"
                                     " par ligne. Récolte alors la DERNIÈRE"
                                     " VERSION PUBLIÉE de chacun, au lieu des"
                                     " lois promulguées")
    args = ap.parse_args()

    SOCLE = args.socle.rstrip("/")
    args.sortie.mkdir(parents=True, exist_ok=True)

    # Deux sources, selon ce qu'on décrit — c'est la règle qui décide de tout :
    # une loi promulguée se décrit sur le droit qu'elle change et qui est en
    # vigueur, un texte en cours sur sa dernière version publiée.
    if args.textes:
        chemin = pathlib.Path(args.textes)
        uids = ([x.strip() for x in chemin.read_text(encoding="utf-8").split() if x.strip()]
                if chemin.exists()
                else [x.strip() for x in args.textes.split(",") if x.strip()])
        ecrits = sautes = 0
        for uid in uids:
            texte = lire_ou_rien(f"{SOCLE}/textes/{uid}.json")
            faits = faits_du_texte_en_cours(uid, texte) if texte else None
            if not faits:
                sautes += 1
                print(f"  {uid} : aucune version publiée à lire", file=sys.stderr)
                continue
            (args.sortie / f"{uid}.json").write_text(
                json.dumps(faits, ensure_ascii=False, indent=1), encoding="utf-8")
            ecrits += 1
            print(f'  {uid}  {faits["articlesLus"]:>2}/{faits["articlesEnTout"]:<4}'
                  f'  {faits["quelleVersion"]["nom"][:28]:28}  {(faits["titre"] or "")[:44]}')
        print(f"{ecrits} textes écrits dans {args.sortie}, {sautes} sans version",
              file=sys.stderr)
        return 0

    voulues = set((args.lois or "").split(",")) if args.lois else None
    promulguees = lire(f"{SOCLE}/promulgues.json")["textes"]
    ecrits = 0
    for t in promulguees:
        if voulues and t.get("loiNumero") not in voulues:
            continue
        entete = {"uid": t["uid"], "titre": t["titre"], "type": t["type"],
                  "loiDate": t.get("loiDate")}
        try:
            faits = faits_d_une_loi(t["uid"], entete, args.avec_paroles)
        except (urllib.error.URLError, KeyError, json.JSONDecodeError) as erreur:
            print(f"{t['uid']} sans changements lisibles : {erreur}", file=sys.stderr)
            # Une loi dont le droit consolidé n'a rien à dire garde le reste :
            # son parcours et ses débats suffisent à écrire un contexte.
            faits = {**entete, "aEcrire": A_ECRIRE, "loi": t.get("loiNumero"),
                     "dossier": parcours(t["uid"]), "articlesEnTout": 0,
                     "articlesLus": 0, "codesTouches": [], "articles": [],
                     **({"paroles": paroles_du_texte(t["uid"])} if args.avec_paroles else {})}
        (args.sortie / f"{t['uid']}.json").write_text(
            json.dumps(faits, ensure_ascii=False, indent=1), encoding="utf-8")
        ecrits += 1
        print(f"  {faits['loi']:>10}  {faits['articlesLus']:>2}/{faits['articlesEnTout']:<5}"
              f"  {t['titre'][:60]}")
    print(f"{ecrits} lois écrites dans {args.sortie}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
