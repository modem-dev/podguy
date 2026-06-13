#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Discover smoke tests instead of maintaining a registry; a new
# tests/test_*.sh file is automatically picked up.
for smoke_test in tests/test_*.sh; do
  echo "==> $smoke_test"
  bash "$smoke_test"
done
