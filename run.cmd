@echo off
REM 一键启动（Windows）。macOS / Linux 请用 ./run.sh。
REM 前置条件：已安装 Docker Desktop 并已启动。
REM 其余环境（Python / Node / PostgreSQL / Playwright）全部在容器内，无需本机安装。

cd /d "%~dp0"

where docker >nul 2>nul
if errorlevel 1 (
    echo [run] 未检测到 docker。请先安装 Docker Desktop：https://www.docker.com/products/docker-desktop/
    exit /b 1
)

docker compose version >nul 2>nul
if errorlevel 1 (
    echo [run] 未检测到 docker compose 插件。请升级 Docker Desktop。
    exit /b 1
)

echo [run] 构建并启动容器（首次较慢，需下载镜像与 Playwright 浏览器）...
docker compose up --build
