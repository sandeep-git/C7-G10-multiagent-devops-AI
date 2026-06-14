#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "=== DevOps Incident Analysis Suite — Setup ==="

# 1. Python virtualenv
if [ ! -d "$ROOT/.venv" ]; then
  echo "[1/5] Creating Python venv..."
  python3 -m venv "$ROOT/.venv"
fi
source "$ROOT/.venv/bin/activate"

echo "[2/5] Installing Python dependencies..."
pip install -q -r "$ROOT/requirements.txt"

# 2. .env
if [ ! -f "$ROOT/.env" ]; then
  echo "[3/5] Creating .env from .env.example..."
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "  ⚠️  Edit .env and add your ANTHROPIC_API_KEY before starting."
else
  echo "[3/5] .env already exists, skipping."
fi

# 3. Seed vector store
echo "[4/5] Seeding vector store..."
cd "$ROOT" && python seed_vectorstore.py

# 4. Frontend
echo "[5/5] Installing frontend dependencies..."
cd "$ROOT/frontend" && npm install --legacy-peer-deps

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the backend:"
echo "  source .venv/bin/activate && uvicorn backend.api:app --reload --port 8000"
echo ""
echo "To start the frontend (separate terminal):"
echo "  cd frontend && npm run dev"
echo ""
echo "Then open: http://localhost:3000"
