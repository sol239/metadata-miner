
#!/usr/bin/env bash
set -euo pipefail

# Resolve script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
SQLITE_FILE="$SCRIPT_DIR/db.sqlite"

# Display usage
usage() {
    echo "Usage: $0 <database>"
    echo "Available: oracle, mysql, postgres, mssql, sqlite, all"
    exit 1
}

# Validate arguments
[[ $# -eq 1 ]] || usage

DB="${1,,}"

# Start Docker database
start_container() {
    local db="$1"

    echo "Starting $db..."
    docker compose -f "$COMPOSE_FILE" up -d "$db"
    echo "$db started."
}

# Initialize SQLite database
start_sqlite() {
    command -v sqlite3 >/dev/null 2>&1 || {
        echo "Error: sqlite3 is not installed."
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
        echo "Error: Unknown database '$DB'"
        usage
        ;;
esac
s