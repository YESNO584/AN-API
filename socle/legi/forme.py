"""Comparer deux rédactions, et ne pas prendre une virgule déplacée pour un changement de fond.
"""
from __future__ import annotations

import difflib
from legi.balises import normaliser


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
