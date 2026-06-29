#!/usr/bin/env bash
# 一键启动（macOS / Linux）。Windows 请用 run.cmd。
# 前置条件：已安装 Docker Desktop / Docker Engine（含 compose 插件）。
# 其余环境（Python / Node / PostgreSQL / Playwright）全部在容器内，无需本机安装。
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
    echo "[run] 未检测到 docker。请先安装 Docker Desktop：https://www.docker.com/products/docker-desktop/" >&2
    exit 1
fi

# 兼容新旧两种 compose 调用方式
if docker compose version >/dev/null 2>&1; then
    COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE="docker-compose"
else
    echo "[run] 未检测到 docker compose 插件。请升级 Docker 或安装 docker-compose。" >&2
    exit 1
fi

echo "[run] 构建并启动容器（首次较慢，需下载镜像与 Playwright 浏览器）..."
exec $COMPOSE up --build
