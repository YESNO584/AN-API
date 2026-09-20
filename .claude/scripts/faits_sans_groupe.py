#!/usr/bin/env python3
"""Les paroles que la source n'a rattachées à aucun groupe, texte par texte.

Un ministre qui défend son texte, un non-inscrit, ou un député que le
rapprochement orateur → groupe a manqué : leurs paroles sont publiées comme les
autres, mais **hors de la liste des groupes**. Elles n'avaient donc jamais de
résumé.

Ce programme les récolte pour qu'on puisse les écrire, sans toucher aux
résumés déjà faits : chaque fichier de sortie porte **les groupes déjà écrits,
tels quels**, plus les paroles à traiter. La rédaction rend un lot complet, et
rien n'est perdu — `assembler_resumes.py` remplace l'entrée d'un texte en
entier.

    ./faits_sans_groupe.py --sortie /tmp/seuls

**Deux cas à distinguer, et c'est à la rédaction de le faire :**

  — l'orateur **revendique un groupe** (« le groupe EPR abordera ce texte
    ainsi ») : son argument va sous le sigle de ce groupe, avec les autres ;
  — l'orateur ne revendique rien, ou c'est un membre du gouvernement : son
    argument va sous son nom, dans `orateurs`.

Mesuré le 2026-09-20 : 128 paroles sur 2 976, dans 91 textes, chez 60
orateurs — le reliquat attendu des 95,6 % d'attribution.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

RACINE = pathlib.Path(__file__).resolve().parents[2]
PUBLIE = RACINE / "socle" / "public"
RESUMES = RACINE / "socle" / "resumes_debats.json"
# De quoi juger ce qu'un orateur a dit, et s'il parle au nom d'un groupe.
CARACTERES = 2500


def main(argv: list[str] | None = None) -> int:
    a = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--sortie", type=pathlib.Path, required=True)
    o = a.parse_args(argv)
    o.sortie.mkdir(parents=True, exist_ok=True)

    deja = json.loads(RESUMES.read_text(encoding="utf-8")).get("resumes") or {}
    ecrits = 0
    for fichier in sorted((PUBLIE / "paroles").glob("*.json")):
        uid = fichier.stem
        d = json.loads(fichier.read_text(encoding="utf-8"))
        seules = [p for p in (d.get("paroles") or []) if not p.get("sigle")]
        if not seules:
            continue
        texte = json.loads((PUBLIE / "textes" / f"{uid}.json").read_text(encoding="utf-8"))
        r = deja.get(uid) or {}
        (o.sortie / f"{uid}.json").write_text(json.dumps({
            "uid": uid,
            "titre": texte.get("titre"),
            "aEcrire": "les paroles ci-dessous, sous le sigle du groupe que "
                       "l'orateur revendique, ou sous son nom s'il n'en "
                       "revendique aucun",
            "groupesDejaEcrits": {g["sigle"]: g["arguments"]
                                  for g in (r.get("groupes") or [])},
            "sigles": [g["sigle"] for g in (d.get("groupes") or [])],
            "aTraiter": [{"nom": p.get("nom"), "date": p.get("date"),
                          "section": p.get("section"),
                          "texte": (p.get("texte") or "")[:CARACTERES]}
                         for p in seules],
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        ecrits += 1
        print(f'  {uid} : {len(seules)} parole(s), '
              f'{len(r.get("groupes") or [])} groupe(s) déjà écrits')
    print(f"{ecrits} fichiers dans {o.sortie}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
