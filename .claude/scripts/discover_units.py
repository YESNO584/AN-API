#!/usr/bin/env python3
"""
Splits a codebase into the units a checker reports on.

"Unit" is deliberately vague: a module, a package, a service, a top-level
folder — whatever this project considers one reportable thing. The strategy is
declared in code_rules.json under scope.unit_discovery, so swapping it is a
config edit, not a code change:

  directories_with_matching_manifest
      A unit is any directory holding a file named after itself
      (foo/foo.json). The convention in manifest-per-module codebases.
      Set "manifest_suffix" (default ".json").

  top_level_directories
      Every immediate child directory of the discovery root is a unit.
      The right default when a project has no manifest convention.

  single_unit
      The whole tree is one unit, named after the root folder. Use this for
      a small repo where per-unit reporting adds nothing.

Each unit is {"id", "path"}, with "path" relative to the discovery root, in
POSIX form. Sorted by id.

Usage:
  ./discover_units.py                 # table
  ./discover_units.py --json          # JSON array
  ./discover_units.py --rules PATH    # non-default rules file
"""
import json
import sys
from pathlib import Path

DEFAULT_RULES_PATH = Path(__file__).resolve().parent.parent / "code_rules.json"

DEFAULT_EXCLUDED = ["bin", "obj", "Library", "Temp", "node_modules", ".git"]


def load_config(rules_path=None):
    """Returns (project_root, unit_discovery_dict). project_root is the
    directory scope.root resolves against — the parent of the .claude folder
    holding the rules file, i.e. the repo root in a standard layout."""
    rules_path = Path(rules_path or DEFAULT_RULES_PATH).resolve()
    data = json.loads(rules_path.read_text(encoding="utf-8"))
    scope = data.get("scope", {})
    project_root = rules_path.parent.parent
    discovery = dict(scope.get("unit_discovery", {}))
    discovery.setdefault("strategy", "top_level_directories")
    discovery.setdefault("root", scope.get("root", "."))
    discovery.setdefault("manifest_suffix", ".json")
    discovery.setdefault("exclude_dir_names", DEFAULT_EXCLUDED)
    return project_root, discovery


def list_units(rules_path=None):
    project_root, cfg = load_config(rules_path)
    root = (project_root / cfg["root"]).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"discovery root not found: {root}")

    excluded = set(cfg["exclude_dir_names"])
    strategy = cfg["strategy"]

    if strategy == "single_unit":
        return [{"id": root.name, "path": "."}]

    if strategy == "top_level_directories":
        units = [{"id": d.name, "path": d.name}
                 for d in root.iterdir()
                 if d.is_dir() and d.name not in excluded and not d.name.startswith(".")]
        return sorted(units, key=lambda u: u["id"])

    if strategy == "directories_with_matching_manifest":
        suffix = cfg["manifest_suffix"]
        units = []
        for manifest in root.rglob("*" + suffix):
            directory = manifest.parent
            if directory.name != manifest.name[: -len(suffix)]:
                continue
            rel = directory.relative_to(root)
            if excluded.intersection(rel.parts):
                continue
            units.append({"id": directory.name, "path": rel.as_posix()})
        return sorted(units, key=lambda u: u["id"])

    raise ValueError(f"unknown unit_discovery strategy: {strategy!r}")


def unit_root(rules_path=None):
    """Absolute path the units' "path" values are relative to."""
    project_root, cfg = load_config(rules_path)
    return (project_root / cfg["root"]).resolve()


def main():
    args = sys.argv[1:]
    rules_path = None
    if "--rules" in args:
        rules_path = args[args.index("--rules") + 1]

    units = list_units(rules_path)

    if "--json" in args:
        print(json.dumps(units, indent=2))
        return

    print(f"{'UNIT':<45} PATH")
    for u in units:
        print(f"{u['id']:<45} {u['path']}")
    print(f"\nTotal: {len(units)} unit(s)")


if __name__ == "__main__":
    main()
