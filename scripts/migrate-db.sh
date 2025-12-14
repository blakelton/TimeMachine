#!/bin/bash
#
# TimeMachine Database Migration Script
# Runs Alembic migrations for the database
#
set -e

# Detect installation context
if [ -d "/opt/timemachine/backend" ]; then
    # Production/installed environment
    BACKEND_DIR="/opt/timemachine/backend"
    VENV_DIR="/opt/timemachine/venv"
    ENV_FILE="/etc/timemachine/timemachine.env"
else
    # Development environment
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    BACKEND_DIR="$(dirname "$SCRIPT_DIR")/backend"
    VENV_DIR="$BACKEND_DIR/.venv"
    ENV_FILE="$BACKEND_DIR/.env"
fi

# Check if backend directory exists
if [ ! -d "$BACKEND_DIR" ]; then
    echo "❌ Error: Backend directory not found at $BACKEND_DIR"
    exit 1
fi

# Check if venv exists
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Error: Virtual environment not found at $VENV_DIR"
    exit 1
fi

# Load environment if exists
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

cd "$BACKEND_DIR"

# Activate virtual environment
PYTHON="$VENV_DIR/bin/python"
ALEMBIC="$VENV_DIR/bin/alembic"

# Check if alembic is installed
if [ ! -f "$ALEMBIC" ]; then
    echo "📦 Installing alembic..."
    "$VENV_DIR/bin/pip" install alembic
fi

# Command handling
case "${1:-upgrade}" in
    upgrade)
        echo "🔄 Running database migrations..."
        "$ALEMBIC" upgrade head
        echo "✓ Migrations complete"
        ;;
    stamp)
        # Stamp database with current revision without running migrations
        # Useful for existing databases created with create_all()
        REVISION="${2:-head}"
        echo "🔖 Stamping database with revision: $REVISION"
        "$ALEMBIC" stamp "$REVISION"
        echo "✓ Database stamped"
        ;;
    current)
        echo "📍 Current database revision:"
        "$ALEMBIC" current
        ;;
    history)
        echo "📜 Migration history:"
        "$ALEMBIC" history
        ;;
    generate)
        # Generate a new migration based on model changes
        MESSAGE="${2:-auto_generated}"
        echo "📝 Generating new migration: $MESSAGE"
        "$ALEMBIC" revision --autogenerate -m "$MESSAGE"
        echo "✓ Migration generated - review before applying!"
        ;;
    *)
        echo "Usage: $0 {upgrade|stamp [revision]|current|history|generate [message]}"
        echo ""
        echo "Commands:"
        echo "  upgrade         - Apply all pending migrations (default)"
        echo "  stamp [rev]     - Stamp database with revision without running migrations"
        echo "  current         - Show current database revision"
        echo "  history         - Show migration history"
        echo "  generate [msg]  - Generate new migration from model changes"
        exit 1
        ;;
esac
