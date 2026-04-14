# Second-Hand Market Trends System for Digital Hardware

一个面向固定硬件池的二手行情采集与可视化系统。  
当前版本聚焦闲鱼数据，提供「采集 -> 清洗 -> LLM 校验 -> 聚合 -> 前端可视化」的完整链路。

## 1. 项目概览

本项目用于持续追踪 CPU / GPU / 内存 / SSD 的二手价格趋势，核心能力包括：

- 固定硬件池管理（避免关键词漂移）
- 闲鱼搜索结果抓取（Playwright + API 拦截）
- 规则过滤 + LLM 语义过滤
- 每日统计聚合（中位价、均价、区间、样本数、价格等级）
- 多视图展示（热力矩阵 / 表格趋势 / 卡片）
- 单硬件详情分析（7/30/90 天趋势 + 风险/估值/样本可信度）

## 2. 技术栈

### 后端（`backend/`）

- `Python 3.12+`
- `FastAPI`（REST API）
- `SQLAlchemy 2.x` + `asyncpg`（异步数据库访问）
- `Alembic`（数据库迁移）
- `Playwright`（Firefox 抓取与接口拦截）
- `httpx`（调用 OpenAI 兼容 LLM 服务）
- `APScheduler`（定时任务）
- `NumPy / Pandas`（统计与数据处理）
- `Pydantic / pydantic-settings`（配置与 schema）

后端依赖定义见 [backend/pyproject.toml](/home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend/pyproject.toml)。

### 前端（`frontend/`）

- `Vue 3` + `TypeScript`
- `Vite 5`
- `Vue Router 4`
- `Pinia`
- `Element Plus` + `@element-plus/icons-vue`
- `ECharts` + `vue-echarts`
- `Axios`

前端依赖定义见 [frontend/package.json](/home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/frontend/package.json)。

### 数据层

- `PostgreSQL 16`（推荐）
- 三张核心业务表：
  - `hardware_items`
  - `price_snapshots`
  - `daily_stats`

## 3. 项目结构

```text
.
├── backend/                     # FastAPI 后端
│   ├── app/
│   │   ├── api/                 # /api 路由（hardware/crawler/validator）
│   │   ├── core/                # 配置、数据库、硬件池
│   │   ├── crawler/             # 闲鱼抓取
│   │   ├── models/              # SQLAlchemy 模型
│   │   ├── scheduler/           # APScheduler 定时任务
│   │   ├── schemas/             # Pydantic 输出模型
│   │   └── services/            # 爬取/校验/聚合服务
│   ├── alembic/                 # 迁移脚本
│   ├── reset_backend_data.py    # 清空业务数据并按硬件池重建
│   ├── rerun_one_hardware.py    # 单硬件当日重跑
│   ├── revalidate.py            # 历史快照重跑校验
│   └── README.md
├── frontend/                    # Vue 前端
│   ├── src/
│   │   ├── views/               # 首页/详情页
│   │   ├── components/          # 图表、卡片、迷你趋势图
│   │   ├── api/                 # Axios API 封装
│   │   └── router/
│   ├── vite.config.ts           # 本地 /api 代理到 8000
│   └── package.json
├── setup.sh                     # 一键本地环境安装脚本（Linux）
└── .env.example
```

## 4. 环境要求

- OS: Linux（`setup.sh` 以 Ubuntu/Debian 为目标）
- `Python 3.12+`
- `Node.js 18+`（建议）+ `pnpm`
- `PostgreSQL`
- 可用的 OpenAI 兼容 LLM 服务（本地或远程）
- Playwright Firefox 运行依赖

## 5. 环境变量

从 `.env.example` 复制：

```bash
cp .env.example .env
```

示例配置：

```env
DATABASE_URL=postgresql+asyncpg://<db_user>:<db_password>@localhost:5432/<db_name>
CRAWLER_SCHEDULE=0 2 * * *
LLM_BASE_URL=http://127.0.0.1:8082
LLM_MODEL=Qwen3.5-27B-Q4_K_M.gguf
```

说明：

- `DATABASE_URL`：后端数据库连接
- `CRAWLER_SCHEDULE`：定时任务 cron 表达式（默认每天 2:00）
- `LLM_BASE_URL`：OpenAI 兼容服务地址（如 `.../v1/chat/completions`）
- `LLM_MODEL`：模型名称

## 6. 快速启动

### 方案 A：一键安装（推荐，Linux）

```bash
bash setup.sh
```

脚本会做：

- 安装/检查 PostgreSQL
- 创建数据库与用户（可通过环境变量覆盖）
- 安装后端依赖
- 安装 Playwright Firefox 与依赖
- 安装前端依赖
- 执行 Alembic 迁移

脚本见 [setup.sh](/home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/setup.sh)。

### 方案 B：手动安装

1. 后端依赖

```bash
cd backend
pip install -e .
playwright install firefox
playwright install-deps firefox
```

2. 数据库迁移

```bash
cd backend
alembic upgrade head
```

3. 前端依赖

```bash
cd frontend
pnpm install
```

4. 启动服务

```bash
# 终端 1：后端
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 终端 2：前端
cd frontend
pnpm dev
```

## 7. 访问地址

- 前端开发页：`http://localhost:5173`
- 后端 API：`http://localhost:8000`
- Swagger 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health`

## 8. 运行机制（数据流）

1. 读取固定硬件池（[hardware_pool.py](/home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend/app/core/hardware_pool.py)）
2. 逐个硬件抓取闲鱼搜索结果
3. 规则过滤后写入 `price_snapshots`
4. 调用 LLM 标注 `is_valid`
5. 对有效样本做离群值过滤与日聚合
6. 写入 `daily_stats`
7. 前端读取 `/api/hardware` 与 `/api/hardware/{id}/trend` 展示

定时任务在后端启动时自动注册，定义见 [jobs.py](/home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend/app/scheduler/jobs.py)。

## 9. 常用接口

基址：`/api`

- `GET /hardware`：按分类返回硬件及最新统计（已按硬件池顺序）
- `GET /hardware/{hardware_id}`：单硬件详情
- `GET /hardware/{hardware_id}/trend?days=7|30|90`：趋势数据
- `GET /crawler/status`：最近爬取状态
- `POST /crawler/run`：手动触发全量爬取（后台任务）
- `POST /validator/run?limit=100`：手动触发校验任务
- `GET /validator/status`：校验进度

## 10. 常用维护脚本（后端）

在 `backend/` 下执行：

- 单关键词抓取调试（不写库）
  - `python test_crawl.py "<keyword>" --pages 3`
- 单硬件当日重跑
  - `python rerun_one_hardware.py --hardware-name "RTX 4090" --pages 3`
- 历史快照重跑 LLM 校验
  - `python revalidate.py --hardware-name "RTX 4090" --date 2026-04-01 --limit 100`
- 清空业务数据并按硬件池重建（慎用）
  - `python reset_backend_data.py`

## 11. 前端说明

- 首页支持三种视图：热力矩阵、表格趋势、卡片视图
- 详情页支持：
  - 7/30/90 天价格走势
  - 估值定位、趋势动量、波动风险、样本可信度分析
- 本地开发使用 Vite 代理：
  - `frontend/vite.config.ts` 将 `/api` 转发到 `http://localhost:8000`

## 12. 常见问题

### Q1：前端打不开数据，接口 404/跨域问题？

- 确认后端已启动在 `8000`
- 确认前端通过 `pnpm dev` 启动（走 Vite 代理）

### Q2：爬虫跑不出来数据？

- 检查 `backend/cookies.json` 是否存在且有效
- 检查 Playwright Firefox 是否安装成功
- 检查网络代理与站点可访问性

### Q3：LLM 校验一直失败？

- 检查 `LLM_BASE_URL` 与 `LLM_MODEL`
- 确保目标服务兼容 OpenAI Chat Completions API

### Q4：修改硬件池后为什么前端顺序不变/数据不一致？

- 修改 [hardware_pool.py](/home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend/app/core/hardware_pool.py) 后，建议执行：
  - `python reset_backend_data.py`
- 然后重新爬取当日数据

## 13. 安全与注意事项

- `.env`、`cookies.json` 不应提交到仓库
- 默认配置仅用于本地开发，生产环境请替换为安全凭据
- `reset_backend_data.py` 会清空业务数据，请谨慎使用

---

如需更详细的后端调试说明，可查看 [backend/README.md](/home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend/README.md) 与 [backend/Debug_Manual.md](/home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend/Debug_Manual.md)。
