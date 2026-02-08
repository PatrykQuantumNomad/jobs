#!/usr/bin/env bash
# Claude Code PostToolUse hook: Optimized Python linting (uv)
# Place in: .claude/hooks/python-lint.sh

set -uo pipefail

# Fast exit: parse file path and check extension in one shot
FILE_PATH=$(jq -r '.tool_input.file_path // empty')
[[ -z "$FILE_PATH" || "$FILE_PATH" != *.py ]] && exit 0

# Resolve relative paths
[[ "$FILE_PATH" != /* ]] && FILE_PATH="${CLAUDE_PROJECT_DIR:-.}/$FILE_PATH"

# Skip deleted files
[[ ! -f "$FILE_PATH" ]] && exit 0

# Work from project root so uv resolves pyproject.toml once
cd "${CLAUDE_PROJECT_DIR:-.}"

ERRORS=""

# --- Phase 1: Ruff format + check in a single uv invocation ---
# One `uv run` pays the resolver cost once instead of twice.
# Format runs first (quiet), then check runs on the formatted output.
RUFF_OUTPUT=$(uv run -- sh -c '
    ruff format --quiet "$1" 2>&1
    ruff check --fix --output-format=concise "$1" 2>&1
' _ "$FILE_PATH" 2>&1)
RUFF_RC=${PIPESTATUS[0]:-$?}

if [[ $RUFF_RC -ne 0 && -n "$RUFF_OUTPUT" ]]; then
    ERRORS+="$RUFF_OUTPUT"$'\n'
fi

# --- Phase 2: Pyright with structured JSON output ---
# --outputjson gives machine-readable diagnostics we can condense
# into file:line: severity - message format for Claude.
PYRIGHT_OUTPUT=$(uv run pyright --outputjson "$FILE_PATH" 2>&1)
PYRIGHT_RC=$?

if [[ $PYRIGHT_RC -ne 0 ]]; then
    SUMMARY=$(printf '%s' "$PYRIGHT_OUTPUT" | jq -r '
        .generalDiagnostics[]? |
        "\(.file | split("/") | last):\(.range.start.line + 1): \(.severity) - \(.message)"
    ' 2>/dev/null)

    if [[ -n "$SUMMARY" ]]; then
        ERRORS+="[pyright]"$'\n'"$SUMMARY"$'\n'
    else
        # Fallback: strip ANSI codes from raw output for readability
        ERRORS+="[pyright] $(printf '%s' "$PYRIGHT_OUTPUT" | sed 's/\x1b\[[0-9;]*m//g')"$'\n'
    fi
fi

# Exit 2 feeds errors back to Claude as actionable context
if [[ -n "$ERRORS" ]]; then
    printf '%s' "$ERRORS" >&2
    exit 2
fi
