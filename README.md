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
- `FastAPI` + `SQLAlchemy 2.x` + `asyncpg` + `Alembic`
- `Playwright`（Firefox 抓取与接口拦截）
- `httpx`（调用 OpenAI 兼容 LLM 服务）
- `APScheduler`（定时任务）
- `NumPy`（统计聚合）
- `Pydantic` / `pydantic-settings`

### 前端（`frontend/`）

- `Vue 3` + `TypeScript` + `Vite 5`
- `Vue Router 4` + `Pinia`
- `Element Plus` + `ECharts` + `vue-echarts` + `Axios`

### 数据层

- `PostgreSQL 16`
- 三张核心业务表：`hardware_items`、`price_snapshots`、`daily_stats`

## 3. 项目结构

```text
.
├── backend/                     # FastAPI 后端
│   ├── app/                     # 应用代码（api / core / crawler / models / scheduler / schemas / services）
│   ├── alembic/                 # 数据库迁移
│   ├── reset_backend_data.py    # 清空业务数据并按硬件池重建
│   ├── rerun_one_hardware.py    # 单硬件当日重跑
│   ├── revalidate.py            # 历史快照重跑校验
│   ├── test_crawl.py            # 单关键词抓取调试
│   └── README.md
├── frontend/                    # Vue 前端
│   └── src/                     # 视图、组件、API 封装、路由
├── scripts/
│   ├── dev-setup.sh             # 开发环境自举（Linux / macOS）
│   ├── dev-setup.ps1            # 开发环境自举（Windows）
│   └── legacy/setup.sh          # 旧 Ubuntu 全自动安装脚本（已弃用）
└── .env.example
```

## 4. 本地开发环境（跨 Win / macOS / Linux）

### 4.1 准备

请自行安装：

- **Python 3.12+** ([下载](https://www.python.org/downloads/))
- **Node.js 20+** ([下载](https://nodejs.org/))
- **PostgreSQL 16+**
  - Linux (Ubuntu/Debian)：`sudo apt-get install -y postgresql`
  - macOS：`brew install postgresql@16 && brew services start postgresql@16`
  - Windows：`winget install PostgreSQL.PostgreSQL` 或 [EDB 安装器](https://www.postgresql.org/download/windows/)

### 4.2 数据库准备（首次）

启动 PostgreSQL 后，创建数据库与用户。账号密码与 `.env` 里的 `POSTGRES_USER` / `POSTGRES_PASSWORD` 保持一致即可。

**Linux / macOS：**

```bash
# 默认存在 postgres 超管角色
sudo -u postgres psql <<'SQL'
CREATE USER market WITH PASSWORD 'change-me';
CREATE DATABASE market OWNER market;
SQL
```

macOS（brew 装的 PG，无 postgres 用户）：

```bash
psql postgres <<'SQL'
CREATE USER market WITH PASSWORD 'change-me';
CREATE DATABASE market OWNER market;
SQL
```

**Windows：**

```powershell
# 使用安装时设的 postgres 密码
psql -U postgres -h localhost -c "CREATE USER market WITH PASSWORD 'change-me';"
psql -U postgres -h localhost -c "CREATE DATABASE market OWNER market;"
```

### 4.3 一键自举

```bash
cp .env.example .env
# 编辑 .env：填好 DATABASE_URL 密码、LLM_BASE_URL / LLM_MODEL / LLM_API_KEY
```

然后执行：

**Linux / macOS：**

```bash
bash scripts/dev-setup.sh
```

**Windows（PowerShell）：**

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev-setup.ps1
```

脚本会：检测工具版本 → 装后端 pip 依赖 → 装 Playwright Firefox → 装前端 pnpm 依赖 → 跑 alembic 迁移。**不会**自动安装 Python / Node / PostgreSQL（只检测，缺则给提示）。

### 4.4 启动开发服务

```bash
# 终端 1：后端
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 终端 2：前端
cd frontend
pnpm dev
```

访问：

- 前端开发页：`http://localhost:5173`（Vite 自动代理 `/api` 到 8000）
- Swagger：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health`

爬虫需要 `backend/cookies.json`（goofish 登录后用 Cookie-Editor 等扩展导出 JSON）。

### 4.5 维护脚本

```bash
cd backend
python rerun_one_hardware.py --hardware-name "RTX 4090" --pages 3
python revalidate.py --hardware-name "RTX 4090" --date 2026-04-01 --limit 100
python test_crawl.py "RTX 4090" --pages 1
python reset_backend_data.py    # 慎用
```

## 5. 环境变量

完整变量见 `.env.example`。要点：

- `DATABASE_URL`：本地连接串
- `LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY`：OpenAI 兼容协议；本地 LLM 留空 api_key
- `CRAWLER_SCHEDULE`：cron 表达式，默认每天 02:00
- `FRONTEND_PORT`：用于派生 CORS 白名单，默认 5173（与 Vite 开发端口一致）
- `CORS_ORIGINS`：留空时由 `FRONTEND_PORT` 自动派生
- 通知扩展（Telegram、Webhook、SMTP）已在 `.env.example` 预留位，但本版本未实现

## 6. 运行机制（数据流）

1. 读取固定硬件池（`backend/app/core/hardware_pool.py`）
2. 逐个硬件抓取闲鱼搜索结果
3. 规则过滤后写入 `price_snapshots`
4. 调用 LLM 标注 `is_valid`
5. 对有效样本做离群值过滤与日聚合
6. 写入 `daily_stats`
7. 前端读取 `/api/hardware` 与 `/api/hardware/{id}/trend` 展示

定时任务在后端启动时自动注册，见 `backend/app/scheduler/jobs.py`。

## 7. 常用接口

基址：`/api`

- `GET /hardware`：按分类返回硬件及最新统计
- `GET /hardware/{hardware_id}`：单硬件详情
- `GET /hardware/{hardware_id}/trend?days=7|30|90`：趋势数据
- `GET /crawler/status`：最近爬取状态
- `POST /crawler/run`：手动触发全量爬取（后台任务）
- `POST /validator/run?limit=100`：手动触发校验任务
- `GET /validator/status`：校验进度

## 8. 前端说明

- 首页支持三种视图：热力矩阵、表格趋势、卡片
- 详情页支持 7/30/90 天价格走势 + 估值/动量/波动/可信度分析
- 开发期 Vite 自动把 `/api` 代理到 `http://localhost:8000`

## 9. 常见问题

### Q1：前端打不开数据，接口 404/CORS 报错？

- 确认后端在 8000 端口运行；前端用 `pnpm dev`（5173）走 Vite proxy
- 改了 `.env` 后需要重启 uvicorn

### Q2：爬虫跑不出来数据？

- 检查 `backend/cookies.json` 是否最新（goofish 登录态）
- 查看 uvicorn 控制台日志，找 `Loaded N cookies`
- 必要时给 uvicorn 进程设置 `HTTPS_PROXY` / `HTTP_PROXY`

### Q3：LLM 校验一直失败？

- 检查 `LLM_BASE_URL`（应以 `/v1` 结尾，代码会拼 `/chat/completions`）
- 检查 `LLM_API_KEY`：本地服务可留空，云端服务必填

### Q4：修改硬件池后为什么前端顺序不变/数据不一致？

- 修改 `backend/app/core/hardware_pool.py` 后执行：
  - `cd backend && python reset_backend_data.py`
- 然后触发或等待下一次爬取

## 10. 安全与注意事项

- `.env`、`backend/cookies.json` 已在 `.gitignore`，不要提交
- 建议 `chmod 600 .env backend/cookies.json`
- `reset_backend_data.py` 会清空业务数据，请谨慎
- 当前 `POST /crawler/run`、`POST /validator/run` 无鉴权，不要把后端暴露公网

---

详细后端说明：`backend/README.md`、`backend/Debug_Manual.md`。
