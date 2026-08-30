#!/bin/bash
# statusLine command — supports Rule 4: visibility into token/cost usage.
#
# IMPORTANT CAVEAT: Claude Code does not expose an exact cumulative
# token-usage figure to hooks or to the model itself, so this script shows
# whatever the statusline JSON payload provides (model, cwd, git branch, and
# cost/context fields on Claude Code versions that include them). For precise
# numbers, run `/cost` inside the session, or wire in a dedicated tool such as
# ccusage, which parses the session transcript directly for exact token/cost
# totals: https://ccusage.com/guide/statusline

INPUT=$(cat)

MODEL=$(echo "$INPUT" | jq -r '.model.display_name // "unknown-model"')
CWD=$(echo "$INPUT" | jq -r '.cwd // "."')
PROJECT=$(basename "$CWD")

BRANCH=""
if git -C "$CWD" rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  BRANCH=$(git -C "$CWD" branch --show-current 2>/dev/null)
fi

# These fields are only present on Claude Code versions that expose them;
# fall back gracefully if absent.
CONTEXT_PCT=$(echo "$INPUT" | jq -r '.context.used_percent // empty')
COST=$(echo "$INPUT" | jq -r '.cost.total_usd // empty')

LINE="[$MODEL] $PROJECT"
[[ -n "$BRANCH" ]] && LINE="$LINE (git:$BRANCH)"
[[ -n "$CONTEXT_PCT" ]] && LINE="$LINE | ctx:${CONTEXT_PCT}%"
[[ -n "$COST" ]] && LINE="$LINE | \$${COST}"
[[ -z "$CONTEXT_PCT$COST" ]] && LINE="$LINE | run /cost for exact usage"

echo "$LINE"
