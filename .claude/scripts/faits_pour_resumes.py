#!/usr/bin/env python3
"""Ce que chaque groupe a dit d'un texte, rassemblé pour en écrire le résumé.

Première moitié de la chaîne des résumés de débats, calquée sur celle des
descriptions :

    faits_pour_resumes.py        récolte les paroles, groupe par groupe
    (une IA, ou une personne)    écrit au plus 4 arguments par groupe
    assembler_resumes.py         contrôle, ajoute les positions de vote, range

Ce programme ne rédige rien : il récolte. Il lit les fichiers **déjà publiés**
par le socle — `paroles/<uid>.json` et `textes/<uid>.json` — et écrit un
fichier par texte, où les prises de parole sont regroupées par groupe
politique, dans l'ordre de l'hémicycle.

    ./faits_pour_resumes.py --sortie /tmp/debats [--textes DLR5L17N52922,…]
    ./faits_pour_resumes.py --sortie /tmp/debats --combien 10
    ./faits_pour_resumes.py --liste            # ce qui est disponible, et où

**Le vote n'est pas à écrire, il est relevé.** Le fichier de faits porte le
scrutin sur l'ensemble le plus récent, avec la position de chaque groupe, pour
que la rédaction sache de quoi elle parle — mais c'est `assembler_resumes.py`
qui inscrira ces positions dans le résumé publié, en les reprenant de la
source. Une phrase d'orateur ne décide donc jamais d'un vote affiché : mesuré
le 2026-09-02, l'UDR a voté *pour* les soins palliatifs pendant que son
orateur disait « votera contre » — il parlait de l'autre texte de la séance.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.error
import urllib.request

SOCLE = "https://yesno584.github.io/AN-API"
# De quoi reconnaître un argument sans recopier un discours de dix minutes.
# Les paroles complètes restent affichées dans l'application, mot pour mot :
# ce fichier-ci ne sert qu'à écrire.
CARACTERES_PAR_PAROLE = 2500


def lire(socle: str, chemin: str):
    """Un fichier publié, que le socle soit un dossier local ou une adresse."""
    if "://" not in socle:
        fichier = pathlib.Path(socle) / chemin
        if not fichier.exists():
            return None
        return json.loads(fichier.read_text(encoding="utf-8"))
    try:
        with urllib.request.urlopen(f"{socle}/{chemin}", timeout=60) as reponse:
            return json.loads(reponse.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
        return None


def vote_decisif(texte: dict) -> dict | None:
    """Le scrutin sur l'ensemble le plus récent — celui qui a tranché.

    Un texte peut en compter plusieurs : première lecture, puis lecture
    définitive. C'est le dernier qui dit ce que l'Assemblée a décidé.
    """
    sur_ensemble = [v for v in (texte.get("votes") or [])
                    if v.get("portee") == "ensemble"]
    if not sur_ensemble:
        return None
    return sorted(sur_ensemble, key=lambda v: v.get("date") or "")[-1]


def faits_du_texte(socle: str, uid: str, taille: int = CARACTERES_PAR_PAROLE) -> dict | None:
    texte = lire(socle, f"textes/{uid}.json")
    paroles = lire(socle, f"paroles/{uid}.json")
    if not texte or not paroles or not paroles.get("paroles"):
        return None

    vote = vote_decisif(texte)
    positions = {g["sigle"]: g for g in (vote or {}).get("groupes", [])}

    # Les groupes dans l'ordre de l'hémicycle quand le vote le donne, sinon
    # dans celui du fichier des paroles.
    ordre = {g["sigle"]: g.get("rang", 99) for g in (vote or {}).get("groupes", [])}
    par_groupe: dict[str, list[dict]] = {}
    for p in paroles["paroles"]:
        par_groupe.setdefault(p.get("sigle") or "sans groupe", []).append(p)

    groupes = []
    for sigle in sorted(par_groupe, key=lambda s: (ordre.get(s, 99), s)):
        dit = par_groupe[sigle]
        g = positions.get(sigle) or {}
        groupes.append({
            "sigle": sigle,
            # Relevé, pas à écrire : voir le docstring.
            "voteReleve": ({"position": g.get("position"), "pour": g.get("pour"),
                            "contre": g.get("contre"),
                            "abstentions": g.get("abstentions")} if g else None),
            "paroles": [{"nom": p.get("nom"), "date": p.get("date"),
                         "section": p.get("section"),
                         "texte": (p.get("texte") or "")[:taille]}
                        for p in dit],
        })

    return {
        "uid": uid,
        "titre": texte.get("titre"),
        "aEcrire": "au plus 4 arguments par groupe, tirés de ses paroles",
        "voteSurLEnsemble": ({"date": vote.get("date"), "sort": vote.get("sort"),
                              "objet": vote.get("objet"), "pour": vote.get("pour"),
                              "contre": vote.get("contre"),
                              "abstentions": vote.get("abstentions")}
                             if vote else None),
        "prisesDeParole": paroles.get("total"),
        "groupes": groupes,
    }


def disponibles(socle: str) -> list[dict]:
    """Les textes qui ont des paroles, du plus bavard au moins bavard."""
    index = lire(socle, "etat.json") or {}
    del index                                   # l'état ne les liste pas
    if "://" in socle:
        sys.exit("--liste demande un socle local (socle/public)")
    dossier = pathlib.Path(socle) / "paroles"
    rangs = []
    for fichier in dossier.glob("*.json"):
        d = json.loads(fichier.read_text(encoding="utf-8"))
        texte = lire(socle, f"textes/{fichier.stem}.json") or {}
        rangs.append({"uid": fichier.stem, "paroles": d.get("total", 0),
                      "groupes": len(d.get("groupes") or []),
                      "vote": bool(vote_decisif(texte)),
                      "titre": (texte.get("titre") or "")[:70]})
    return sorted(rangs, key=lambda x: -x["paroles"])


def main(argv: list[str] | None = None) -> int:
    a = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--socle", default="socle/public",
                   help="dossier publié, ou adresse du socle en ligne")
    a.add_argument("--sortie", type=pathlib.Path, help="où écrire les faits")
    a.add_argument("--textes", help="identifiants séparés par des virgules")
    a.add_argument("--combien", type=int,
                   help="les N textes les plus discutés, vote compris")
    a.add_argument("--taille", type=int, default=CARACTERES_PAR_PAROLE,
                   help="caractères gardés par prise de parole (2500 par défaut)")
    a.add_argument("--liste", action="store_true",
                   help="afficher ce qui est disponible, sans rien écrire")
    o = a.parse_args(argv)

    if o.liste:
        for x in disponibles(o.socle)[:60]:
            print(f'{x["uid"]}  {x["paroles"]:3d} paroles  {x["groupes"]:2d} groupes'
                  f'  {"vote" if x["vote"] else "    "}  {x["titre"]}')
        return 0

    if not o.sortie:
        sys.exit("--sortie est nécessaire")
    if o.textes:
        uids = [x.strip() for x in o.textes.split(",") if x.strip()]
    elif o.combien:
        uids = [x["uid"] for x in disponibles(o.socle)[:o.combien]]
    else:
        sys.exit("--textes ou --combien")

    o.sortie.mkdir(parents=True, exist_ok=True)
    ecrits = 0
    for uid in uids:
        faits = faits_du_texte(o.socle, uid, o.taille)
        if not faits:
            print(f"  {uid} : pas de paroles publiées", file=sys.stderr)
            continue
        (o.sortie / f"{uid}.json").write_text(
            json.dumps(faits, ensure_ascii=False, indent=1), encoding="utf-8")
        ecrits += 1
        print(f'  {uid} : {faits["prisesDeParole"]} paroles, '
              f'{len(faits["groupes"])} groupes, '
              f'{"vote relevé" if faits["voteSurLEnsemble"] else "sans vote sur l_ensemble"}')
    print(f"{ecrits} fichiers de faits dans {o.sortie}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
