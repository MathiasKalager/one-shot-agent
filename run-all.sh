#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-$ROOT_DIR/.venv/bin/python}"

if [[ ! -x "$PYTHON" ]]; then
    echo "Python interpreter is not executable: $PYTHON" >&2
    echo "Create .venv and install the project with: pip install -e ." >&2
    exit 1
fi

cd "$ROOT_DIR"

"$PYTHON" -m mcp_app.server &
MCP_PID=$!

cleanup() {
    if kill -0 "$MCP_PID" 2>/dev/null; then
        kill "$MCP_PID" 2>/dev/null || true
    fi
    wait "$MCP_PID" 2>/dev/null || true
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

sleep "${MCP_STARTUP_DELAY:-5}"  # Wait for the MCP server to start
if ! kill -0 "$MCP_PID" 2>/dev/null; then
    wait "$MCP_PID" || true
    echo "MCP server exited before the agent started." >&2
    exit 1
fi

"$PYTHON" -m agent.agent