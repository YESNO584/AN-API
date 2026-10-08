"""Télécharger une archive sans jamais la laisser à moitié, et la parcourir sans tout charger en mémoire.
"""
from __future__ import annotations

import http.client
import json
import pathlib
import time
import urllib.request
import zipfile
from typing import Iterable, Iterator
from extraction.sources import URL_ARCHIVE


def _lire(archive: pathlib.Path, dossier: str) -> Iterator[dict]:
    """Parcourt une archive et rend ses objets, sans tout charger en mémoire."""
    with zipfile.ZipFile(archive) as zf:
        for nom in zf.namelist():
            if f"/{dossier}/" not in nom or not nom.endswith(".json"):
                continue
            with zf.open(nom) as fichier:
                yield json.load(fichier)


# Une archive de 297 Mo ne traverse pas toujours le réseau d'un coup. Les deux
# publications du 2026-08-31 ont échoué ainsi : la connexion a été coupée après
# 2,6 Mo, puis après 51,7 Mo. Recommencer depuis le début n'y suffisait pas.
#
# Le serveur de l'Assemblée accepte les reprises — il répond « 206 Partial
# Content » et annonce « accept-ranges: bytes » (vérifié le 2026-08-31). On
# reprend donc là où le transfert s'est arrêté, au lieu de tout redemander.
# Tant que des octets arrivent, on continue : seule une tentative qui
# n'apporte rien consomme le budget. Sans cette nuance, six tentatives
# fructueuses mais courtes épuisaient les essais à 13 Mo sur 297.
ESSAIS_SANS_PROGRES = 6


MORCEAU = 1 << 20


def _taille_annoncee(entetes, deja_recu: int) -> int | None:
    """La taille totale que le serveur annonce, ou None s'il n'en annonce pas.

    Sur une reprise, `Content-Range: bytes 5-99/100` porte le total ; sinon
    c'est `Content-Length`, auquel s'ajoute ce qui est déjà sur le disque.
    """
    portee = entetes.get("Content-Range")
    if portee and "/" in portee:
        total = portee.rsplit("/", 1)[1].strip()
        if total.isdigit():
            return int(total)
    longueur = entetes.get("Content-Length")
    return deja_recu + int(longueur) if longueur and str(longueur).isdigit() else None


def _requete(url: str, entetes: dict[str, str]) -> urllib.request.Request:
    return urllib.request.Request(
        url, headers={"User-Agent": "AN-API/socle (recuperation open data)", **entetes})


def _accueillir(reponse, fichier, recu: int) -> tuple[int, dict]:
    """Ce qu'une réponse dit avant son contenu : d'où reprendre, et ce qu'on
    retiendra d'elle. Une reprise refusée — le serveur renvoie tout, l'archive
    a changé — fait repartir le fichier de zéro."""
    if reponse.status != 206 and recu:
        fichier.seek(0)
        fichier.truncate()
        recu = 0
    return recu, {
        "modifie": True,
        "etag": reponse.headers.get("ETag"),
        "modifieLe": reponse.headers.get("Last-Modified"),
    }


def telecharger(destination: pathlib.Path, entetes: dict[str, str] | None = None,
                url: str = URL_ARCHIVE, essais: int = ESSAIS_SANS_PROGRES,
                patienter=None) -> dict:
    """Télécharge une archive. Rend un compte rendu, sans jamais lever d'exception HTTP 304.

    `entetes` sert au téléchargement conditionnel : en passant l'`ETag` ou le
    `Last-Modified` de la fois précédente, le serveur répond `304` si rien n'a
    changé et l'on économise le transfert.

    Un transfert coupé est **repris à l'octet où il s'est arrêté**, pas
    recommencé. Si l'archive a changé entre-temps, le serveur refuse la reprise
    et renvoie tout : on repart alors de zéro, ce qui est le comportement juste.
    Une réponse HTTP en bonne et due forme — 404, 500 — n'est pas réessayée.
    """
    if patienter is None:
        patienter = time.sleep
    recu, empreinte, compte_rendu = 0, None, None
    steriles = 0                      # tentatives d'affilée qui n'ont rien apporté
    with destination.open("wb") as fichier:
        while True:
            avant = recu
            demande = dict(entetes or {})
            if recu and empreinte:
                demande["Range"] = f"bytes={recu}-"
                demande["If-Range"] = empreinte
            try:
                with urllib.request.urlopen(_requete(url, demande), timeout=600) as reponse:
                    recu, compte_rendu = _accueillir(reponse, fichier, recu)
                    empreinte = reponse.headers.get("ETag") or empreinte
                    total = _taille_annoncee(reponse.headers, recu)
                    avant = recu
                    while morceau := reponse.read(MORCEAU):
                        fichier.write(morceau)
                        recu += len(morceau)
                # Lu par morceaux, un transfert coupé ne lève rien : la lecture
                # rend une chaîne vide et le fichier paraît complet. Il faut
                # donc comparer soi-même à la taille annoncée. C'est ce piège
                # qui a produit une archive de 4,7 Mo au lieu de 297, sans la
                # moindre erreur (constaté le 2026-08-31).
                if total is not None and recu < total:
                    raise http.client.IncompleteRead(b"", total - recu)
                return {**compte_rendu, "octets": recu}
            except urllib.error.HTTPError as erreur:
                if erreur.code == 304:
                    return {"modifie": False, "octets": 0,
                            "etag": (entetes or {}).get("If-None-Match"),
                            "modifieLe": (entetes or {}).get("If-Modified-Since")}
                raise
            except (http.client.IncompleteRead, urllib.error.URLError,
                    ConnectionError, TimeoutError):
                steriles = 0 if recu > avant else steriles + 1
                if steriles >= essais:
                    raise
                fichier.flush()
                patienter(min(2 ** steriles, 30))
    raise RuntimeError("inatteignable")  # pragma: no cover
