#!/usr/bin/env bash
# 开发环境一键自举脚本（Linux / macOS）
# 作用：检测必备工具、装后端/前端依赖、拉 Playwright Firefox、跑数据库迁移
# 不会自动安装 PostgreSQL、Python、Node —— 这些请按下方提示自行安装
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

bold()  { printf '\033[1m%s\033[0m\n' "$*"; }
warn()  { printf '\033[33m[WARN]\033[0m %s\n' "$*"; }
ok()    { printf '\033[32m[ OK ]\033[0m %s\n' "$*"; }
info()  { printf '\033[36m[INFO]\033[0m %s\n' "$*"; }
fail()  { printf '\033[31m[FAIL]\033[0m %s\n' "$*" >&2; exit 1; }

OS="$(uname -s)"
case "$OS" in
    Linux*)  PLATFORM="linux" ;;
    Darwin*) PLATFORM="macos" ;;
    *)       PLATFORM="unknown" ;;
esac

# ── 1. 工具检查 ──────────────────────────────────
bold "==> [1/6] 检查基础工具"

require_cmd() {
    local cmd="$1" hint="$2"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        fail "未检测到 $cmd。请先安装：$hint"
    fi
    ok "$cmd: $(command -v "$cmd")"
}

require_cmd python3 "https://www.python.org/downloads/  (>=3.12)"
PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
case "$PY_VER" in
    3.1[2-9]|3.[2-9][0-9]) ok "Python $PY_VER" ;;
    *) fail "Python 版本过低（$PY_VER），需要 3.12+" ;;
esac

require_cmd node "https://nodejs.org/  (>=20)"
NODE_VER="$(node -v | sed 's/^v//')"
NODE_MAJOR="${NODE_VER%%.*}"
[ "$NODE_MAJOR" -ge 20 ] || fail "Node 版本过低（$NODE_VER），需要 20+"
ok "Node $NODE_VER"

if ! command -v pnpm >/dev/null 2>&1; then
    info "未检测到 pnpm，尝试用 npm 安装..."
    npm install -g pnpm
fi
require_cmd pnpm "https://pnpm.io/installation"

# ── 2. PostgreSQL 检查 ────────────────────────────
bold "==> [2/6] 检查 PostgreSQL"
if command -v pg_isready >/dev/null 2>&1; then
    if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
        ok "PostgreSQL 在 localhost:5432 上运行"
    else
        warn "pg_isready 已安装，但 localhost:5432 未响应"
        case "$PLATFORM" in
            linux) info "启动：sudo systemctl start postgresql" ;;
            macos) info "启动：brew services start postgresql@16" ;;
        esac
    fi
else
    warn "未检测到 pg_isready；PostgreSQL 可能未安装"
    case "$PLATFORM" in
        linux) info "Ubuntu/Debian: sudo apt-get install -y postgresql"
               info "Arch:          sudo pacman -S postgresql && sudo -iu postgres initdb -D /var/lib/postgres/data" ;;
        macos) info "macOS:         brew install postgresql@16 && brew services start postgresql@16" ;;
    esac
    info "之后请按 README「开发环境数据库准备」一节创建数据库与用户"
fi

# ── 3. .env 文件 ─────────────────────────────────
bold "==> [3/6] 检查 .env"
if [ ! -f .env ]; then
    cp .env.example .env
    warn ".env 已从 .env.example 复制。请编辑 .env 填入："
    warn "  - POSTGRES_PASSWORD 与 DATABASE_URL（密码保持一致）"
    warn "  - LLM_BASE_URL / LLM_MODEL / LLM_API_KEY"
    warn "填好后重新运行此脚本。"
    exit 0
fi
ok ".env 已存在"

# ── 4. 后端依赖 + Playwright ────────────────────
bold "==> [4/6] 安装后端依赖"
(cd backend && pip install -e . --quiet)
ok "backend pip 依赖完成"

info "安装 Playwright Firefox（首次需下载约 100MB+）..."
python3 -m playwright install firefox
if [ "$PLATFORM" = "linux" ]; then
    info "Linux 平台：安装 Playwright 系统依赖（需 sudo）"
    if command -v sudo >/dev/null 2>&1; then
        sudo python3 -m playwright install-deps firefox || warn "playwright install-deps 失败，可手动重试"
    else
        warn "未检测到 sudo，跳过 install-deps；如运行时报缺库请手动执行 playwright install-deps firefox"
    fi
fi
ok "Playwright Firefox 完成"

# ── 5. 前端依赖 ──────────────────────────────────
bold "==> [5/6] 安装前端依赖"
(cd frontend && pnpm install --frozen-lockfile 2>/dev/null || pnpm install)
ok "frontend pnpm 依赖完成"

# ── 6. 数据库迁移 ────────────────────────────────
bold "==> [6/6] 执行 alembic 迁移"
if (cd backend && alembic upgrade head); then
    ok "数据库迁移完成"
else
    warn "alembic 失败。请检查："
    warn "  - DATABASE_URL 中的账号/密码是否与 PG 一致"
    warn "  - PostgreSQL 是否已运行"
    warn "  - 数据库 / 用户是否已在 PG 中创建（参见 README「数据库准备」）"
    exit 1
fi

# ── 完成 ─────────────────────────────────────────
echo ""
ok "环境就绪。启动开发服务："
echo ""
echo "  # 终端 1：后端"
echo "  cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "  # 终端 2：前端"
echo "  cd frontend && pnpm dev"
echo ""
echo "  # 浏览器访问 http://localhost:5173"
echo ""
warn "注意填入backend/cookies.json，否则爬虫无法正常工作"
