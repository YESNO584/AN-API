#!/usr/bin/env python3
"""Les tests du droit consolidé voient-ils vraiment casser les règles ?

    cd .claude/scripts && ./mutations_legi.py

Un test qui ne casse pas quand la règle casse ne teste rien. Ce programme défait
une règle de `socle/legi.py` à la fois, relance `socle/test_legi.py`, et exige
qu'**au moins un test échoue, nommément**.

Deux précautions, l'une et l'autre apprises à ses dépens le 2026-09-03 :

- **Le travail se fait sur une copie**, jamais sur le vrai `socle/`. Une version
  antérieure modifiait le fichier et le restaurait dans un `finally` — ce qui ne
  protège de rien si le programme est tué.
- **Une mutation qui casse la syntaxe ne prouve rien.** Le fichier ne s'importe
  plus, tout échoue, et on croit la règle couverte. C'est exactement ce qui
  s'était passé sur le filtre de nature : la mutation supprimait deux lignes et
  laissait une indentation invalide. Chaque mutation est donc compilée d'abord.

Quand une règle de `legi.py` change, mettre `MUTATIONS` à jour : un motif
introuvable est signalé comme un manque, pas ignoré.
"""

from __future__ import annotations

import pathlib
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile

RACINE = pathlib.Path(__file__).resolve().parents[2]
SOCLE = RACINE / "socle"

# (ce qu'on défait, le motif exact, ce qu'on met à la place). Les remplacements
# gardent la syntaxe valable : `and True`, `if False`, un préfixe d'expression
# régulière — jamais une suppression de ligne.
MUTATIONS: list[tuple[str, str, str]] = [
    ("le contrôle « pas soi-même » de version_precedente",
     'and version.get("id") != soi\n', 'and True\n'),
    ("le refus de la date sentinelle",
     'if debut == SANS_FIN:\n        return None',
     'if False:\n        return None'),
    ("le contrôle « pas de rédaction d'avant » de est_un_ajout",
     'if precedent:\n        return False', 'if False:\n        return False'),
    ("le contrôle « il reste du texte »",
     'if not utile:\n        return False', 'if False:\n        return False'),
    ("l'exception des renvois pas encore saisis",
     'return not (est_en_attente(utile) and champ(xml, "TYPE") == TYPE_SANS_TEXTE)',
     'return True'),
    ("la reconnaissance d'un renvoi ailleurs qu'au début",
     r'r"\ba\s+(?:modifié', r'r"^a\s+(?:modifié'),
    ("le retrait des blockquote",
     'ancien, bloc = bloc, _BLOCKQUOTE.sub("", bloc)',
     'ancien, bloc = bloc, bloc'),
    ("le filtre sur la nature du texte porteur",
     'if not porteur.get("nature", "").startswith("LOI"):',
     'if not porteur.get("nature", "").startswith(""):'),
    ("le nettoyage des renvois pour un ajout",
     'sans_les_renvois(bloc) if ajout else nettoyer(bloc)', 'nettoyer(bloc)'),
    ("l'écart des rédactions mort-nées",
     'and not est_mort_ne(version.get("etat", ""))', 'and True'),
    ("la date d'effet d'une abrogation",
     'date = fin if quoi == "ABROGE" else debut', 'date = debut'),
]


def essayer(copie: pathlib.Path, nom: str, avant: str, apres: str,
            original: str) -> str | None:
    """Rend `None` si un test nommé voit la mutation, sinon dit ce qui manque."""
    if avant not in original:
        print(f"  ??  {nom}\n      motif introuvable — la règle a changé, "
              f"mettre MUTATIONS à jour")
        return f"{nom} (motif introuvable)"

    (copie / "legi.py").write_text(original.replace(avant, apres, 1))
    with tempfile.NamedTemporaryFile(suffix=".pyc") as sortie:
        try:
            py_compile.compile(str(copie / "legi.py"), cfile=sortie.name,
                               doraise=True)
        except py_compile.PyCompileError:
            print(f"  !!  {nom}\n      la mutation casse la syntaxe : "
                  f"elle ne prouve rien")
            return f"{nom} (mutation invalide)"

    fait = subprocess.run([sys.executable, "test_legi.py"], cwd=copie,
                          capture_output=True, text=True)
    vus = re.findall(r"^(?:FAIL|ERROR): (\w+)", fait.stderr, re.M)
    if not vus:
        print(f"  ÉCHEC : {nom}\n      aucun test nommé ne le voit "
              f"(code de sortie {fait.returncode})")
        return nom
    print(f"  vu par {len(vus)} test(s) : {nom}")
    print(f"      {', '.join(vus[:3])}{' …' if len(vus) > 3 else ''}")
    return None


def main() -> int:
    with tempfile.TemporaryDirectory() as bac:
        copie = pathlib.Path(bac) / "socle"
        shutil.copytree(SOCLE, copie,
                        ignore=shutil.ignore_patterns("*.db", "*.db-*", "public",
                                                      "archives_legi", "__pycache__"))
        original = (copie / "legi.py").read_text()

        temoin = subprocess.run([sys.executable, "test_legi.py"], cwd=copie,
                                capture_output=True, text=True)
        if temoin.returncode != 0:
            print("Les tests échouent déjà sans mutation : rien à mesurer.",
                  file=sys.stderr)
            print(temoin.stderr[-1500:], file=sys.stderr)
            return 1
        combien = re.search(r"^Ran (\d+) tests", temoin.stderr, re.M)
        print(f"{combien.group(1) if combien else '?'} tests passent sans mutation. "
              f"{len(MUTATIONS)} règles à défaire.\n")

        manquants = [m for m in (essayer(copie, *mutation, original)
                                 for mutation in MUTATIONS) if m]

    print()
    if manquants:
        print(f"{len(manquants)} règle(s) que les tests ne voient pas casser :")
        for m in manquants:
            print(f"  - {m}")
        return 1
    print("Toutes les règles listées sont vues casser par un test nommé.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
