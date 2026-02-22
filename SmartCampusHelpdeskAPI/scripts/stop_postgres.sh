#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PGDATA_DIR="$ROOT_DIR/.postgres/data"

/opt/homebrew/bin/pg_ctl -D "$PGDATA_DIR" stop
echo "PostgreSQL stopped"
