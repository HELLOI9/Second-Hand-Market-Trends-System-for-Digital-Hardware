#!/usr/bin/env bash
# 后端容器入口：首次补 .env、等待数据库、跑迁移、启动 uvicorn
set -euo pipefail

ROOT_ENV="/workspace/.env"
EXAMPLE_ENV="/workspace/.env.example"

# ── 1. 首次启动补 .env（用户之后在前端「详细设置」里改）────────────
if [ ! -f "$ROOT_ENV" ]; then
    if [ -f "$EXAMPLE_ENV" ]; then
        cp "$EXAMPLE_ENV" "$ROOT_ENV"
        echo "[entrypoint] 已从 .env.example 生成 .env（请在前端「详细设置」中填写 LLM 等配置）"
    else
        touch "$ROOT_ENV"
        echo "[entrypoint] 未找到 .env.example，已创建空 .env"
    fi
fi

# ── 2. 等待数据库就绪 ─────────────────────────────────────────────
echo "[entrypoint] 等待数据库 ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432} ..."
for i in $(seq 1 60); do
    if python -c "
import socket, sys
host = '${POSTGRES_HOST:-db}'
port = int('${POSTGRES_PORT:-5432}')
s = socket.socket()
s.settimeout(2)
try:
    s.connect((host, port)); s.close()
except Exception:
    sys.exit(1)
" 2>/dev/null; then
        echo "[entrypoint] 数据库已就绪"
        break
    fi
    if [ "$i" -eq 60 ]; then
        echo "[entrypoint] 等待数据库超时" >&2
        exit 1
    fi
    sleep 1
done

# ── 3. 跑数据库迁移 ───────────────────────────────────────────────
echo "[entrypoint] 执行 alembic 迁移 ..."
alembic upgrade head

# ── 4. 启动 API ───────────────────────────────────────────────────
echo "[entrypoint] 启动 uvicorn (0.0.0.0:8000) ..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
