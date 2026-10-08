"""Ce qui se dit d'un texte : les prises de parole mot pour mot, et les deux rubriques écrites hors ligne — la description et le résumé des débats.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from publication.commun import DESCRIPTIONS, RESUMES_DEBATS


def vu_le(cx: sqlite3.Connection, url: str) -> str | None:
    """Quand cette archive a été téléchargée avec succès pour la dernière fois.

    La table `source` n'est mise à jour que sur un téléchargement réussi : une
    source absente y garde donc la date de la fois d'avant, qui est exactement
    ce qu'on veut afficher.
    """
    ligne = cx.execute("SELECT vu_le FROM source WHERE url = ?", (url,)).fetchone()
    return ligne["vu_le"] if ligne else None


def paroles_du_texte(cx: sqlite3.Connection, uid: str) -> dict:
    """Ce que les groupes ont dit du texte en séance, mot pour mot.

    Rien n'est coupé ni résumé : une prise de parole fait 4 260 caractères en
    médiane, 12 377 au plus long, et la tronquer reviendrait à choisir ce qui
    compte. C'est l'affichage qui la replie, pas la publication.

    L'ordre est celui de la séance — (jour, compte rendu, rang). Le groupe est
    celui du jour du débat, imprimé par le compte rendu : 95,6 % des paroles
    en ont un, les autres sont des ministres, des rapporteurs et des
    non-inscrits, qui s'affichent sous leur seul nom.
    """
    lignes = cx.execute(
        "SELECT p.date, p.section, p.nom, p.qualite, p.sigle, p.texte,"
        " g.couleur, a.photo"
        " FROM parole p"
        " LEFT JOIN groupe g ON g.sigle = p.sigle"
        " LEFT JOIN acteur a ON a.ref = p.acteur_ref"
        " WHERE p.dossier_uid = ?"
        " ORDER BY p.date, p.seance, p.ordre", (uid,)).fetchall()
    if not lignes:
        return {"total": 0, "groupes": [], "paroles": []}

    # Les groupes qui ont parlé, dans l'ordre de l'hémicycle : c'est celui de
    # la table `groupe`, mesuré sur les numéros de siège.
    compte: dict[str, dict] = {}
    for l in lignes:
        if l["sigle"]:
            g = compte.setdefault(l["sigle"], {"sigle": l["sigle"],
                                               "couleur": l["couleur"], "paroles": 0})
            g["paroles"] += 1
    rangs = {s: r for s, r in cx.execute("SELECT sigle, rang FROM groupe")}
    groupes = sorted(compte.values(), key=lambda g: rangs.get(g["sigle"], 99))
    return {"total": len(lignes), "groupes": groupes,
            "paroles": [dict(l) for l in lignes]}


def lire_descriptions() -> dict[str, dict]:
    """La description d'un texte, telle qu'elle s'affiche en haut de sa fiche.

    **C'est l'une des deux seules données du projet qui ne viennent pas d'une
    source publique** — l'autre étant le résumé des débats — et la première des
    deux exceptions à la règle « rien n'est écrit par une IA ». D'où le
    champ `origine`, publié avec le texte et affiché à l'écran : le lecteur doit
    savoir qui a écrit ce qu'il lit. Voir `docs/CE-QUE-L-ON-ECRIT.md`.

    Une entrée porte un contexte d'un paragraphe au plus, une accroche d'une
    phrase et une liste de points — une mesure concrète par point. Elle porte
    aussi le **nom d'usage** du texte quand il en a un, avec le nombre de fois
    qu'il est prononcé dans les débats publiés : ce compte est relevé par
    `assembler_descriptions.py`, jamais écrit par la rédaction. Contexte et
    nom d'usage sont facultatifs, et une accroche sans point reste valable :
    une loi qui autorise l'approbation d'un traité n'a qu'une chose à dire.

    Le fichier est versionné, contrairement aux bases : rien ne le reconstruit.
    Un texte qui n'y figure pas n'a pas de description, et la fiche n'affiche
    alors pas la rubrique — plutôt qu'un cadre vide.

    Absent ou illisible, on publie sans descriptions : elles sont un confort de
    lecture, pas une donnée du Parlement, et rien ne doit s'arrêter pour elles.
    """
    if not DESCRIPTIONS.exists():
        return {}
    try:
        contenu = json.loads(DESCRIPTIONS.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as erreur:
        print(f"  descriptions ignorées : {erreur}", file=sys.stderr)
        return {}
    retenues = {}
    for uid, d in (contenu.get("descriptions") or {}).items():
        accroche = (d.get("accroche") or "").strip()
        points = [p.strip() for p in (d.get("points") or []) if p and p.strip()]
        # Une origine inconnue ne s'affiche pas comme « écrite par une
        # personne » : sans mention sûre, on ne publie pas la description.
        if accroche and d.get("origine") in ("ia", "humain"):
            retenues[uid] = {
                # Le contexte — ce qui se passait avant le texte — et le nom
                # d'usage sont facultatifs : un texte peut n'avoir ni l'un ni
                # l'autre, et la fiche n'affiche alors que l'accroche.
                **({"contexte": d["contexte"].strip()}
                   if (d.get("contexte") or "").strip() else {}),
                **({"nomUsage": d["nomUsage"]}
                   if (d.get("nomUsage") or {}).get("nom") else {}),
                "accroche": accroche, "points": points,
                "origine": d["origine"], "le": d.get("le"),
                # Le modèle qui a écrit, quand il est renseigné.
                # Vide pour une description rédigée à la main.
                "modele": d.get("modele") or None}
    return retenues


def lire_resumes_debats() -> dict[str, dict]:
    """Le résumé des débats d'un texte, en tête de l'onglet « Débats ».

    **Seconde rubrique du projet écrite par une IA**, après la description d'un
    texte — l'exception est décidée dans `docs/CE-QUE-L-ON-ECRIT.md`. D'où le
    champ `origine`, publié et affiché : le lecteur doit savoir qui a écrit ce
    qu'il lit. Les prises de parole complètes restent publiées à côté, mot pour
    mot, et rien ne les remplace.

    **La position de vote de chaque groupe n'est pas écrite par la rédaction** :
    `assembler_resumes.py` la relève dans le scrutin publié. Un résumé ne peut
    donc pas se tromper sur un vote, seulement sur un argument.

    Le fichier est versionné, comme les descriptions : rien ne le reconstruit.
    Un texte qui n'y figure pas n'affiche aucun résumé, plutôt qu'un cadre vide.
    """
    if not RESUMES_DEBATS.exists():
        return {}
    try:
        contenu = json.loads(RESUMES_DEBATS.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as erreur:
        print(f"  résumés de débats ignorés : {erreur}", file=sys.stderr)
        return {}
    retenus = {}
    for uid, r in (contenu.get("resumes") or {}).items():
        groupes = [g for g in (r.get("groupes") or [])
                   if g.get("sigle") and (g.get("arguments") or [])]
        # Les orateurs que la source n'a rattachés à aucun groupe — un
        # ministre, un non-inscrit. Ils s'affichent sous leur nom, après les
        # camps, et n'ont jamais de position : un ministre ne vote pas.
        orateurs = [o for o in (r.get("orateurs") or [])
                    if o.get("nom") and (o.get("arguments") or [])]
        # Sans origine sûre, on ne publie pas : une rubrique écrite qui ne dit
        # pas qui l'a écrite est exactement ce que le projet refuse.
        if (groupes or orateurs) and r.get("origine") in ("ia", "humain"):
            retenus[uid] = {"vote": r.get("vote"), "groupes": groupes,
                            **({"orateurs": orateurs} if orateurs else {}),
                            "origine": r["origine"], "le": r.get("le"),
                            "modele": r.get("modele") or None}
    return retenus
