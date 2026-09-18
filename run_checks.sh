#!/usr/bin/env bash
set -euo pipefail

pycodestyle ./src ./tests
pytest
ruff check .
pyright
