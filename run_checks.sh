#!/usr/bin/env bash
set -euo pipefail
set -x

pycodestyle ./src ./tests
pytest
ruff check .
python -m pyright --pythonpath "$(command -v python)"
codespell .

python examples/simple_simulation.py
python examples/monte_carlo_simulation.py
