# HardPulse — 二手数码硬件行情系统

面向固定硬件池的二手行情采集与可视化系统，当前数据源为闲鱼（goofish.com）。

完整链路：**爬取（Playwright/Firefox）→ 规则过滤 → LLM 语义校验 → 离群值过滤 → 日聚合 → 前端可视化**

每个监控商品可单独配置「筛选规则」，作为最高优先级约束注入 LLM 校验提示词，适配 CPU/GPU/内存/SSD 乃至任意品类的差异化判断。

---

## 技术栈

| 层级 | 选型 |
|---|---|
| 后端 API | Python 3.12 + FastAPI + uvicorn |
| 数据库 | PostgreSQL 16 + SQLAlchemy 2.x async + asyncpg + Alembic |
| 爬虫 | Playwright（Firefox），拦截闲鱼 mtop XHR |
| LLM 校验 | httpx + OpenAI 兼容协议（OpenAI / DeepSeek / 通义 / 智谱 / 本地 Ollama 等） |
| 统计聚合 | NumPy（log 空间密度聚类 / MAD 离群值过滤） |
| 定时任务 | APScheduler |
| 前端 | Vue 3 + TypeScript + Vite + ECharts + Element Plus + Pinia + vue3-spline |
| 包管理 | uv / pip（Python），pnpm（Node） |
| 部署 | Docker + Docker Compose |

---

## 快速开始（Docker 一键部署）

**适合「只想体验系统」的用户**——无需安装 Python / Node / PostgreSQL，只需 Docker。

### 1. 安装 Docker

- **Windows / macOS**：[Docker Desktop](https://www.docker.com/products/docker-desktop/)
- **Linux**：[Docker Engine](https://docs.docker.com/engine/install/) + Compose 插件

### 2. 启动

```bash
# Linux / macOS
./run.sh

# Windows（双击或命令行）
run.cmd
```

首次启动较慢（下载镜像 + Playwright Firefox，约 1.5GB），之后秒起。

### 3. 访问与配置

服务启动后：
- 前端：**http://localhost:5173**
- 后端 API 文档：http://localhost:8000/docs

打开前端，进入右上角 **「详细设置」** 页面，填写：
- LLM 配置（Base URL / Model / API Key）
- 调度时间（如 `02:00,14:00` 表示每天 2 点和 14 点采集）
- 管理员 Token（默认 `dev-admin-token`）

点击「保存配置」，然后 **按 Ctrl+C 停止容器，重新运行 `./run.sh` 启动**，新配置即生效。

### 4. 可选：闲鱼 Cookie

爬虫不填 Cookie 也能运行，但价格数据可能不完整。若需填入：
- 在「详细设置」页上传 Cookie JSON（Playwright 格式）
- 或直接编辑宿主机 `backend/cookies.json`

---

## 本地开发（适合开发者）

如果你需要改代码、调试，推荐**本地运行而非 Docker**（热重载更快、调试更方便）。

### 前置条件

- Python 3.12+（推荐用 [uv](https://docs.astral.sh/uv/)）
- Node.js 20+ + [pnpm](https://pnpm.io/installation)
- PostgreSQL 16

### 1. 创建数据库

```sql
-- 以 postgres 超级用户执行
CREATE USER market WITH PASSWORD 'your-password';
CREATE DATABASE market OWNER market;
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，**必填**：

```env
# 数据库（密码与 CREATE USER 一致）
DATABASE_URL=postgresql+asyncpg://market:your-password@localhost:5432/market

# LLM —— 任选一组 OpenAI 兼容服务
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-xxxx

# 管理员 Token（硬件池增删改、手动采集、配置接口）
ADMIN_TOKEN=dev-admin-token
```

### 3. 安装依赖

```bash
# 后端
cd backend
uv sync                       # 或：pip install -e .
uv run playwright install firefox
# Linux 还需系统依赖：
uv run playwright install-deps firefox

# 前端
cd ../frontend
pnpm install
```

### 4. 初始化数据库

```bash
cd backend
uv run alembic upgrade head
```

### 5. 启动

```bash
# 终端 1 — 后端（http://localhost:8000）
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 终端 2 — 前端（http://localhost:5173）
cd frontend
pnpm dev
```

浏览器访问 `http://localhost:5173`。

---

## 子项目文档

- 后端细节见 [backend/README.md](backend/README.md)
- 前端细节见 [frontend/README.md](frontend/README.md)
- 维护脚本见 [backend/Debug_Manual.md](backend/Debug_Manual.md)

---

## 项目结构

```
.
├── docker-compose.yml         # Docker 编排（db / backend / frontend）
├── run.sh / run.cmd          # 跨平台一键启动脚本
├── .env / .env.example       # 环境变量配置
├── backend/
│   ├── Dockerfile            # 后端镜像（Python + uv + Playwright）
│   ├── docker-entrypoint.sh  # 容器入口（迁移 + 启动）
│   ├── app/
│   │   ├── api/              # FastAPI 路由
│   │   ├── core/             # 配置 / 数据库 / 硬件池 / 时区
│   │   ├── crawler/          # Playwright 爬虫
│   │   ├── models/           # SQLAlchemy ORM
│   │   ├── schemas/          # Pydantic 输出模型
│   │   ├── services/         # 业务逻辑
│   │   ├── scheduler/        # APScheduler 定时任务
│   │   └── main.py
│   ├── alembic/versions/     # 数据库迁移（0001 → 0008）
│   ├── test_crawl.py         # 单关键词调试
│   ├── revalidate.py         # 历史快照重跑 LLM + 聚合
│   ├── rerun_one_hardware.py # 单硬件当日重跑
│   ├── reset_backend_data.py # 清空业务数据并重建硬件池（慎用）
│   └── cookies.json          # 闲鱼 Cookie（需手动填写，不入 git）
├── frontend/
│   ├── Dockerfile            # 前端镜像（Node + pnpm + Vite dev）
│   └── src/
│       ├── views/            # 落地页 / 看板 / 详情 / 捡漏 / 提醒 / 订阅管理 / 健康 / 配置
│       ├── components/       # OpsLayout / HardwareCard / PriceTrendChart / MiniTrendSparkline
│       ├── api/              # Axios 封装 + 类型定义
│       ├── router/           # 路由
│       └── styles/           # 三层主题（base / light / dark）+ 共享样式
└── scripts/
    └── dev-setup.ps1         # Windows 本地安装脚本（备选，与 Docker 路径互斥）
```

---

## 数据库表结构

| 表 | 说明 |
|---|---|
| `hardware_items` | 硬件池主表（`name` / `category` / `search_keywords` / `validation_rule` / `is_active`） |
| `price_snapshots` | 爬取原始样本（`price` / `title` / `item_url` / `is_valid` / `validation_reason` 等） |
| `daily_stats` | 每日聚合行情（`median` / `avg` / `min` / `max` / `sample_count` / `price_level`） |
| `price_alerts` | 价格提醒规则（`scope` / `rule_type` / `threshold` / `channel` / `channel_target`） |
| `crawl_runs` | 采集运行记录（`started_at` / `ended_at` / `status` / `success` / `failed` / `skipped`） |

`price_level` 为 `low` / `normal` / `high`，由「今日中位价 vs 最近 30 天中位价」的偏离判定，阈值 ±10%。

---

## 统计口径：全站锚点日

聚合视图（首页环图 / 热力矩阵 / 表格）按**全站最近一轮采集日**（所有 `daily_stats` 的 `MAX(stat_date)`，即「锚点日」）取数：

- 商品在锚点日**有**统计 → 展示当轮数据。
- 商品在锚点日**无**统计（本轮未采到样本）→ 归为「今日无数据」，显示灰色，**不回退**到历史旧数据，保证同一张图是同一时点的快照。
- 商品**详情页**例外：仍展示该商品最近一次有数据的统计，但若早于锚点日，会以**红色「⚠ 旧数据」**标注，提示这不是当天数据。

接口侧通过 `HardwareDetail.latest_run_date`（锚点日）与 `stats_is_stale`（是否旧数据）两个字段表达。

---

## 前端页面

| 路由 | 页面 |
|---|---|
| `/` | 落地页（Spline 3D 场景） |
| `/home` | 主看板：热力矩阵 + 表格 + 卡片 + 行情分布环图 + 今日捡漏榜 |
| `/hardware/:id` | 硬件详情：分析卡片 + 价格走势图 + 精选样本 |
| `/deals` | 今日捡漏瀑布卡片 |
| `/alerts` | 价格提醒管理 |
| `/admin/hardware` | 硬件池订阅管理（增删改、筛选规则、手动采集） |
| `/health/crawler` | 采集健康状态 |
| `/config` | 运行时配置（LLM / 数据库 / Cookie / 调度） |

---

## Docker 与本地开发对比

| 维度 | Docker 部署 | 本地开发 |
|---|---|---|
| 适用场景 | 快速体验 / 演示 / 无开发需求 | 日常开发 / 调试 / 改代码 |
| 前置条件 | 只需 Docker | Python + Node + PostgreSQL |
| 启动方式 | `./run.sh` 或 `run.cmd` | 两个终端分别跑后端和前端 |
| 热重载 | 支持（代码 bind mount） | 原生支持（更快） |
| 配置修改 | 前端「详细设置」保存 → 重启容器生效 | 直接编辑 `.env` 重启后端生效 |
| 依赖安装 | 自动（镜像内） | 手动（uv sync + pnpm install） |

---

## 重置数据库

**只清空业务数据，保留表结构，并按硬件池（含筛选规则）重建（最常用）：**

```bash
# 本地开发
cd backend
uv run python reset_backend_data.py

# Docker 环境
docker compose exec backend python reset_backend_data.py
```

也可在前端「订阅管理」页点「重置数据库」（需管理员 Token）。

**彻底重建表结构（慎用）：**

```bash
# 本地
psql "postgresql://market:your-password@localhost:5432/market" \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
cd backend
uv run alembic upgrade head
uv run python reset_backend_data.py

# Docker
docker compose down -v  # 删除数据卷
docker compose up --build
```

---

## 维护脚本

详细参数见 [backend/Debug_Manual.md](backend/Debug_Manual.md)。

| 脚本 | 用途 |
|---|---|
| `test_crawl.py <keyword>` | 单关键词调试爬取，不写库 |
| `revalidate.py` | 历史快照重跑 LLM 校验 + 聚合 |
| `rerun_one_hardware.py --hardware-name <N>` | 单硬件当日重爬 + 清洗 + 聚合 |
| `reset_backend_data.py` | 清空 `price_snapshots` / `daily_stats` 并重建硬件池（**慎用**） |

---

## 常见问题

### Docker 启动后无法访问？

检查容器是否都在运行：
```bash
docker compose ps
```
如果有容器 Exit，查看日志：
```bash
docker compose logs backend
docker compose logs frontend
```

### 前端保存配置后不生效？

Docker 部署下，配置写入 `.env` 但已加载的后端进程不会自动重载。需要：
```bash
docker compose restart backend
```

### Cookie 怎么获取？

1. 浏览器登录 goofish.com
2. 打开开发者工具 → Application/Storage → Cookies
3. 导出为 JSON 数组（Playwright 格式）
4. 在前端「详细设置」上传，或放到 `backend/cookies.json`

### LLM 服务不可用怎么办？

后端仍能启动，但 `is_valid` 字段保持 `null`，聚合结果会偏差。可设 `LLM_VALIDATION_ENABLED=false` 显式跳过 LLM 校验。

---

## 注意事项

- 闲鱼已迁移至 `goofish.com`，爬虫目标 URL 已跟进；爬虫使用 Playwright **Firefox**。
- Cookie 不填仍可运行，但部分商品价格可能不完整；遇强制登录拦截时必须填入。
- 全程使用东八区（CST）时间，见 `app/core/timezone.py`。
- 同一时间只允许一个采集任务（全量或单项），并发触发会被拒绝。
- Docker 部署首次启动会下载约 1.5GB 镜像（主要是 Playwright Firefox 及其依赖）。
