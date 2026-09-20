#!/bin/bash
# PreToolUse hook — backstop enforcement of Rule 1:
# "Never edit anything outside of this folder, or nested folders."
#
# The permissions.deny patterns in settings.json already block this at the
# path-pattern level. This hook adds a second, resolved-path check so that
# symlinks, `..` traversal, or unusual path forms can't slip through.
#
# Exit code 2 blocks the tool call and feeds the message back to Claude.

INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# A Bash call has no file_path, so the check below never saw it: `echo … >
# /elsewhere` wrote outside the project unnoticed. Measured 2026-09-20, two
# sessions did exactly that after Write was blocked. So look at the command
# too, and refuse the writing forms whose target leaves the project.
#
# This is a tripwire, not a wall: a shell command can always write in a way a
# pattern does not recognise. It makes the accident impossible and the
# deliberate bypass visible — that is what it is for.
if [[ -n "$COMMAND" ]]; then
  # Strip here-document bodies first. The text a command carries is not a
  # command: measured 2026-09-20, the very commit message describing this hook
  # was blocked by it, because it quoted a redirection as an example. A false
  # alarm is what teaches people to work around a guard, so it has to go.
  COMMAND=$(printf '%s\n' "$COMMAND" | awk '
    !dans && match($0, /<<-?[[:space:]]*'"'"'?"?[A-Za-z_][A-Za-z0-9_]*/) {
      fin = substr($0, RSTART, RLENGTH)
      sub(/^<<-?[[:space:]]*'"'"'?"?/, "", fin)
      dans = 1; print; next
    }
    dans { if ($0 ~ "^[[:space:]]*" fin "[[:space:]]*$") dans = 0; next }
    { print }')

  # Absolute paths that are the target of a redirection, tee, cp or mv.
  CIBLES=$(printf '%s\n' "$COMMAND" \
    | grep -oE '(>>?[[:space:]]*|tee[[:space:]]+(-a[[:space:]]+)?|cp[[:space:]]+[^|;]*[[:space:]]|mv[[:space:]]+[^|;]*[[:space:]])/[^[:space:];|&)"'"'"']+' \
    | grep -oE '/[^[:space:];|&)"'"'"']+' || true)
  PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
  while IFS= read -r cible; do
    [[ -z "$cible" ]] && continue
    # /dev/null and friends are not the project's business.
    [[ "$cible" == /dev/* || "$cible" == /proc/* ]] && continue
    if [[ "$cible" != "$PROJECT_DIR"/* ]]; then
      echo "Blocked: this command writes to '$cible', outside the project ($PROJECT_DIR). Working files go in $PROJECT_DIR/tmp/, which git ignores." >&2
      exit 2
    fi
  done <<< "$CIBLES"
fi

if [[ -z "$FILE" ]]; then
  # No file_path on this tool call — nothing to check, allow it.
  exit 0
fi

# Resolve symlinks / relative segments to an absolute real path.
# realpath has no portable -m equivalent across BSD (macOS), GNU (Linux),
# and MSYS/Git-Bash (Windows) realpath, and it requires the path to exist,
# so for not-yet-created files (e.g. a new Write target) resolve the
# parent directory and reattach the filename instead.
resolve_path() {
  if [[ -e "$1" ]]; then
    realpath "$1" 2>/dev/null
  else
    local dir base
    dir=$(dirname "$1")
    base=$(basename "$1")
    [[ -d "$dir" ]] && printf '%s/%s\n' "$(cd "$dir" && pwd)" "$base"
  fi
}

REAL=$(resolve_path "$FILE")
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
PROJECT_REAL=$(resolve_path "$PROJECT_DIR")

if [[ -z "$REAL" || -z "$PROJECT_REAL" || "$REAL" != "$PROJECT_REAL"/* ]]; then
  echo "Blocked: '$FILE' resolves outside the project folder ($PROJECT_REAL). Edits are restricted to this folder and its subfolders." >&2
  exit 2
fi

exit 0
