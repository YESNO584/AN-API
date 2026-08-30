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
