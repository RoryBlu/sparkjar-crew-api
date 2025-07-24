#!/bin/bash
# Run tests using crew-api's dedicated virtual environment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"

if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo "❌ Virtual environment not found. Please run ./setup_venv.sh first"
    exit 1
fi

source "$SCRIPT_DIR/.venv/bin/activate"

if [ -f "$REPO_ROOT/.env" ]; then
    set -a
    source "$REPO_ROOT/.env"
    set +a
fi

export PYTHONPATH="$REPO_ROOT:$REPO_ROOT/services/crew-api:$REPO_ROOT/services/crew-api/src:$PYTHONPATH"

cd "$REPO_ROOT"
echo "🧪 Running crew-api tests..."
python -m pytest tests/ -v "$@"
