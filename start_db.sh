#!/usr/bin/env bash
set -euo pipefail

# Resolve script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/database/docker-compose.yml"
SQLITE_FILE="$SCRIPT_DIR/db.sqlite"

# Display help
usage() {
    cat <<EOF
Usage: $(basename "$0") <database>
       $(basename "$0") [OPTION]

Start a database container or initialize a SQLite database.

Databases:
  oracle       Start Oracle Database
  mysql        Start MySQL
  postgres     Start PostgreSQL
  mssql        Start Microsoft SQL Server
  sqlite       Create db.sqlite using VACUUM if it doesn't exist
  all          Start all database containers and initialize SQLite

Options:
  -h, --help   Display this help message and exit

Examples:
  $(basename "$0") postgres
  $(basename "$0") sqlite
  $(basename "$0") all
EOF
}

# Handle help and validate arguments
if [[ $# -eq 1 && ( "$1" == "-h" || "$1" == "--help" ) ]]; then
    usage
    exit 0
fi

if [[ $# -ne 1 ]]; then
    echo "Error: Expected exactly one database argument." >&2
    usage >&2
    exit 1
fi

DB="${1,,}"

# Start Docker database
start_container() {
    local db="$1"

    if [[ ! -f "$COMPOSE_FILE" ]]; then
        echo "Error: Docker Compose file not found: $COMPOSE_FILE" >&2
        exit 1
    fi

    echo "Starting $db..."
    docker compose -f "$COMPOSE_FILE" up -d "$db"
    echo "$db started."
}

# Initialize SQLite database
start_sqlite() {
    command -v sqlite3 >/dev/null 2>&1 || {
        echo "Error: sqlite3 is not installed." >&2
        exit 1
    }

    if [[ -f "$SQLITE_FILE" ]]; then
        echo "SQLite database already exists: $SQLITE_FILE"
    else
        sqlite3 "$SQLITE_FILE" "VACUUM;"
        echo "SQLite database created: $SQLITE_FILE"
    fi
}

# Select database
case "$DB" in
    oracle|mysql|postgres|mssql)
        start_container "$DB"
        ;;

    sqlite)
        start_sqlite
        ;;

    all)
        for db in oracle mysql postgres mssql; do
            start_container "$db"
        done
        start_sqlite
        ;;

    *)
        echo "Error: Unknown database '$DB'" >&2
        usage >&2
        exit 1
        ;;
esac
