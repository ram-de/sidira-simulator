#!/usr/bin/env bash
# PostToolUse hook: compresses verbose Bash output before Claude reads it.
# Keeps first 15 lines, all error/warn/fail/pass lines (up to 50), last 5 lines.
# Passes output through unchanged if under THRESHOLD lines.

set -euo pipefail

THRESHOLD=150
MAX_NOTABLE=50

input=$(cat)

# Extract stdout output from tool response JSON
output=$(python3 - "$input" <<'PYEOF'
import sys, json
try:
    data = json.loads(sys.argv[1])
    # Claude Code PostToolUse schema: tool_response.output or output
    out = (data.get("tool_response") or {}).get("output") \
       or data.get("output") \
       or ""
    print(out, end="")
except Exception:
    pass
PYEOF
)

line_count=$(printf '%s\n' "$output" | wc -l | tr -d ' ')

if [ "$line_count" -le "$THRESHOLD" ]; then
    exit 0  # short output — pass through, don't modify
fi

# Build compressed output
head_lines=$(printf '%s\n' "$output" | head -15)
tail_lines=$(printf '%s\n' "$output" | tail -5)
notable=$(printf '%s\n' "$output" \
    | grep -iE '(error|Error|ERROR|fail|Fail|FAIL|warn|Warn|WARNING|PASS|pass|✓|✗|exception|traceback|assert|TypeError|SyntaxError|ImportError)' \
    | head -"$MAX_NOTABLE" || true)

notable_count=$(printf '%s\n' "$notable" | grep -c . || true)

compressed="[hook: output compressed — ${line_count} lines → summary below]

--- first 15 lines ---
${head_lines}

--- notable lines (errors/warnings/results: ${notable_count}) ---
${notable}

--- last 5 lines ---
${tail_lines}"

# Output replacement JSON — Claude Code replaces tool_response.output with this
python3 - "$input" "$compressed" <<'PYEOF'
import sys, json
try:
    data = json.loads(sys.argv[1])
    compressed = sys.argv[2]
    if "tool_response" in data:
        data["tool_response"]["output"] = compressed
    else:
        data["output"] = compressed
    print(json.dumps(data))
except Exception:
    # fallback: just print the compressed text so Claude sees it
    print(sys.argv[2])
PYEOF
