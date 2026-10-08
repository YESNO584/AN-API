#!/usr/bin/env python3
"""Mesure la longueur des fichiers et des fonctions, et refuse ce qui dépasse.

    ./longueurs.py                    # l'état des lieux, et le verdict
    ./longueurs.py --fichier 350      # avec un autre seuil de fichier
    ./longueurs.py --fonction 40

**Un fichier long n'est pas une faute en soi : c'est un signal.** Aucune norme
Python ne fixe de longueur de fichier — PEP 8 limite la ligne, pas le module ;
pylint avertit à 1 000. Le seuil retenu ici est celui du projet, et la vraie
règle est *une responsabilité par fichier*. Le nombre sert à la faire respecter.

La règle des fonctions, elle, est celle que les guides de style mesurent
vraiment : au-delà d'une soixantaine de lignes, une fonction fait plusieurs
choses.

Ce qui est compté : le Python de `socle/` et de `.claude/scripts/`, le script
et le style de la maquette. Ce qui ne l'est pas : les fichiers produits par un
programme (`.claude/reports/`), les données, et `tmp/`.
"""
from __future__ import annotations

import argparse
import ast
import pathlib
import re
import sys

RACINE = pathlib.Path(__file__).resolve().parents[2]
SEUIL_FICHIER = 500
SEUIL_FONCTION = 60
# Les deux seuils dont on fait l'état des lieux, quel que soit celui retenu.
PALIERS = (350, 500)

DOSSIERS = ("socle", ".claude/scripts", "maquette")
EXTENSIONS = {".py", ".js", ".css", ".html"}
EXCLUS = ("/public/", "/__pycache__/", "/tmp/", "/.claude/reports/")


def fichiers() -> list[pathlib.Path]:
    trouves = []
    for d in DOSSIERS:
        for p in (RACINE / d).rglob("*"):
            if p.suffix in EXTENSIONS and not any(x in str(p) for x in EXCLUS):
                trouves.append(p)
    return sorted(trouves)


def longueur(p: pathlib.Path) -> int:
    return p.read_text(encoding="utf-8", errors="replace").count("\n") + 1


def fonctions_python(p: pathlib.Path) -> list[tuple[str, int, int]]:
    """(nom, ligne, longueur) de chaque fonction, méthodes comprises."""
    try:
        arbre = ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    return [(n.name, n.lineno, n.end_lineno - n.lineno + 1)
            for n in ast.walk(arbre)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]


# Une fonction JavaScript au niveau du fichier, ou une méthode d'objet : on
# compte jusqu'à l'accolade qui la ferme, en suivant la profondeur. C'est une
# mesure de forme, pas une analyse du langage — assez pour une règle de taille.
DEBUT_JS = re.compile(r"^\s*(?:async\s+)?function\s+(\w+)\s*\(")


def fonctions_js(p: pathlib.Path) -> list[tuple[str, int, int]]:
    lignes = p.read_text(encoding="utf-8", errors="replace").split("\n")
    trouvees, i = [], 0
    while i < len(lignes):
        m = DEBUT_JS.match(lignes[i])
        if not m:
            i += 1
            continue
        profondeur, j, ouverte = 0, i, False
        while j < len(lignes):
            profondeur += lignes[j].count("{") - lignes[j].count("}")
            if "{" in lignes[j]:
                ouverte = True
            if ouverte and profondeur <= 0:
                break
            j += 1
        trouvees.append((m.group(1), i + 1, j - i + 1))
        i = j + 1
    return trouvees


def fonctions(p: pathlib.Path) -> list[tuple[str, int, int]]:
    if p.suffix == ".py":
        return fonctions_python(p)
    if p.suffix in (".js", ".html"):
        return fonctions_js(p)
    return []


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--fichier", type=int, default=SEUIL_FICHIER)
    a.add_argument("--fonction", type=int, default=SEUIL_FONCTION)
    a.add_argument("--tout", action="store_true", help="lister tous les fichiers")
    o = a.parse_args()

    tous = [(p, longueur(p)) for p in fichiers()]
    longs = sorted(((p, n) for p, n in tous if n > o.fichier), key=lambda x: -x[1])
    grosses = sorted(((p, nom, l, n) for p, _ in tous for nom, l, n in fonctions(p)
                      if n > o.fonction), key=lambda x: -x[3])

    rel = lambda p: p.relative_to(RACINE)
    print(f"{len(tous)} fichiers de code mesurés.\n")
    print("État des lieux par palier :")
    for s in sorted(set(PALIERS) | {o.fichier}):
        dep = [p for p, n in tous if n > s]
        print(f"  > {s:4} lignes : {len(dep):2} fichier{'s' if len(dep) > 1 else ''}")
    if o.tout:
        print()
        for p, n in sorted(tous, key=lambda x: -x[1]):
            print(f"  {n:5}  {rel(p)}")

    print(f"\nFichiers au-dessus de {o.fichier} lignes : {len(longs)}")
    for p, n in longs:
        print(f"  {n:5}  {rel(p)}")
    print(f"\nFonctions au-dessus de {o.fonction} lignes : {len(grosses)}")
    for p, nom, l, n in grosses:
        print(f"  {n:4}  {rel(p)}:{l}  {nom}")

    faute = bool(longs or grosses)
    print("\n" + ("REFUSÉ : la règle de longueur n'est pas tenue."
                  if faute else "Tout est sous les seuils."))
    return 1 if faute else 0


if __name__ == "__main__":
    sys.exit(main())
