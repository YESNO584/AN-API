# Session learnings

Append-only log of things learned while working on this project that aren't
derivable from the code, and that would otherwise be rediscovered at cost.
Loaded every session via the root `CLAUDE.md`.

## How to use this file

- **Newest entries at the top**, under a dated `##` heading.
- One bullet per lesson. State the fact, then *why it matters*. Name the file,
  class or flag so it can be verified later.
- If a lesson belongs to one subsystem, put it in that subsystem's own
  `CLAUDE.md` instead and only cross-reference here. This file is for
  cross-cutting or process lessons.
- If a lesson turns out to be wrong, **delete or correct it** — a stale
  learning is worse than none.
- Durable facts about *the user's* preferences go in the auto-memory, not
  here.

---

## Permission rules cannot contain a literal `*`

Carried over from a previous project; true of Claude Code itself, not of any
one codebase.

- **In a `Bash(...)` allow rule, `*` always means "anything from here on" —
  there is no escape.** So a rule recording a command that genuinely contains
  an asterisk (`--include="*.cs"`, or a regex piece like `\s*` or `.*`) does
  not approve that one command: it approves everything matching up to the
  asterisk, including extra options slipped in at that spot, with no prompt.
- **A rule like this can only be deleted, never fixed.** The safe form is a
  wildcard at the very end (`Bash(/usr/bin/grep *)`), which usually already
  covers the command that was being approved, so nothing is lost by deleting
  the over-broad one.
- **`Read(...)` rules are different.** `Read(/tmp/**)` and friends are
  ordinary path globs and are fine; don't sweep them up in the same pass.
- Cheapest way to find these: for each `Bash(...)` rule, check whether the
  first `*` in the body is the last character. If not, the rule is broader
  than it looks.

Worth re-running that check on `.claude/settings.local.json` every few weeks —
these accumulate one one-off search at a time.
