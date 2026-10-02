#!/bin/bash
# Double-click launcher for the Frontier TradeLight website (FastAPI API +
# Vite site). Opens Terminal automatically when double-clicked from Finder.
# Sets up anything missing on first run, applies database migrations,
# starts both servers, opens the site in your browser, and stops both
# servers together when this window is closed or Ctrl+C is pressed.

set -e

# Resolve this script's own directory, following symlinks, so it works
# regardless of where it's double-clicked from or copied to.
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
cd "$SCRIPT_DIR"

API_PORT=8100
WEB_PORT=5180
VENV="api/.venv"
VENV_PYTHON="$VENV/bin/python"

echo "Frontier TradeLight website"
echo "==========================="
echo "Working directory: $SCRIPT_DIR"
echo

fail() {
  echo "Error: $1"
  read -n 1 -s -r -p "Press any key to close..."
  exit 1
}

for port in "$API_PORT" "$WEB_PORT"; do
  if lsof -ti tcp:"$port" >/dev/null 2>&1; then
    fail "port $port is already in use (is the website already running in another window?)"
  fi
done

# --- First-run setup: Python environment ---------------------------------
if [ ! -x "$VENV_PYTHON" ]; then
  PY=$(command -v python3.12 || command -v python3.13 || true)
  [ -z "$PY" ] && fail "Python 3.12+ not found. Install it (e.g. brew install python@3.12) and try again."
  echo "Creating Python environment with $PY..."
  "$PY" -m venv "$VENV"
fi

# Re-install whenever requirements change, so a new dependency never shows
# up as a ModuleNotFoundError at runtime.
REQS_STAMP="$VENV/.requirements.installed"
if [ ! -f "$REQS_STAMP" ] || ! cat api/requirements.txt api/requirements-dev.txt | cmp -s - "$REQS_STAMP"; then
  echo "Installing API dependencies..."
  "$VENV_PYTHON" -m pip install -q -r api/requirements-dev.txt
  cat api/requirements.txt api/requirements-dev.txt > "$REQS_STAMP"
fi

# --- First-run setup: secrets ---------------------------------------------
if [ ! -f api/.env ]; then
  echo "Creating api/.env with freshly generated local secrets..."
  KEY=$("$VENV_PYTHON" -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
  SYNC=$("$VENV_PYTHON" -c "import secrets; print(secrets.token_urlsafe(48))")
  sed -e "s#^DATA_ENCRYPTION_KEY=.*#DATA_ENCRYPTION_KEY=$KEY#" \
      -e "s#^SYNC_SECRET=.*#SYNC_SECRET=$SYNC#" api/.env.example > api/.env
fi

# --- Database (safe to run every time) -----------------------------------
echo "Applying database migrations..."
(cd api && .venv/bin/alembic upgrade head)

ACCOUNTS=$(cd api && .venv/bin/python -c "
from sqlalchemy import func, select
from app.db import SessionLocal
from app.models import User
with SessionLocal() as db: print(db.scalar(select(func.count()).select_from(User)))")

# --- First-run setup: website packages -----------------------------------
if [ ! -d "web/node_modules" ]; then
  command -v npm >/dev/null || fail "npm not found. Install Node 18+ and try again."
  echo "web/node_modules not found - running npm install..."
  (cd web && npm install)
fi

API_PID=""
WEB_PID=""

cleanup() {
  echo
  echo "Shutting down..."
  [ -n "$API_PID" ] && kill "$API_PID" 2>/dev/null
  [ -n "$WEB_PID" ] && kill "$WEB_PID" 2>/dev/null
  wait 2>/dev/null
  echo "Stopped. You can close this window."
}
trap cleanup EXIT INT TERM

echo "Starting API on port $API_PORT..."
(cd api && exec .venv/bin/uvicorn app.main:app --port "$API_PORT" --reload --reload-dir app) &
API_PID=$!

echo "Starting website on port $WEB_PORT..."
# exec so $! is vite itself, not an npm wrapper that would orphan it.
(cd web && exec node_modules/.bin/vite --port "$WEB_PORT") &
WEB_PID=$!

echo "Waiting for the website to come up..."
for _ in $(seq 1 60); do
  if curl -s -o /dev/null "http://localhost:$WEB_PORT" && curl -s -o /dev/null "http://localhost:$API_PORT/api/health"; then
    break
  fi
  sleep 1
done

open "http://localhost:$WEB_PORT" 2>/dev/null

echo
echo "Website:  http://localhost:$WEB_PORT"
echo "Login:    http://localhost:$WEB_PORT/login"
echo "API docs: http://localhost:$API_PORT/api/docs"
echo
if [ "$ACCOUNTS" = "0" ]; then
  echo "No accounts exist yet. Create your admin account in another terminal:"
  echo "  cd \"$SCRIPT_DIR/api\" && .venv/bin/python -m app.cli create-admin you@example.com"
  echo "(or load FAKE demo data: .venv/bin/python -m app.cli seed)"
  echo
fi
echo "Sync fresh numbers from FrontierTradeLight (in another terminal):"
echo "  cd \"$SCRIPT_DIR/sync\" && python3 export_snapshot.py --push"
echo
echo "Close this window or press Ctrl+C to stop both servers."

wait
