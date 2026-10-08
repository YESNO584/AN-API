"""Le dépôt du droit consolidé : son adresse, ses archives, et comment les parcourir sans tout charger.
"""
from __future__ import annotations

import re
import tarfile
from typing import BinaryIO, Iterator


DEPOT_LEGI = "https://echanges.dila.gouv.fr/OPENDATA/LEGI/"


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


def url_legifrance(identifiant: str) -> str:
    """L'adresse publique d'une rédaction, pour qui veut lire la source.

    Légifrance refuse les robots (403, pare-feu Cloudflare, mesuré le
    2026-09-01), mais un lecteur qui clique passe sans difficulté.
    """
    return f"https://www.legifrance.gouv.fr/codes/article_lc/{identifiant}"
