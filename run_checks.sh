#!/usr/bin/env bash
set -euo pipefail
set -x

pycodestyle ./src ./tests
pytest
ruff check .
pyright
