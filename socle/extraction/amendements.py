"""Un amendement tel que publié → un amendement tel que la base le range, et son dispositif découpé en ce qu'il retire et ce qu'il ajoute.
"""
from __future__ import annotations

import html
import json
import pathlib
import re
import zipfile
from typing import Iterable, Iterator


AJOUT, RETRAIT, NEUTRE = "ajout", "retrait", "neutre"


# Le verbe qui gouverne l'instruction dit ce qu'il advient des passages cités.
# Ce classement est une aide de lecture, pas une vérité juridique : un
# amendement complexe peut mêler plusieurs opérations.
VERBES_RETRAIT = ("supprimer", "abroger")


VERBES_REMPLACEMENT = ("substituer", "remplacer", "rédiger ainsi", "rediger ainsi")


def _texte_brut(html_source: str) -> str:
    sans_balises = re.sub(r"<[^>]+>", " ", html_source or "")
    return re.sub(r"\s+", " ", html.unescape(sans_balises)).strip()


def colorer_dispositif(dispositif: str) -> list[dict]:
    """Découpe l'instruction en morceaux, en marquant les passages cités.

    Rend une liste de `{"texte": …, "role": ajout|retrait|neutre}`. Le texte
    hors guillemets reste neutre : c'est l'instruction elle-même. Les passages
    entre « … » sont ceux que l'amendement ajoute ou retire.

    Règle, volontairement simple et annoncée comme telle :
      — « supprimer », « abroger »            → tout ce qui est cité est retiré ;
      — « substituer », « remplacer »         → le premier cité est retiré,
                                                les suivants sont ajoutés ;
      — sinon (compléter, insérer, ajouter…)  → ce qui est cité est ajouté.
    """
    texte = _texte_brut(dispositif)
    if not texte:
        return []

    debut = texte[:60].lower()
    if any(v in debut for v in VERBES_RETRAIT):
        roles = lambda rang: RETRAIT                                    # noqa: E731
    elif any(v in debut for v in VERBES_REMPLACEMENT):
        roles = lambda rang: RETRAIT if rang == 0 else AJOUT            # noqa: E731
    else:
        roles = lambda rang: AJOUT                                      # noqa: E731

    morceaux, position, rang = [], 0, 0
    for citation in re.finditer(r"«\s*(.*?)\s*»", texte, re.S):
        avant = texte[position:citation.start()]
        if avant.strip():
            morceaux.append({"texte": avant, "role": NEUTRE})
        contenu = citation.group(1)
        if contenu:
            morceaux.append({"texte": contenu, "role": roles(rang)})
            rang += 1
        position = citation.end()
    reste = texte[position:]
    if reste.strip():
        morceaux.append({"texte": reste, "role": NEUTRE})
    return morceaux or [{"texte": texte, "role": NEUTRE}]


def analyser_amendement(brut: dict) -> dict:
    """Un amendement tel que publié → un amendement tel que la base le range."""
    a = brut["amendement"]
    identification = a.get("identification") or {}
    pointeur = a.get("pointeurFragmentTexte") or {}
    division = pointeur.get("division") or {}
    corps = (a.get("corps") or {}).get("contenuAuteur") or {}
    cycle = a.get("cycleDeVie") or {}
    traitements = (cycle.get("etatDesTraitements") or {})
    signataires = (a.get("signataires") or {}).get("auteur") or {}

    def mot(valeur):
        """Le format XML rend un champ vide par {'@xsi:nil': 'true'}, pas par
        `null`. Sans ce filtre, un dict finit dans une colonne de la base."""
        return valeur if isinstance(valeur, str) and valeur else None

    def nombre(valeur):
        try:
            return int(valeur)
        except (TypeError, ValueError):
            return None

    return {
        "uid": a["uid"],
        "dossier": None,                       # rempli par l'appelant, d'après le chemin
        "numero": mot(identification.get("numeroLong")),
        "ordre": nombre(identification.get("numeroOrdreDepot")),
        "article": mot(division.get("titre")) or mot(division.get("articleDesignationCourte")),
        # **Où** l'amendement agit, et sur quel document. Ces deux champs
        # décident du rapprochement avec les versions du texte (voir
        # `textes.py`) : un amendement « Après l'article 1er » ne modifie pas
        # l'article 1er, il crée l'article 1er bis — 2 823 amendements adoptés
        # de la législature sont dans ce cas. Et le document visé dit à quelle
        # étape l'amendement s'applique : le texte déposé pour la commission,
        # le texte de la commission pour la séance.
        "ou": mot(division.get("avant_A_Apres")) or "A",
        "divisionType": mot(division.get("type")),
        "texte": None,                         # rempli par l'appelant, d'après le chemin
        "auteurRef": mot(signataires.get("acteurRef")),
        "groupeRef": mot(signataires.get("groupePolitiqueRef")),
        "typeAuteur": mot(signataires.get("typeAuteur")),
        "dateDepot": mot(cycle.get("dateDepot")),
        "etat": mot((traitements.get("etat") or {}).get("libelle")),
        "sort": mot((traitements.get("sousEtat") or {}).get("libelle")),
        "dispositif": _texte_brut(corps.get("dispositif")),
        "expose": _texte_brut(corps.get("exposeSommaire")),
        "morceaux": colorer_dispositif(corps.get("dispositif")),
    }


def lire_amendements(archive: pathlib.Path) -> Iterator[dict]:
    """Les amendements, avec le dossier auquel ils appartiennent.

    Le lien vers le dossier n'est pas dans le fichier : il est dans le chemin,
    `json/<dossier>/<texte>/<amendement>.json`.
    """
    with zipfile.ZipFile(archive) as zf:
        for nom in zf.namelist():
            if not nom.endswith(".json"):
                continue
            morceaux = nom.split("/")
            if len(morceaux) < 3:
                continue
            with zf.open(nom) as fichier:
                a = analyser_amendement(json.load(fichier))
            a["dossier"] = morceaux[1]
            # `json/<dossier>/<texte>/<amendement>.json` : le document amendé
            # n'est pas dans le fichier non plus, il est dans le chemin.
            a["texte"] = morceaux[2]
            yield a
