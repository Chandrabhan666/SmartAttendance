#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PGDATA_DIR="$ROOT_DIR/.postgres/data"
PGLOG_FILE="$ROOT_DIR/.postgres/postgres.log"
PGPORT="${POSTGRES_PORT:-5433}"

if [ ! -d "$PGDATA_DIR" ]; then
  echo "PostgreSQL data directory not found at $PGDATA_DIR"
  echo "Run init first:"
  echo "  /opt/homebrew/bin/initdb -D \"$PGDATA_DIR\" --auth=trust --username=helpdesk_admin"
  exit 1
fi

/opt/homebrew/bin/pg_ctl -D "$PGDATA_DIR" -l "$PGLOG_FILE" -o "-p $PGPORT" start
echo "PostgreSQL started on port $PGPORT"
