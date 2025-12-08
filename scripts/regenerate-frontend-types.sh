#!/bin/bash
#
# Regenerate Frontend TypeScript Types from Backend OpenAPI Schema
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🔄 Regenerating Frontend TypeScript Types"
echo ""

# Check if backend is running
if ! curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
  echo "❌ Backend is not running at http://localhost:8000"
  echo "   Please start the backend first:"
  echo "   cd $PROJECT_ROOT/backend && uvicorn app.main:app --host 0.0.0.0 --port 8000"
  exit 1
fi

echo "✓ Backend is running"
echo ""

cd "$PROJECT_ROOT/frontend"

echo "📥 Fetching OpenAPI schema from backend..."
npm run generate-types

echo ""
echo "✓ TypeScript types regenerated successfully!"
echo "  File: $PROJECT_ROOT/frontend/src/types/api.ts"
