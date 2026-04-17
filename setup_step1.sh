#!/usr/bin/env bash
set -euo pipefail

if ! command -v mysql >/dev/null 2>&1; then
  echo "Error: mysql client not found in PATH."
  echo "Install MySQL client first, then rerun this script."
  exit 1
fi

if [[ $# -lt 2 ]]; then
  echo "Usage: bash RentalApp/setup_step1.sh <mysql_user> <mysql_password> [mysql_host]"
  exit 1
fi

MYSQL_USER="$1"
MYSQL_PASSWORD="$2"
MYSQL_HOST="${3:-localhost}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCHEMA_SQL="$ROOT_DIR/RentalApp/sql/maskinutleie_schema_flask.sql"

mysql -h "$MYSQL_HOST" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" < "$SCHEMA_SQL"

echo "Database setup completed."
