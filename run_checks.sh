#!/usr/bin/env bash
set -euo pipefail
set -x

pycodestyle ./src ./tests
pytest
ruff check .
pyright
codespell . --skip site

python scripts/sync_front_page_example.py --check
python examples/front_page.py > /dev/null
python examples/simple_simulation.py > /dev/null
python examples/monte_carlo_simulation.py > /dev/null
