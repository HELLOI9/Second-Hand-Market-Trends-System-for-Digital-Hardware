#!/usr/bin/env bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()    { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }

need_install() { ! command -v "$1" &>/dev/null; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

info "========================================"
info " Local Dev Environment Setup"
info "========================================"

# ── 1. PostgreSQL ─────────────────────────────────────────────

if need_install psql; then
    info "[1/5] Installing PostgreSQL 16..."
    sudo apt-get update -q
    sudo apt-get install -y -q postgresql postgresql-contrib
    success "PostgreSQL installed: $(psql --version)"
else
    success "[1/5] PostgreSQL already installed: $(psql --version)"
fi

# Ensure the service is running
sudo systemctl start postgresql
sudo systemctl enable postgresql --quiet

# Create DB role and database (idempotent)
info "Setting up database user and schema..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='market'" \
    | grep -q 1 \
    || sudo -u postgres psql -c "CREATE USER market WITH PASSWORD 'market_pass';"

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='market'" \
    | grep -q 1 \
    || sudo -u postgres psql -c "CREATE DATABASE market OWNER market;"

success "Database 'market' ready"

# ── 2. Python dependencies + Playwright ──────────────────────

info "[2/5] Installing Python dependencies into current Python environment..."
cd "$SCRIPT_DIR/backend"

# Requires: conda activate <env> before running this script
if [ -z "$CONDA_DEFAULT_ENV" ] && [ -z "$VIRTUAL_ENV" ]; then
    warn "No conda/virtualenv environment detected."
    warn "It is recommended to run: conda activate <your-env> first."
fi

pip install -e .

info "Downloading Playwright Firefox browser..."
playwright install firefox
playwright install-deps firefox

success "Python dependencies and Playwright ready"
cd "$SCRIPT_DIR"

# ── 4. pnpm ───────────────────────────────────────────────────

if need_install pnpm; then
    info "[4/5] Installing pnpm..."
    curl -fsSL https://get.pnpm.io/install.sh | sh -
    export PNPM_HOME="$HOME/.local/share/pnpm"
    export PATH="$PNPM_HOME:$PATH"
    success "pnpm installed: $(pnpm --version)"
else
    success "[4/5] pnpm already installed: $(pnpm --version)"
fi

# ── 5. Frontend dependencies ──────────────────────────────────

info "[5/5] Installing frontend dependencies..."
cd "$SCRIPT_DIR/frontend"
pnpm install
success "Frontend dependencies installed"
cd "$SCRIPT_DIR"

# ── 6. Database migrations ────────────────────────────────────

info "Running database migrations..."
cd "$SCRIPT_DIR/backend"
alembic upgrade head
success "Migrations complete"
cd "$SCRIPT_DIR"

# ── Done ──────────────────────────────────────────────────────

echo ""
info "========================================"
info " Setup complete!"
info "========================================"
echo ""
echo "To start the backend:"
echo "  conda activate Xianyu   # or your env name"
echo "  cd backend"
echo "  uvicorn app.main:app --reload"
echo ""
echo "To start the frontend (separate terminal):"
echo "  cd frontend"
echo "  pnpm dev"
echo ""
echo "  API docs : http://localhost:8000/docs"
echo "  Frontend : http://localhost:5173"
echo ""
