#!/bin/bash
# Auto-format Python code with all configured tools

set -e  # Exit on error

# Get the project root directory (parent of scripts/)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Use venv python
PYTHON=".venv/bin/python"

echo "✨ Formatting code..."
echo

# Run isort for import sorting
echo "→ isort (sorting imports)"
$PYTHON -m isort src/ *.py

echo
echo "→ Ruff (auto-fix)"
$PYTHON -m ruff check --fix src/ *.py

echo
echo "→ Black (formatting)"
$PYTHON -m black src/ *.py

echo
echo "✅ Formatting complete!"
