# Portable Claude Code kit

Everything in this folder works in **any** project. Nothing here knows what
codebase it was extracted from — no product names, no folder layout, no
absolute paths. It is a copy, not a move: the project it came from still runs
on its own `.claude/`, untouched.

## Install into a new project

From the target project's root:

```bash
mkdir -p .claude
cp -R /path/to/.claude-portable/hooks       .claude/
cp -R /path/to/.claude-portable/agents      .claude/
cp -R /path/to/.claude-portable/reference   .claude/
cp -R /path/to/.claude-portable/scripts     .claude/
cp    /path/to/.claude-portable/settings.json            .claude/settings.json
cp    /path/to/.claude-portable/code_rules.template.json .claude/code_rules.json
cp    /path/to/.claude-portable/LEARNINGS.template.md    .claude/LEARNINGS.md
cp    /path/to/.claude-portable/CLAUDE.template.md       ./CLAUDE.md
chmod +x .claude/hooks/*.sh .claude/scripts/*.py
```

Then do these four things, in order. Skipping the first one is the only way to
end up with a harness that looks configured and isn't.

1. **Fill in `CLAUDE.md`.** Every `<!-- FILL IN -->` block. The rules around
   them work as-is; the blocks are the only place project knowledge belongs.
2. **If the project is Unity**, merge `settings.unity.json`'s deny entries
   into `.claude/settings.json`. They keep Claude out of Unity's regenerated
   caches and the `.meta` sidecars.
3. **Mine the real conventions.** Run the `code-convention-miner` agent
   against the codebase and let it rewrite `.claude/code_rules.json`. What
   ships here is a generic C# baseline with empty `evidence` fields — useful
   on day one, but it is not yet *this* project's contract. See "Code rules"
   below.
4. **Check the hooks fire.** Start a session and confirm the reformulation
   reminder appears and the status line renders. A hook that fails silently
   is indistinguishable from one that isn't configured.

## What's here

### `hooks/`
| File | What it does |
|---|---|
| `enforce-scope.sh` | PreToolUse on Edit/Write. Resolves the target path (through symlinks and `..`) and blocks anything outside the project folder. A backstop for the `permissions.deny` globs, which patterns alone can't fully cover. |
| `inject-rules.sh` | UserPromptSubmit. Re-injects the "reformulate first, then wait for confirmation" rule on every message, so it survives context compaction. |
| `statusline.sh` | Model, project, git branch, and cost/context when the Claude Code version exposes them. |

The hooks need `jq` on the PATH.

### `settings.json`
Git allow/deny rules, the three hooks, the status line, `defaultMode: auto`.
Deliberately **not** included: anything referencing a specific tool installed
on one machine. Add those to `.claude/settings.local.json` in the target
project, where they belong.

One rule to keep in mind while that file grows: in a `Bash(...)` permission
rule, `*` means "anything from here on" and cannot be escaped. A rule whose
first `*` is not its last character approves far more than it appears to.
`LEARNINGS.template.md` carries the full explanation.

### `agents/`
| Agent | Reusable where |
|---|---|
| `code-convention-miner` | Any codebase. Reverse-engineers real conventions into a rules document. |
| `code-rule-checker-builder` | Any codebase. Turns that document into a working checker + report. |
| `config-portability-auditor` | Any project. Classifies a `.claude/` config into portable vs project-specific — this kit's own origin. |
| `runtime-test-log-triager` | Any project with a long device/CI test log. |
| `bulk-refactor-verifier` | Any codebase, most valuable where the compiler can't be run from the agent's environment. |
| `repeated-class-inventory` | Any codebase with per-module boilerplate repeated N times. |
| `unity-asset-relocation-planner` | Unity projects only. Plans `.asset`/`.meta` moves without orphaning GUIDs. |

### `scripts/`
| Script | Role |
|---|---|
| `discover_units.py` | Splits the codebase into reportable units. Three strategies, chosen in the rules file. |
| `code_rule_checker.py` | Applies `code_rules.json`. Two entry points: `check_unit(id)` and `check_all()`. |
| `code_rule_report.py` | Renders the result as console text and as the HTML report. |
| `audit_report_html.py` | The HTML page itself, shared by every checker. Build your next checker's report on this rather than a fifth copy of the same CSS. |

Run them from the `scripts/` directory (they import each other as
siblings):

```bash
cd .claude/scripts
./discover_units.py                 # what will be reported on
./code_rule_report.py               # text + write .claude/reports/code_rule_audit.html
./code_rule_report.py --json        # machine-readable
./code_rule_checker.py <unit_id>    # one unit, for a pre-commit gate
```

### `code_rules.template.json`
A generic C# baseline: 15 automated rules plus 3 marked manual, with the
`evidence` fields left empty on purpose.

**Everything about a rule is data.** Severity, regex, thresholds, and every
exemption (`known_exceptions`, `exempt_name_patterns`, `exempt_units`,
`exempt_type_suffix`) are read from the JSON at run time, so tuning a rule is
a config edit, never a code change. Four rules ship with `"enabled": false`
because they only make sense once a project opts in: `namespace-mirrors-folder`,
`class-naming-prefix`, `unit-manifest-present`,
`public-api-surface-single-entrypoint`.

Two honesty rules the checker enforces on itself:

- A rule whose `check.type` is `manual`, `manual_or_heuristic` or
  `manual_diff_review` is never turned into a finding. It is surfaced
  separately as needing human review.
- A `regex_required` rule the checker has no extraction site for is moved to
  that same manual list rather than silently reporting zero findings. A rule
  that quietly checks nothing is worse than one openly marked unautomated.

When adding an exemption, count the real occurrences first and write the count
into the rule's `evidence`. An exemption without evidence is indistinguishable
from a checker bug being papered over.

### `reference/store-apis.md`
How to list a publisher's live apps and their versions from the App Store
Connect API and the two Google Play APIs, including which credentials each one
needs and where the credential-free shortcuts stop working. Relevant to any
mobile project, unrelated to any particular one.

## What is deliberately not here

- **Anything machine-specific**: absolute home paths, locally installed
  tooling, one user's permission allowlist.
- **Domain checkers**: a dependency-graph checker, an SDK-version manifest
  auditor and a runtime unit-test contract checker all exist in the project
  this kit came from. They encode that project's architecture, and a
  de-domained version would be a rewrite, not a copy. Use
  `code-rule-checker-builder` to grow the equivalent for a new project.
- **`settings.local.json`**: session-accumulated permissions are never
  portable. Start a fresh one.

## Verifying the kit is still clean

The kit's one hard invariant is that it names no specific project. Re-check it
after any edit:

```bash
grep -rniE '<your product name>|/Users/|/home/' . && echo "NOT CLEAN" || echo "clean"
```
