#!/usr/bin/env python3
"""
Applies the rules declared in code_rules.json to a codebase's first-party C#.

Design: severities, regex patterns, numeric thresholds AND exemptions are all
read live from the JSON. Editing the JSON — by hand, or via the
code-convention-miner agent — changes what the checker does without touching
this file. The one thing the JSON cannot express is WHERE in a line to look
for a given rule's identifier (a rule's "applies_to" is prose, not a machine
pattern), so a small per-rule EXTRACTION regex lives here; the naming pattern
it validates against still comes from the JSON.

Rules whose check.type is "manual", "manual_or_heuristic" or
"manual_diff_review" cannot be mechanically verified and are never turned into
findings — they are surfaced separately under check_all()["manualRules"] for a
human or agent to apply judgement to. A rule with "enabled": false is skipped
entirely; that is how the template ships rules that only make sense once a
project opts into them.

Two public entry points:
  check_unit(unit_id)  -> one unit's result dict
  check_all()          -> {"total", "rulesVersion", "manualRules", "units",
                            "summary"}

See discover_units.py for how the codebase is split into units, and
code_rule_report.py for rendering the result as text or HTML.

Usage:
  ./code_rule_checker.py                # JSON for the whole project
  ./code_rule_checker.py <unit_id>      # JSON for one unit
"""
import json
import re
import sys
from pathlib import Path

import discover_units

DEFAULT_RULES_PATH = Path(__file__).resolve().parent.parent / "code_rules.json"

MANUAL_CHECK_TYPES = {"manual", "manual_or_heuristic", "manual_diff_review"}

# This rule hunts for commented-out code, so it must see raw lines. Every
# other regex rule runs against comment-stripped text.
KEEP_COMMENTS_FOR_RULES = {"no-commented-out-code"}

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}

TYPE_DECL_RE = re.compile(
    r'\b(?:public|internal)\s+(?:abstract\s+|sealed\s+|static\s+|partial\s+)*'
    r'(class|struct|interface|enum)\s+([A-Za-z_]\w*)')

# Per-rule extraction regex: finds the candidate declaration and captures the
# identifier that the rule's JSON "pattern" must then validate. The second
# element, when present, skips a match whose text contains it.
EXTRACTORS = {
    "class-naming-prefix": (
        re.compile(r'\b(?:public|internal)\s+(?:abstract\s+|sealed\s+|static\s+|partial\s+)*'
                   r'(?:class|struct)\s+([A-Za-z_]\w*)', re.MULTILINE),
        None,
    ),
    "interface-naming-i-prefix": (
        re.compile(r'\b(?:public|internal)\s+interface\s+([A-Za-z_]\w*)', re.MULTILINE),
        None,
    ),
    "enum-naming-pascalcase": (
        re.compile(r'\b(?:public|internal)\s+enum\s+([A-Za-z_]\w*)', re.MULTILINE),
        None,
    ),
    "private-field-underscore-camelcase": (
        # (?!const\b) excludes consts (their own rule); (?:;|=(?!>)) excludes
        # expression-bodied properties ('=>'), which aren't fields at all.
        re.compile(r'^\s*private\s+(?!const\b)(?:static\s+|readonly\s+)*[\w<>\[\],.\? ]+?\s+'
                   r'(_?[A-Za-z_]\w*)\s*(?:;|=(?!>))', re.MULTILINE),
        None,
    ),
    "constant-upper-snake-case": (
        re.compile(r'^\s*(?:public|private|protected|internal)?\s*const\s+[\w<>\[\], ]+?\s+'
                   r'([A-Za-z_]\w*)\s*=', re.MULTILINE),
        None,
    ),
    "public-member-pascalcase": (
        re.compile(r'^\s*(?:public|protected)\s+(?:static\s+|virtual\s+|override\s+|abstract\s+|'
                   r'readonly\s+|async\s+)*[\w<>\[\], .\?]+?\s+([A-Za-z_]\w*)\s*(?:\(|=>|\{)',
                   re.MULTILINE),
        # Skip operators and indexers, and skip TYPE declarations: with Allman
        # braces, 'public enum foo' + '{' on the next line otherwise parses as
        # a member named 'foo' of type 'enum', producing a second, wrongly
        # attributed finding on top of the naming rule that really owns it.
        re.compile(r'\boperator\b|this\s*\[|\b(?:class|struct|interface|enum|delegate|event|namespace)\b'),
    ),
}


# --------------------------------------------------------------------------
# configuration
# --------------------------------------------------------------------------

def load_rules(rules_path=None):
    """Returns (data, automated_rules, manual_rules). Disabled rules are in
    neither list."""
    path = Path(rules_path or DEFAULT_RULES_PATH)
    data = json.loads(path.read_text(encoding="utf-8"))
    automated, manual = [], []
    for rule in data["rules"]:
        if rule.get("enabled") is False:
            continue
        if rule["check"]["type"] in MANUAL_CHECK_TYPES:
            manual.append(rule)
        else:
            automated.append(rule)
    return data, automated, manual


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def _strip_line_comments(text):
    return "\n".join(line.split("//", 1)[0] for line in text.splitlines())


def _lineno(text, pos):
    return text.count("\n", 0, pos) + 1


def _finding(rule, rel_path, line, message, severity=None):
    return {
        "rule": rule["id"], "category": rule["category"],
        "severity": severity or rule["severity"],
        "file": rel_path, "line": line, "message": message,
    }


def _compiled(patterns):
    return [re.compile(p) for p in (patterns or [])]


def _primary_type_name(text):
    m = TYPE_DECL_RE.search(text)
    return m.group(2) if m else None


def _is_vendor(path, text, vendor_cfg):
    """Vendor code must never be linted: it produces violations nobody can act
    on and drowns the real findings. Two signals, both optional — a path
    marker, and (strongest, when a project prefixes its own types) a file
    whose every declared class/struct lacks that prefix."""
    for marker in vendor_cfg.get("path_contains_any") or []:
        if marker in path.parts:
            return True
    prefix = vendor_cfg.get("type_prefix")
    if prefix:
        # Check EVERY declared class/struct, not just the first — a vendor
        # file can declare an enum or a helper first, which is not itself a
        # vendor signal, before its actual vendor classes.
        class_like = [m.group(2) for m in TYPE_DECL_RE.finditer(text) if m.group(1) in ("class", "struct")]
        if class_like and all(not name.startswith(prefix) for name in class_like):
            return True
    return False


# --------------------------------------------------------------------------
# per-check implementations
# --------------------------------------------------------------------------

def _check_indentation(rule, rel_path, raw):
    findings = []
    for i, line in enumerate(raw.splitlines(), start=1):
        leading = line[: len(line) - len(line.lstrip())]
        if "\t" in leading:
            findings.append(_finding(rule, rel_path, i, "Line is indented with a tab, not spaces"))
    return findings


def _check_regex_pattern(rule, rel_path, raw, is_forbidden):
    text = raw if rule["id"] in KEEP_COMMENTS_FOR_RULES else _strip_line_comments(raw)
    pattern = re.compile(rule["check"]["pattern"], re.MULTILINE)
    findings = []
    for m in pattern.finditer(text):
        snippet = m.group(0).strip()[:80]
        verb = "matches a forbidden pattern" if is_forbidden else "flagged"
        findings.append(_finding(rule, rel_path, _lineno(text, m.start()),
                                 f"'{snippet}' {verb} ({rule['id']})"))
    return findings


def _check_line_length(rule, rel_path, raw):
    warn_over, error_over = rule["check"]["warn_over"], rule["check"]["error_over"]
    findings = []
    for i, line in enumerate(raw.splitlines(), start=1):
        length = len(line)
        if length > error_over:
            findings.append(_finding(rule, rel_path, i, f"Line is {length} chars (> {error_over})", "error"))
        elif length > warn_over:
            findings.append(_finding(rule, rel_path, i, f"Line is {length} chars (> {warn_over})"))
    return findings


def _check_line_count(rule, rel_path, raw):
    warn_over, error_over = rule["check"]["warn_over"], rule["check"]["error_over"]
    n = len(raw.splitlines())
    if n > error_over:
        return [_finding(rule, rel_path, None, f"File is {n} lines (> {error_over})", "error")]
    if n > warn_over:
        return [_finding(rule, rel_path, None, f"File is {n} lines (> {warn_over})")]
    return []


def _check_filename_matches_type(rule, rel_path, raw, stem):
    known_exceptions = set(rule["check"].get("known_exceptions", []))
    types = [m.group(2) for m in TYPE_DECL_RE.finditer(raw)
             if m.group(1) in ("class", "struct", "interface", "enum")
             and m.group(2) not in known_exceptions]
    if not types:
        return []
    if len(types) > 1:
        return [_finding(rule, rel_path, None,
                         f"{len(types)} public types declared in one file: {', '.join(types)}")]
    if types[0] != stem:
        return [_finding(rule, rel_path, None,
                         f"Public type '{types[0]}' does not match filename '{stem}.cs'")]
    return []


_ANY_NAMESPACE_RE = re.compile(r'^\s*namespace\s+([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)*)',
                               re.MULTILINE)


def _check_namespace_matches_path(rule, rel_path, raw, unit_rel_path):
    """Every namespace is examined, including one that doesn't start with the
    project's root namespace at all. Matching only namespaces under the root
    would make the worst case — a first-party file declared in a completely
    foreign namespace — the one case the rule stays silent about."""
    namespace_root = rule["check"]["namespace_root"]
    category_parts = [p for p in unit_rel_path.split("/")[:-1] if p not in (".", "")]
    expected = namespace_root + ("." + ".".join(category_parts) if category_parts else "")
    findings = []
    for m in _ANY_NAMESPACE_RE.finditer(raw):
        ns = m.group(1)
        if ns == expected or ns.startswith(expected + "."):
            continue
        if ns == namespace_root or ns.startswith(namespace_root + "."):
            message = f"namespace '{ns}' does not start with expected '{expected}'"
        else:
            message = (f"namespace '{ns}' is outside the project root namespace "
                       f"'{namespace_root}' (expected '{expected}')")
        findings.append(_finding(rule, rel_path, _lineno(raw, m.start()), message))
    return findings


def _check_regex_required(rule, rel_path, raw):
    extractor_entry = EXTRACTORS.get(rule["id"])
    if extractor_entry is None:
        # A regex_required rule with no extraction site defined here cannot be
        # applied. Silently skipping it would be a lie about coverage, so it
        # is reported to the caller as a manual rule instead (see _split_rules).
        return []
    extractor, skip_re = extractor_entry
    validator = re.compile(rule["check"]["pattern"])
    known_exceptions = set(rule["check"].get("known_exceptions", []))
    exempt_patterns = _compiled(rule["check"].get("exempt_name_patterns"))

    findings = []
    for m in extractor.finditer(raw):
        name = m.group(1)
        if name in known_exceptions:
            continue
        if skip_re and skip_re.search(m.group(0)):
            continue
        if any(p.match(name) for p in exempt_patterns):
            continue
        if not validator.match(name):
            findings.append(_finding(rule, rel_path, _lineno(raw, m.start()),
                                     f"'{name}' does not match required naming pattern for {rule['id']}"))
    return findings


def _check_unit_manifest(rule, unit_dir, unit_id, rel_dir):
    pattern = rule["check"]["pattern"]
    if any(unit_dir.glob(pattern)):
        return []
    return [_finding(rule, rel_dir, None,
                     f"No manifest matching '{pattern}' found for unit '{unit_id}'")]


# --------------------------------------------------------------------------
# driving
# --------------------------------------------------------------------------

def _check_file(automated_rules, path, rel_path, unit_id, unit_rel_path, raw):
    stem = path.stem
    findings = []

    for rule in automated_rules:
        check = rule["check"]
        ctype = check["type"]

        if unit_id in set(check.get("exempt_units", [])):
            continue
        exempt_suffix = check.get("exempt_type_suffix")
        if exempt_suffix:
            primary = _primary_type_name(raw)
            if primary and primary.endswith(exempt_suffix):
                continue

        if ctype == "no_tabs_and_indent_multiple_of":
            findings += _check_indentation(rule, rel_path, raw)
        elif ctype in ("regex_forbidden", "regex_flagged"):
            findings += _check_regex_pattern(rule, rel_path, raw, ctype == "regex_forbidden")
        elif ctype == "line_length":
            findings += _check_line_length(rule, rel_path, raw)
        elif ctype == "line_count":
            findings += _check_line_count(rule, rel_path, raw)
        elif ctype == "filename_matches_public_type":
            findings += _check_filename_matches_type(rule, rel_path, raw, stem)
        elif ctype == "namespace_matches_path":
            findings += _check_namespace_matches_path(rule, rel_path, raw, unit_rel_path)
        elif ctype == "regex_required":
            findings += _check_regex_required(rule, rel_path, raw)
        # "sibling_file_exists" is unit-level, handled in _analyze_one.

    return findings


def _split_rules(automated_rules):
    """A regex_required rule this checker has no extraction regex for is not
    automated, whatever the JSON says. Move it to the manual list rather than
    reporting zero findings for it — a rule that silently checks nothing is
    worse than one openly marked as needing review."""
    runnable, unimplemented = [], []
    for rule in automated_rules:
        if rule["check"]["type"] == "regex_required" and rule["id"] not in EXTRACTORS:
            unimplemented.append(rule)
        else:
            runnable.append(rule)
    return runnable, unimplemented


def _analyze_one(unit, automated_rules, root, project_root, scope):
    unit_id, rel = unit["id"], unit["path"]
    unit_dir = root if rel == "." else root / rel
    vendor_cfg = scope.get("vendor_detection", {})
    exclude_parts = set(scope.get("exclude_path_parts", []))

    all_files, checked, excluded = [], [], []
    for f in sorted(unit_dir.rglob("*.cs")):
        if exclude_parts.intersection(f.parts):
            continue
        all_files.append(f)
        try:
            text = f.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            continue
        (excluded if _is_vendor(f, text, vendor_cfg) else checked).append((f, text))

    findings = []
    for f, text in checked:
        try:
            rel_path = str(f.relative_to(project_root))
        except ValueError:
            rel_path = str(f)
        findings += _check_file(automated_rules, f, rel_path, unit_id, rel, text)

    manifest_rule = next((r for r in automated_rules if r["check"]["type"] == "sibling_file_exists"), None)
    if manifest_rule:
        findings += _check_unit_manifest(manifest_rule, unit_dir, unit_id, rel)

    counts = {"error": 0, "warning": 0, "info": 0}
    for f in findings:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1

    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f["severity"], 3), f["file"], f["line"] or 0))

    return {
        "id": unit_id, "path": rel,
        "totalFiles": len(all_files), "checkedFiles": len(checked), "excludedFiles": len(excluded),
        "findings": findings, "counts": counts,
        "clean": counts["error"] == 0 and counts["warning"] == 0,
    }


def _manual_entry(rule, note=""):
    return {"id": rule["id"], "category": rule["category"], "severity": rule["severity"],
            "description": rule["description"] + (f" [{note}]" if note else "")}


def check_unit(unit_id, rules_path=None):
    """Runs every automated rule against one unit's first-party .cs files
    (vendored files inside the unit are detected and skipped). Returns the
    unit's result dict: file counts, every finding, counts by severity, and a
    'clean' flag (no error/warning findings; info does not affect it)."""
    units = discover_units.list_units(rules_path)
    unit = next((u for u in units if u["id"] == unit_id), None)
    if unit is None:
        raise ValueError(f"Unknown unit id: {unit_id}")

    data, automated, _ = load_rules(rules_path)
    runnable, _unimplemented = _split_rules(automated)
    root = discover_units.unit_root(rules_path)
    project_root = Path(rules_path or DEFAULT_RULES_PATH).resolve().parent.parent
    return _analyze_one(unit, runnable, root, project_root, data.get("scope", {}))


def check_all(rules_path=None):
    """Applies check_unit()'s analysis to every discovered unit. Returns
    {"total", "rulesVersion", "manualRules", "units", "summary"}."""
    data, automated, manual = load_rules(rules_path)
    runnable, unimplemented = _split_rules(automated)
    units = discover_units.list_units(rules_path)
    root = discover_units.unit_root(rules_path)
    project_root = Path(rules_path or DEFAULT_RULES_PATH).resolve().parent.parent
    scope = data.get("scope", {})

    results = [_analyze_one(u, runnable, root, project_root, scope) for u in units]

    clean_count = sum(1 for r in results if r["clean"])
    by_severity = {"error": 0, "warning": 0, "info": 0}
    by_rule = {}
    for r in results:
        for f in r["findings"]:
            by_severity[f["severity"]] = by_severity.get(f["severity"], 0) + 1
            by_rule[f["rule"]] = by_rule.get(f["rule"], 0) + 1

    manual_rules = [_manual_entry(r) for r in manual]
    manual_rules += [_manual_entry(r, "no extraction site implemented for this rule id")
                     for r in unimplemented]

    return {
        "total": len(units),
        "rulesVersion": data.get("version"),
        "manualRules": manual_rules,
        "units": results,
        "summary": {
            "clean": clean_count, "flagged": len(results) - clean_count,
            "totalFindings": sum(by_severity.values()),
            "bySeverity": by_severity, "byRule": by_rule,
        },
    }


def main():
    args = [a for a in sys.argv[1:]]
    rules_path = None
    if "--rules" in args:
        i = args.index("--rules")
        rules_path = args[i + 1]
        del args[i:i + 2]

    if args:
        print(json.dumps(check_unit(args[0], rules_path), indent=2))
    else:
        print(json.dumps(check_all(rules_path), indent=2))


if __name__ == "__main__":
    main()
