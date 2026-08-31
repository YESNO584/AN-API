#!/usr/bin/env python3
"""Sert les données du socle à l'application.

C'est ce serveur qui débloquera la future version web. Une page dans un
navigateur ne peut pas lire `data.assemblee-nationale.fr` directement — les
portails du Parlement n'envoient pas l'en-tête `Access-Control-Allow-Origin`.
Le socle, lui, l'envoie : l'application Flutter web pourra donc l'interroger,
et l'application mobile aussi.

Il ne lit que la base. Il ne télécharge rien et n'écrit nulle part —
`recuperer.py` s'en charge, de son côté, une fois par jour.

Usage :
    ./serveur.py                       # sur http://127.0.0.1:8000
    ./serveur.py --port 9000 --hote 0.0.0.0

Adresses :
    GET /                    la liste de ce qui suit, en clair
    GET /api/sante           la base est-elle à jour, et de quand date-t-elle
    GET /api/etapes          les six étapes du parcours, et combien de textes à chacune
    GET /api/textes          la liste des textes  (voir les filtres ci-dessous)
    GET /api/textes/<uid>    un texte et toutes ses étapes

Filtres de /api/textes :
    etape=1..6        seulement les textes à cette étape
    chambre=assemblee|senat
    statut=en_cours|promulgue|retire     (défaut : en_cours)
    lois=0|1          garder les dossiers qui ne font pas de loi (défaut : 1, non)
    recherche=mots    dans le titre
    limite=1..500     (défaut : 100)     debut=0
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import extraction

RACINE = pathlib.Path(__file__).resolve().parent
BASE = RACINE / "parlement.db"
LIMITE_MAX = 500


class Erreur(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def entier(valeurs: dict, cle: str, defaut: int, mini: int, maxi: int) -> int:
    brut = valeurs.get(cle, [None])[0]
    if brut is None:
        return defaut
    try:
        nombre = int(brut)
    except ValueError:
        raise Erreur(400, f"« {cle} » doit être un nombre, reçu « {brut} »")
    if not mini <= nombre <= maxi:
        raise Erreur(400, f"« {cle} » doit être compris entre {mini} et {maxi}, reçu {nombre}")
    return nombre


def sante(cx: sqlite3.Connection) -> dict:
    derniere = cx.execute(
        "SELECT * FROM journal WHERE statut IN ('succes','inchange')"
        " ORDER BY id DESC LIMIT 1").fetchone()
    echec = cx.execute(
        "SELECT * FROM journal WHERE statut = 'echec' ORDER BY id DESC LIMIT 1").fetchone()
    total = cx.execute("SELECT COUNT(*) n FROM dossier").fetchone()["n"]
    return {
        "base": "prête" if total else "vide",
        "dossiers": total,
        "etapes": cx.execute("SELECT COUNT(*) n FROM etape").fetchone()["n"],
        "dernierChargement": dict(derniere) if derniere else None,
        "dernierEchec": dict(echec) if echec else None,
        "source": extraction.URL_ARCHIVE,
        "licence": "Licence Ouverte (Etalab)",
    }


def etapes(cx: sqlite3.Connection) -> dict:
    comptes = {l["etape"]: l["n"] for l in cx.execute(
        "SELECT etape, COUNT(*) n FROM dossier"
        " WHERE statut='en_cours' AND est_loi=1 AND etape IS NOT NULL"
        " GROUP BY etape")}
    return {"etapes": [{"n": n, "nom": nom, "quoi": quoi, "textesEnCours": comptes.get(n, 0)}
                       for n, nom, quoi in extraction.ETAPES]}


def textes(cx: sqlite3.Connection, valeurs: dict) -> dict:
    conditions, arguments = [], []

    statut = valeurs.get("statut", ["en_cours"])[0]
    if statut != "tous":
        conditions.append("statut = ?")
        arguments.append(statut)

    if valeurs.get("lois", ["1"])[0] != "0":
        conditions.append("est_loi = 1")

    if "etape" in valeurs:
        conditions.append("etape = ?")
        arguments.append(entier(valeurs, "etape", 1, 1, len(extraction.ETAPES)))

    if "chambre" in valeurs:
        chambre = valeurs["chambre"][0]
        if chambre not in ("assemblee", "senat"):
            raise Erreur(400, "« chambre » vaut « assemblee » ou « senat »")
        # La chambre où le texte se trouve est celle de son étape courante ; à
        # défaut d'étape (dossier sans acte), celle où il a été déposé.
        conditions.append("""(
            SELECT e.chambre FROM etape e
             WHERE e.dossier_uid = dossier.uid AND e.future = 0
             ORDER BY e.date DESC, e.numero DESC, e.rang DESC LIMIT 1) = ?""")
        arguments.append(chambre)

    if valeurs.get("recherche", [""])[0].strip():
        conditions.append("titre LIKE ?")
        arguments.append(f"%{valeurs['recherche'][0].strip()}%")

    ou = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    total = cx.execute(f"SELECT COUNT(*) n FROM dossier{ou}", arguments).fetchone()["n"]

    limite = entier(valeurs, "limite", 100, 1, LIMITE_MAX)
    debut = entier(valeurs, "debut", 0, 0, 1_000_000)
    lignes = cx.execute(
        f"SELECT * FROM dossier{ou}"
        " ORDER BY etape DESC, date_dernier_mouvement DESC, uid"
        " LIMIT ? OFFSET ?", [*arguments, limite, debut]).fetchall()

    return {"total": total, "debut": debut, "limite": limite,
            "textes": [dict(l) for l in lignes]}


def texte(cx: sqlite3.Connection, uid: str) -> dict:
    ligne = cx.execute("SELECT * FROM dossier WHERE uid = ?", (uid,)).fetchone()
    if not ligne:
        raise Erreur(404, f"aucun dossier « {uid} »")
    parcours = cx.execute(
        "SELECT * FROM etape WHERE dossier_uid = ? ORDER BY date, rang", (uid,)).fetchall()
    return {**dict(ligne), "parcours": [dict(e) for e in parcours]}


def router(cx: sqlite3.Connection, chemin: str, valeurs: dict) -> dict:
    if chemin in ("/", "/api", "/api/"):
        return {"socle": "AN-API", "adresses": [
            "/api/sante", "/api/etapes", "/api/textes", "/api/textes/<uid>"]}
    if chemin == "/api/sante":
        return sante(cx)
    if chemin == "/api/etapes":
        return etapes(cx)
    if chemin == "/api/textes":
        return textes(cx, valeurs)
    if chemin.startswith("/api/textes/"):
        return texte(cx, urllib.parse.unquote(chemin[len("/api/textes/"):]))
    raise Erreur(404, f"adresse inconnue : {chemin}")


class Poignee(BaseHTTPRequestHandler):
    base = BASE
    protocol_version = "HTTP/1.1"

    def _repondre(self, code: int, charge: dict, corps_attendu: bool = True) -> None:
        corps = json.dumps(charge, ensure_ascii=False, indent=1).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        # Sans cet en-tête, aucune page web ne pourrait lire cette réponse.
        # C'est exactement ce qui manque aux portails du Parlement.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "public, max-age=300")
        self.end_headers()
        if corps_attendu:
            self.wfile.write(corps)

    def do_OPTIONS(self) -> None:                     # noqa: N802 — imposé par http.server
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:                         # noqa: N802 — imposé par http.server
        self._servir(avec_corps=True)

    def do_HEAD(self) -> None:                        # noqa: N802 — les outils de supervision
        self._servir(avec_corps=False)                # interrogent souvent en HEAD

    def _servir(self, avec_corps: bool) -> None:
        decoupe = urllib.parse.urlsplit(self.path)
        valeurs = urllib.parse.parse_qs(decoupe.query)
        cx = sqlite3.connect(f"file:{self.base}?mode=ro", uri=True)
        cx.row_factory = sqlite3.Row
        try:
            self._repondre(200, router(cx, decoupe.path, valeurs), avec_corps)
        except Erreur as erreur:
            self._repondre(erreur.code, {"erreur": erreur.message}, avec_corps)
        except sqlite3.Error as erreur:
            self._repondre(503, {"erreur": f"base indisponible : {erreur}."
                                           " Lancer ./recuperer.py d'abord."}, avec_corps)
        finally:
            cx.close()

    def log_message(self, format: str, *args) -> None:
        sys.stderr.write(f"{self.address_string()} — {format % args}\n")


def main() -> int:
    analyseur = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analyseur.add_argument("--hote", default="127.0.0.1")
    analyseur.add_argument("--port", type=int, default=8000)
    analyseur.add_argument("--base", type=pathlib.Path, default=BASE)
    options = analyseur.parse_args()

    if not options.base.exists():
        print(f"Base introuvable : {options.base}\nLancer d'abord ./recuperer.py",
              file=sys.stderr)
        return 1

    Poignee.base = options.base
    serveur = ThreadingHTTPServer((options.hote, options.port), Poignee)
    print(f"Socle en écoute sur http://{options.hote}:{options.port}", file=sys.stderr)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
