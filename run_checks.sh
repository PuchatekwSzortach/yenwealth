#!/usr/bin/env bash
set -euo pipefail

pytest
ruff check .
pyright
