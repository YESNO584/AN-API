#!/bin/bash
# UserPromptSubmit hook — reinforces Rule 3 on every single prompt:
# "Reformulate every prompt to make it optimal for Claude Code, and ask for
#  confirmation. Only start responding after reformulation is confirmed."
#
# This cannot force Claude to literally stop and wait for your reply — that
# relies on the instruction in CLAUDE.md being followed. What this hook
# guarantees is that the reminder is freshly injected on every message, so
# it survives context compaction and can't quietly get "forgotten."
#
# NOTE: plain stdout (exit 0) is used instead of the JSON
# `hookSpecificOutput.additionalContext` form — the JSON form has a known
# display bug on the first UserPromptSubmit of a new session in some Claude
# Code versions. Plain text is injected as context the same way and is
# more robust.

cat <<'EOF'
Reminder (standing rule): before doing anything else, restate this request in
a clear, optimized form for Claude Code — explicit scope (files/modules),
expected output, and constraints. Ask "Is this correct?" and stop there. Do
not read (beyond what's needed to reformulate), edit, or run anything until
the user explicitly confirms the reformulation.

If a reusable agent would help with this kind of task in the future, create
one or update exiting one in `.claude/agents/`. Prefer a generic agent over a project-specific one;
only narrow its scope to this project if a generic version can't do the job.
Skip this step if no future task would plausibly reuse such an agent.
EOF
exit 0
