"""`recherche.json` : les mots que la recherche lit en plus du titre — ceux de la description de chaque texte.
"""
from __future__ import annotations

from publication.commun import ecrire
from publication.contexte import Publication


def mots_de_la_description(d: dict) -> str:
    """Tout ce que la fiche affiche de la description, à la suite : le nom
    d'usage, l'accroche, le contexte, puis chaque point. Le texte est publié
    tel quel — c'est la maquette qui ignore accents, casse, ligatures et
    apostrophes, avec la même règle que pour le titre ; la dupliquer ici, en
    Python, ferait deux règles qui finissent par différer."""
    morceaux = [(d.get("nomUsage") or {}).get("nom"), d.get("accroche"),
                d.get("contexte"), *(d.get("points") or [])]
    return " ".join(m.strip() for m in morceaux if m and m.strip())


def ecrire_recherche(p: Publication) -> None:
    """Un fichier à part, et non un champ de `textes.json` : la liste est lue
    en entier au démarrage, et la description n'y va pas pour la même raison
    qu'elle ne va que dans la fiche (`fiches.py`). La maquette ne lit celui-ci
    qu'à la première frappe dans la recherche.

    Seuls les textes que la base connaît y figurent : une description dont le
    dossier a disparu ne trouverait rien à montrer. La recherche ne dit pas
    pourquoi un texte est sorti — titre ou description — : décidé le
    2026-10-14 avec l'utilisateur.
    """
    connus = {l["uid"] for l in p.cx.execute("SELECT uid FROM dossier")}
    textes = {uid: mots for uid, d in sorted(p.descriptions.items())
              if uid in connus and (mots := mots_de_la_description(d))}
    p.tailles["recherche.json"] = ecrire(p.sortie / "recherche.json", {
        "genereLe": p.genere_le, "total": len(textes), "descriptions": textes})
