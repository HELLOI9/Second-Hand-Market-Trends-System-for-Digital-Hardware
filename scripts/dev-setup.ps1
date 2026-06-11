# 开发环境一键自举脚本（Windows PowerShell）
# 作用：检测必备工具、装后端/前端依赖、拉 Playwright Firefox、跑数据库迁移
# 不会自动安装 PostgreSQL、Python、Node —— 这些请按下方提示自行安装

$ErrorActionPreference = "Stop"

$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RootDir

function Write-Bold($msg) { Write-Host $msg -ForegroundColor White }
function Write-Ok($msg)   { Write-Host "[ OK ] $msg" -ForegroundColor Green }
function Write-Info2($msg){ Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Warn2($msg){ Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Fail($msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red; exit 1 }

function Require-Cmd($cmd, $hint) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Fail "未检测到 $cmd。请先安装：$hint"
    }
    Write-Ok "${cmd}: $((Get-Command $cmd).Source)"
}

# ── 1. 工具检查 ──────────────────────────────────
Write-Bold "==> [1/6] 检查基础工具"

Require-Cmd "python" "https://www.python.org/downloads/windows/  (>=3.12)"
$pyVer = (python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
$pyParts = $pyVer.Split('.')
if ([int]$pyParts[0] -lt 3 -or ([int]$pyParts[0] -eq 3 -and [int]$pyParts[1] -lt 12)) {
    Write-Fail "Python 版本过低（$pyVer），需要 3.12+"
}
Write-Ok "Python $pyVer"

Require-Cmd "node" "https://nodejs.org/  (>=20)"
$nodeVer = (node -v).TrimStart('v')
$nodeMajor = [int]($nodeVer.Split('.')[0])
if ($nodeMajor -lt 20) { Write-Fail "Node 版本过低（$nodeVer），需要 20+" }
Write-Ok "Node $nodeVer"

if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
    Write-Info2 "未检测到 pnpm，用 npm 安装..."
    npm install -g pnpm
    if ($LASTEXITCODE -ne 0) { Write-Fail "pnpm 安装失败" }
}
Require-Cmd "pnpm" "https://pnpm.io/installation"

# ── 2. PostgreSQL 检查 ────────────────────────────
Write-Bold "==> [2/6] 检查 PostgreSQL"
if (Get-Command pg_isready -ErrorAction SilentlyContinue) {
    & pg_isready -h localhost -p 5432 *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "PostgreSQL 在 localhost:5432 上运行"
    } else {
        Write-Warn2 "pg_isready 可用，但 localhost:5432 未响应"
        Write-Info2 "启动：在「服务」中启动 postgresql-x64-XX，或：pg_ctl start"
    }
} else {
    Write-Warn2 "未检测到 pg_isready；PostgreSQL 可能未安装"
    Write-Info2 "推荐安装方式："
    Write-Info2 "  winget install PostgreSQL.PostgreSQL    (Windows 10+)"
    Write-Info2 "  或下载 EDB 安装器：https://www.postgresql.org/download/windows/"
    Write-Info2 "之后请按 README「开发环境数据库准备」一节创建数据库与用户"
}

# ── 3. .env 文件 ─────────────────────────────────
Write-Bold "==> [3/6] 检查 .env"
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Warn2 ".env 已从 .env.example 复制。请编辑 .env 填入："
    Write-Warn2 "  - POSTGRES_PASSWORD 与 DATABASE_URL（密码保持一致）"
    Write-Warn2 "  - LLM_BASE_URL / LLM_MODEL / LLM_API_KEY"
    Write-Warn2 "填好后重新运行此脚本。"
    exit 0
}
Write-Ok ".env 已存在"

# ── 4. 后端依赖 + Playwright ────────────────────
Write-Bold "==> [4/6] 安装后端依赖"
Push-Location backend
pip install -e . --quiet
if ($LASTEXITCODE -ne 0) { Pop-Location; Write-Fail "pip install 失败" }
Pop-Location
Write-Ok "backend pip 依赖完成"

Write-Info2 "安装 Playwright Firefox（首次需下载约 100MB+）..."
python -m playwright install firefox
if ($LASTEXITCODE -ne 0) { Write-Fail "Playwright Firefox 安装失败" }
Write-Ok "Playwright Firefox 完成"
# Windows 下不需要 install-deps

# ── 5. 前端依赖 ──────────────────────────────────
Write-Bold "==> [5/6] 安装前端依赖"
Push-Location frontend
pnpm install --frozen-lockfile
if ($LASTEXITCODE -ne 0) {
    Write-Warn2 "frozen-lockfile 失败，尝试普通 install"
    pnpm install
    if ($LASTEXITCODE -ne 0) { Pop-Location; Write-Fail "pnpm install 失败" }
}
Pop-Location
Write-Ok "frontend pnpm 依赖完成"

# ── 6. 数据库迁移 ────────────────────────────────
Write-Bold "==> [6/6] 执行 alembic 迁移"
Push-Location backend
alembic upgrade head
$alembicExit = $LASTEXITCODE
Pop-Location
if ($alembicExit -ne 0) {
    Write-Warn2 "alembic 失败。请检查："
    Write-Warn2 "  - DATABASE_URL 中的账号/密码是否与 PG 一致"
    Write-Warn2 "  - PostgreSQL 是否已运行"
    Write-Warn2 "  - 数据库 / 用户是否已在 PG 中创建（参见 README「数据库准备」）"
    exit 1
}
Write-Ok "数据库迁移完成"

# ── 完成 ─────────────────────────────────────────
Write-Host ""
Write-Ok "环境就绪。启动开发服务："
Write-Host ""
Write-Host "  # 终端 1：后端"
Write-Host "  cd backend; uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
Write-Host ""
Write-Host "  # 终端 2：前端"
Write-Host "  cd frontend; pnpm dev"
Write-Host ""
Write-Host "  # 浏览器访问 http://localhost:5173"
Write-Host ""
Write-Warn2 "记得把 backend/cookies.json 准备好，否则爬虫无法工作"
