"""Lire le XML de LEGI sans dépendre de l'ordre de ses attributs : une balise, un champ, un bloc rendu lisible.
"""
from __future__ import annotations

import html as _html
import re


_BALISE = re.compile(r"<(\w+)\b([^>]*)/?>")


_ATTRIBUT = re.compile(r'(\w+)="([^"]*)"')


_LIEN_ART = re.compile(r"<LIEN_ART\b[^>]*>")


_LIEN = re.compile(r"<LIEN\b[^>]*>")


_TITRE_TXT = re.compile(r"<TITRE_TXT\b([^>]*)>")


_TEXTE = re.compile(r"<TEXTE\b([^>]*)>")


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
