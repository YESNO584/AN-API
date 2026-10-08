"""Les pages du site du Sénat — la seule source de certains liens — et comment les lire sans se faire couper.
"""
from __future__ import annotations

import urllib.error
import urllib.request
import senat


def lire_url(url: str) -> str:
    """Une page du site du Sénat, compressée quand le serveur le veut bien."""
    requete = urllib.request.Request(
        url,
        headers={"Accept-Encoding": "gzip",
                 "User-Agent": "qui-vote-quoi (github.com/yesno584/AN-API)"})
    with urllib.request.urlopen(requete, timeout=120) as r:
        brut = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            import gzip
            brut = gzip.decompress(brut)
    return brut.decode("utf-8", "replace")


def lire_page(annee: int) -> str:
    """Une page de scrutins : 285 Ko en clair, 29 Ko sur le fil."""
    return lire_url(senat.URL_SCRUTINS.format(annee=annee))
