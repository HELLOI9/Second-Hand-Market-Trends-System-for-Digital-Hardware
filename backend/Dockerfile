# 后端镜像：FastAPI + Playwright(Firefox) + uv
FROM python:3.12-slim

# uv：快速、可复现的依赖安装
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# venv 建在挂载路径之外（/opt/venv），避免被 compose 的 ./:/workspace bind mount 遮挡；
# 并把 venv bin 放进 PATH，使 alembic / uvicorn / python 直接可用。
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /workspace/backend

# 先装依赖（利用层缓存：仅当依赖清单变化才重装）
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-install-project

# 安装 Playwright Firefox 及系统依赖（在容器内一次装好，用户无需关心）
# 直接用 venv 里的 playwright（PATH 已含 /opt/venv/bin），避免 uv run 触发项目安装
RUN playwright install --with-deps firefox

# 入口脚本
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
