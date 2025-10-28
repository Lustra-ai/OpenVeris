#!/bin/bash
# Lint Python code with all configured tools

set -e  # Exit on error

# Get the project root directory (parent of scripts/)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Use venv python
PYTHON=".venv/bin/python"

echo "🔍 Running linters..."
echo

# Run Ruff linter
echo "→ Ruff (linting)"
$PYTHON -m ruff check src/ *.py

echo
echo "→ Ruff (import sorting)"
$PYTHON -m ruff check --select I src/ *.py

echo
echo "→ Black (format check)"
$PYTHON -m black --check src/ *.py

echo
echo "→ mypy (type checking)"
$PYTHON -m mypy src/ *.py || true  # Don't fail on mypy errors initially

echo
echo "✅ Linting complete!"
