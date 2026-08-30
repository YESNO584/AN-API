# AN-API — Project Memory

## Each prompt triggers these rules
- Never edit anything outside of this folder, or nested folders.
- Limit all read operations to the scope of this project, except if explicitly
  required by the prompt. Reading is allowed for any file or internet source
  shared directly in a message.
- Reformulate every prompt to make it optimal for Claude Code, and ask for
  confirmation. Only start responding after the reformulation is confirmed.

## Architecture
- **The repository is empty.** As of this file's creation the only content is
  the Claude harness itself (`.claude/` + this file). There is no source code,
  no build, no tests, no dependency manifest.
- Because of that, everything below marked *(pending)* is a placeholder that
  states what is unknown — not a description of something that exists. Do not
  reason as if any of it were already true.
- *(pending)* Where first-party code lives — no source folder has been created
  yet.
- *(pending)* What the unit of work is (module / package / service / endpoint)
  and what every unit must implement.
- *(pending)* Where the public API surface is declared.
- **First real task rule:** the first session that adds actual code to this
  repository must replace this section with the real map, and re-run step 3 of
  `.claude/README.md` (the `code-convention-miner` agent) so `.claude/code_rules.json`
  stops being a generic template. Until then, treat any architectural claim
  about this project as unverified.

## Read these first
- `.claude/LEARNINGS.md` — cross-session lessons. Read at the start of every
  session; append to it at the end of one.
- `.claude/code_rules.json` — the code-quality contract the checker enforces.
  Worth reading before writing code, because it is currently a **generic C#
  template**, not this project's rules: its `scope.include_globs` is `**/*.cs`
  and every `evidence` field is empty. If this project turns out not to be C#,
  that file is wrong and must be re-mined before its report means anything.
- `.claude/reference/store-apis.md` — how to list a publisher's live apps and
  versions from the App Store Connect and Google Play APIs. Only relevant if
  this API ends up talking to the mobile stores; ignore otherwise.

## Checks
| Checker | How to run | Report |
|---|---|---|
| Code rules | `cd .claude/scripts && ./code_rule_report.py` | `.claude/reports/code_rule_audit.html` |
| Code rules, one unit | `cd .claude/scripts && ./code_rule_checker.py <unit_id>` | console |
| Unit discovery | `cd .claude/scripts && ./discover_units.py` | console |

**When it MUST be run:** before any commit that adds or changes source files,
and again before opening a pull request. It is not wired into a git hook —
nothing runs it for you.

**Caveat that outranks the table:** the checker matches `**/*.cs` only, so
until `.claude/code_rules.json` is mined against real code it will report
"0 findings" on a non-C# codebase. A clean run from an unmined rules file is
not evidence of clean code — it is evidence that nothing was checked.

## External / vendored code
- None yet — the repository has no third-party code in-tree.
- When vendored code is added, list its folders here and register them in
  `.claude/code_rules.json` under `scope.vendor_detection.path_contains_any`,
  so the checker stops linting code we do not own.
- The standing rule for that code: **wrap, don't patch.** If a bug looks like
  it is in vendor code, check our wrapper first.

# Project Rules

## Scope enforcement (mechanically enforced — see .claude/settings.json)
- Edits/writes are restricted to this folder and its subfolders. This is
  enforced by `permissions.deny` plus the `enforce-scope.sh` PreToolUse hook —
  it is not optional and does not depend on remembering this instruction.
- Reads are limited to this project's scope. Reads outside the project prompt
  for explicit confirmation (`permissions.ask`) rather than happening
  silently. Files or internet sources shared directly in a prompt are always
  fine to read.

## Before starting any task
Never begin acting on a prompt directly. First, restate the request in a
clear, optimized form for Claude Code:
- explicit scope (which files/subsystems this touches)
- expected output/deliverable
- constraints or things to avoid

Then ask: "Is this correct?" and stop. Do not read (beyond what's needed to
reformulate), edit, or run anything until the user explicitly confirms the
reformulation. This is reinforced on every message via a UserPromptSubmit
hook (`inject-rules.sh`), but the actual "wait for confirmation" behavior
depends on Claude following it — no hook can force a pause mid-turn.

## Self-configuration (standing authorization)
Claude may create, edit and override its own harness configuration in this
project without asking each time: `.claude/agents/**`, `.claude/skills/**`,
`.claude/hooks/**`, `.claude/scripts/**`, `.claude/settings*.json`, this file,
any nested `CLAUDE.md`, `.claude/LEARNINGS.md`, and the auto-memory directory.
The intent is that each session's learnings are written back into config so
the next session starts better informed.

Editing product source is NOT covered by this — source changes are asked for
first, as usual. Adding a `CLAUDE.md` inside a subsystem folder is.

Product source, for this rule, means **every file in the repository that is
not `.claude/**` and not this `CLAUDE.md`.** That deliberately broad wording
is the only safe one while the repository is empty: with no source layout to
name, a narrower glob would silently exempt whatever gets created first.
Replace it with the real glob (e.g. `src/**/*.ts`) in the same session that
creates the source folder.

## Check before you answer

Understand the whole thing before saying anything. Assume nothing. Almost
every answer is already somewhere in the project — read the code, run the
checkers, read the scripts themselves, check git history. Look it up instead
of guessing.

**Say "I'm not sure" only when the information genuinely isn't anywhere.**
Doubt is a last resort, not a shortcut past the checking. And when it is
genuine, say plainly what is unknown and what was already tried.

**A tool's output is a lead, not a fact.** Confirm it against the source
before repeating it or acting on it. Three real failures of this kind, worth
keeping as the shape to watch for:

- A checker script was run from the command line to capture a baseline. It
  had no command-line entry point, so it printed nothing and reported
  success — 18 empty files were written and the mistake only surfaced when a
  later comparison crashed. *Check that a command actually produced output.*
- A count of "7 skipped checks" was repeated from an audit report. Reading
  the file showed 8, and that the damage was wider than the audit could see.
  *Read the file before quoting a number.*
- A test was flagged as broken by a checker. Counting by hand showed the test
  was right and the checker was wrong; the checker got fixed instead of the
  test. *When a tool and the code disagree, find out which one is wrong.*

This does not override the reformulation rule above. The boundary:

- **Before the user confirms** — look only as far as needed to describe the
  job accurately.
- **After the user confirms** — verify everything, and don't guess.

## How to answer

Write for someone who knows nothing about the subject. These rules are about
answers in the chat, not about code comments or the documents under
`.claude/`, which stay precise.

- **Simple words.** Skip a technical term whenever a plain one works. If a
  technical term is unavoidable, say in a few words what it means.
- **Big picture first.** A short overview of what happened and what it means
  beats a long, detailed description. Add detail only where it changes what
  the user would decide or do.
- **One name per thing.** Pick a name and keep it for the whole conversation.
  Never switch between two words for the same thing (e.g. don't alternate
  between "the checker", "the audit" and "the script" — choose one).
- **Problems: the first sentence is the whole problem.** If something is
  wrong, the opening sentence alone must be enough to understand it. Put the
  cause, the consequence and the fix after that, shortest first.
- **Say what it means, not just what was done.** "This test can never pass"
  beats "the declared count differs from the reachable count".

## Token usage visibility
Exact token/cost usage is shown in the status line (see
`.claude/hooks/statusline.sh`) and via the built-in `/cost` command — not
something for Claude to compute or report in its answers, since it has no
reliable access to the exact running total.
