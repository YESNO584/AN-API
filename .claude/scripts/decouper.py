#!/usr/bin/env python3
"""Déplace des fonctions et des constantes d'un module vers d'autres, sans
les retaper.

    ./decouper.py socle/publier.py plan.json

`plan.json` dit, pour chaque module de destination, son en-tête et les noms
qu'il reçoit :

    {"paquet": "socle/publication",
     "modules": {"amendements": {"doc": "…", "noms": ["sans_les_doublons", …]}}}

Ce que l'outil garantit : chaque bloc déplacé part **avec les commentaires
qui le précèdent**, dans l'ordre d'origine ; les imports de chaque module
neuf sont ceux de l'original **réduits à ceux qu'il utilise** ; et les noms
qu'un module neuf emprunte à un autre sont importés explicitement. Ce qu'il
ne garantit pas : l'absence de cercle d'imports — c'est au test de le dire.

Le fichier d'origine est réécrit **sans** les blocs déplacés, et avec les
imports qu'il lui faut pour continuer d'y accéder.
"""
from __future__ import annotations

import ast
import json
import pathlib
import sys


def blocs(src: str) -> tuple[list[str], list[dict]]:
    """L'en-tête (docstring, __future__) et les blocs de niveau module.

    Un bloc est un nœud de l'arbre **et** les lignes de commentaire collées
    au-dessus : elles parlent de lui, elles le suivent.
    """
    lignes = src.split("\n")
    arbre = ast.parse(src)
    corps = arbre.body
    debut_code = 0
    # L'en-tête : docstring et `from __future__`, qui restent en place.
    for n in corps:
        est_doc = isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
        est_futur = isinstance(n, ast.ImportFrom) and n.module == "__future__"
        if est_doc or est_futur:
            debut_code = n.end_lineno
        else:
            break
    entete = lignes[:debut_code]
    resultat = []
    noeuds = [n for n in corps if n.end_lineno > debut_code]
    for i, n in enumerate(noeuds):
        # Remonter sur les commentaires collés (sans ligne vide entre).
        premiere = n.lineno - 1
        if getattr(n, "decorator_list", None):
            premiere = min(d.lineno for d in n.decorator_list) - 1
        k = premiere - 1
        while k >= 0 and lignes[k].strip().startswith("#"):
            k -= 1
        premiere = k + 1
        derniere = n.end_lineno            # exclusif, en index
        noms = []
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            noms = [n.name]
        elif isinstance(n, ast.Assign):
            noms = [t.id for t in n.targets if isinstance(t, ast.Name)]
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
            noms = [n.target.id]
        resultat.append({"noms": noms, "texte": "\n".join(lignes[premiere:derniere]),
                         "noeud": n,
                         "import": isinstance(n, (ast.Import, ast.ImportFrom))})
    return entete, resultat


def noms_utilises(texte: str) -> set[str]:
    try:
        arbre = ast.parse(texte)
    except SyntaxError:
        return set()
    return {n.id for n in ast.walk(arbre) if isinstance(n, ast.Name)} | \
           {n.value.id for n in ast.walk(arbre)
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)}


def noms_fournis_par_import(n: ast.AST) -> list[str]:
    if isinstance(n, ast.Import):
        return [(a.asname or a.name).split(".")[0] for a in n.names]
    if isinstance(n, ast.ImportFrom):
        return [a.asname or a.name for a in n.names]
    return []


def imports_utiles(imports: list[dict], corps: str) -> list[str]:
    utilises = noms_utilises(corps)
    gardes = []
    for b in imports:
        if any(nom in utilises for nom in noms_fournis_par_import(b["noeud"])):
            gardes.append(b["texte"])
    return gardes


def main() -> int:
    source = pathlib.Path(sys.argv[1])
    plan = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
    paquet = pathlib.Path(plan["paquet"])
    paquet.mkdir(exist_ok=True)
    nom_paquet = paquet.name

    src = source.read_text(encoding="utf-8")
    entete, tous = blocs(src)
    imports = [b for b in tous if b["import"]]
    code = [b for b in tous if not b["import"]]

    # Où va chaque nom.
    destination: dict[str, str] = {}
    for module, d in plan["modules"].items():
        for nom in d["noms"]:
            destination[nom] = module
    inconnus = set(destination) - {n for b in code for n in b["noms"]}
    if inconnus:
        print("Noms introuvables dans la source :", sorted(inconnus), file=sys.stderr)
        return 1

    par_module: dict[str, list[dict]] = {m: [] for m in plan["modules"]}
    restent = []
    for b in code:
        cibles = {destination.get(n) for n in b["noms"]} - {None}
        if len(cibles) > 1:
            print("Un bloc définit des noms de modules différents :", b["noms"], file=sys.stderr)
            return 1
        (par_module[cibles.pop()] if cibles else restent).append(b)

    # Qui définit quoi, pour les emprunts entre modules.
    definis: dict[str, str] = {}
    for m, bs in par_module.items():
        for b in bs:
            for n in b["noms"]:
                definis[n] = f"{nom_paquet}.{m}"
    for b in restent:
        for n in b["noms"]:
            definis[n] = source.stem

    def emprunts(bs: list[dict], moi: str) -> list[str]:
        corps = "\n".join(b["texte"] for b in bs)
        utilises = noms_utilises(corps)
        propres = {n for b in bs for n in b["noms"]}
        par_origine: dict[str, list[str]] = {}
        for n in sorted(utilises):
            if n in definis and n not in propres and definis[n] != moi:
                par_origine.setdefault(definis[n], []).append(n)
        return [f"from {o} import {', '.join(ns)}" for o, ns in sorted(par_origine.items())]

    for m, d in plan["modules"].items():
        bs = par_module[m]
        corps = "\n\n\n".join(b["texte"] for b in bs)
        lignes = ['"""' + d["doc"].rstrip() + '\n"""', "from __future__ import annotations", ""]
        lignes += imports_utiles(imports, corps)
        lignes += emprunts(bs, f"{nom_paquet}.{m}")
        lignes += ["", "", corps, ""]
        (paquet / f"{m}.py").write_text("\n".join(lignes), encoding="utf-8")
        print(f"  {paquet / (m + '.py')} : {len(bs)} blocs")

    corps = "\n\n\n".join(b["texte"] for b in restent)
    lignes = entete + [""] + imports_utiles(imports, corps) + emprunts(restent, source.stem)
    lignes += ["", "", corps, ""]
    source.write_text("\n".join(lignes), encoding="utf-8")
    print(f"  {source} : {len(restent)} blocs gardés")
    return 0


if __name__ == "__main__":
    sys.exit(main())
