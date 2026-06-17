# HardPulse — 二手数码硬件行情系统

面向固定硬件池的闲鱼行情采集与可视化系统。

**爬取（Playwright）→ 规则过滤 → LLM 语义校验 → 离群值过滤 → 日聚合 → 前端可视化**

---

## 技术栈

| 层级 | 选型 |
|---|---|
| 后端 API | Python 3.12 + FastAPI + uvicorn |
| 数据库 | PostgreSQL 16 + SQLAlchemy 2.x async + asyncpg + Alembic |
| 爬虫 | Playwright (Firefox)，拦截闲鱼 mtop XHR |
| LLM 校验 | httpx + OpenAI 兼容协议（OpenAI / DeepSeek / Qwen / 本地 Ollama 均可） |
| 统计聚合 | NumPy（log 空间 DBSCAN / MAD 离群值过滤） |
| 定时任务 | APScheduler |
| 前端 | Vue 3 + TypeScript + Vite + ECharts + Element Plus + vue3-spline |
| 包管理 | pip / uv（Python），pnpm（Node） |

---

## 项目结构

```
.
├── backend/
│   ├── app/
│   │   ├── api/                # FastAPI 路由
│   │   │   ├── hardware.py     # 硬件池 CRUD + 趋势 + 样本
│   │   │   ├── crawler.py      # 爬虫触发 / 暂停 / 状态
│   │   │   ├── validator.py    # LLM 校验任务
│   │   │   ├── deals.py        # 今日捡漏
│   │   │   ├── alerts.py       # 价格提醒 CRUD
│   │   │   └── health.py       # 采集健康
│   │   ├── core/
│   │   │   ├── config.py       # 环境变量读取（pydantic-settings）
│   │   │   ├── database.py     # SQLAlchemy async 引擎
│   │   │   └── hardware_pool.py # 硬件池初始数据
│   │   ├── crawler/
│   │   │   └── xianyu.py       # Playwright Firefox 爬虫
│   │   ├── models/             # SQLAlchemy ORM 模型
│   │   ├── scheduler/          # APScheduler 定时任务
│   │   ├── schemas/            # Pydantic 输出模型
│   │   ├── services/           # 业务逻辑
│   │   │   ├── crawler_service.py
│   │   │   ├── stats.py        # 清洗 + 聚合
│   │   │   ├── llm_validator.py
│   │   │   ├── deals_service.py
│   │   │   ├── health_service.py
│   │   │   └── notifier.py     # Webhook / Telegram 通知
│   │   └── main.py
│   ├── alembic/versions/       # 数据库迁移（0001 → 0007）
│   ├── test_crawl.py           # 单关键词调试爬取，不写库
│   ├── revalidate.py           # 历史快照重跑 LLM + 聚合
│   ├── rerun_one_hardware.py   # 单硬件当日重跑
│   ├── reset_backend_data.py   # 清空业务数据并重建硬件池（慎用）
│   ├── cookies.json            # 闲鱼登录 Cookie（需手动填写）
│   └── Debug_Manual.md        # 维护脚本手册
├── frontend/
│   └── src/
│       ├── views/              # 落地页 / 主看板 / 详情 / 捡漏 / 提醒 / 管理 / 健康
│       ├── components/         # HardwareCard / PriceTrendChart / MiniTrendSparkline
│       ├── api/                # Axios 封装 + 类型定义
│       └── styles/             # 三层主题（base / light / dark）
├── scripts/
│   ├── dev-setup.sh            # Linux/macOS 一键自举
│   └── dev-setup.ps1           # Windows 一键自举
├── .env                        # 实际配置（不入 git）
└── .env.example                # 配置模板
```

---

## 数据库表结构

| 表 | 说明 |
|---|---|
| `hardware_items` | 硬件池主表（id / name / category / search_keywords / is_active） |
| `price_snapshots` | 爬取原始样本（price / title / item_url / is_valid / validation_reason …） |
| `daily_stats` | 每日聚合行情（median / avg / min / max / sample_count / price_level） |
| `price_alerts` | 价格提醒规则（scope / rule_type / threshold / channel / channel_target） |
| `crawl_runs` | 爬虫运行记录（started_at / ended_at / status / success / failed） |

---

## 快速开始

### 前置条件

- Python 3.12+
- Node.js 20+
- pnpm（`npm install -g pnpm`）
- PostgreSQL 16（需提前创建数据库和用户）

### 1. 创建数据库用户和库（首次）

```sql
-- 以 postgres 超级用户执行
CREATE USER market WITH PASSWORD 'your-password';
CREATE DATABASE market OWNER market;
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，**必填项**：

```env
# 数据库（密码与上面 CREATE USER 保持一致）
DATABASE_URL=postgresql+asyncpg://market:your-password@localhost:5432/market

# LLM —— 三选一填一组即可
# 本地 llama.cpp / LM Studio：
LLM_BASE_URL=http://127.0.0.1:8082/v1
LLM_MODEL=your-model-filename.gguf
LLM_API_KEY=

# OpenAI：
# LLM_BASE_URL=https://api.openai.com/v1
# LLM_MODEL=gpt-4o-mini
# LLM_API_KEY=sk-xxxx

# DeepSeek / 通义 / 智谱等 OpenAI 兼容 API 同理

# 管理员 Token（硬件池增删改、手动触发爬取时用）
ADMIN_TOKEN=dev-admin-token
```

**其他可选项**（均有合理默认值，不填也能启动）：

```env
CRAWLER_SCHEDULE=0 2 * * *   # 每天凌晨 2 点自动爬取
FRONTEND_PORT=5173            # 前端端口，用于派生 CORS 白名单
# CORS_ORIGINS=http://localhost:5173   # 手动指定 CORS 白名单（多个逗号分隔）
# TELEGRAM_BOT_TOKEN=                 # 启用 Telegram 通知时填写
```

### 3. 安装依赖

```bash
# 后端
cd backend
pip install -e .
python -m playwright install firefox
# Linux 还需要：
sudo python -m playwright install-deps firefox

# 前端
cd ../frontend
pnpm install
```

### 4. 初始化数据库

```bash
cd backend
alembic upgrade head
```

### 5. 填入闲鱼 Cookie

将浏览器登录闲鱼（goofish.com）后的 Cookie 写入 `backend/cookies.json`。
格式为 Playwright 标准 cookie 数组，可用浏览器扩展（如 EditThisCookie）导出。
**不填 Cookie 爬虫仍可运行，但价格数据可能不完整。**

### 6. 启动服务

开两个终端：

```bash
# 终端 1 — 后端（http://localhost:8000）
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 终端 2 — 前端（http://localhost:5173）
cd frontend
pnpm dev
```

健康检查：`curl http://localhost:8000/health`

---

## API 接口

基址 `http://localhost:8000`，在线文档：`http://localhost:8000/docs`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 服务健康检查 |
| GET | `/api/hardware` | 全部硬件 + 最新统计，按 category 分组 |
| GET | `/api/hardware/admin` | 管理员视图（含 inactive）需要 `X-Admin-Token` |
| GET | `/api/hardware/{id}` | 单硬件详情 + 最新统计 |
| GET | `/api/hardware/{id}/trend?days=7\|30\|90` | 价格趋势 |
| GET | `/api/hardware/{id}/samples?limit=8` | 精选原始样本 |
| POST | `/api/hardware` | 新增硬件（需 `X-Admin-Token`） |
| PATCH | `/api/hardware/{id}` | 编辑硬件（需 `X-Admin-Token`） |
| DELETE | `/api/hardware/{id}` | 软删除（需 `X-Admin-Token`） |
| POST | `/api/hardware/{id}/restore` | 恢复软删除（需 `X-Admin-Token`） |
| POST | `/api/hardware/{id}/crawl` | 单硬件立即爬取（需 `X-Admin-Token`） |
| GET | `/api/crawler/status` | 最近爬虫状态 |
| POST | `/api/crawler/run` | 手动触发全量爬取 |
| POST | `/api/crawler/pause` | 暂停当前爬取 |
| GET | `/api/validator/status` | LLM 校验进度 |
| POST | `/api/validator/run?limit=100` | 手动触发 LLM 校验 |
| GET | `/api/deals/today?limit=20` | 今日捡漏列表 |
| GET | `/api/alerts` | 价格提醒列表 |
| POST | `/api/alerts` | 新增提醒规则 |
| PATCH | `/api/alerts/{id}` | 更新提醒规则 |
| DELETE | `/api/alerts/{id}` | 删除提醒规则 |
| POST | `/api/alerts/{id}/test` | 测试通知发送 |
| GET | `/api/health/crawler` | 采集健康详情 |

需要鉴权的接口在请求头加 `X-Admin-Token: <ADMIN_TOKEN>`（默认 `dev-admin-token`）。

---

## 前端页面

| 路由 | 页面 |
|---|---|
| `/` | 落地页（Spline 3D 场景） |
| `/home` | 主看板：热力矩阵 + 表格 + 卡片 + 今日捡漏榜 |
| `/hardware/:id` | 硬件详情：价格走势图 + 精选样本 |
| `/deals` | 今日捡漏瀑布卡片 |
| `/alerts` | 价格提醒管理 |
| `/admin/hardware` | 硬件池订阅管理（增删改、手动爬取） |
| `/health/crawler` | 采集健康状态 |

---

## 重建数据库

**只清空业务数据，保留表结构（最常用）：**

```bash
cd backend
python reset_backend_data.py
```

**彻底重建表结构：**

```bash
# 用 psql 删库重建
psql "postgresql://market:your-password@localhost:5432/market" \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

cd backend
alembic upgrade head
python reset_backend_data.py
```

---

## 维护脚本

详细参数见 [backend/Debug_Manual.md](backend/Debug_Manual.md)。

| 脚本 | 用途 |
|---|---|
| `test_crawl.py <keyword>` | 单关键词调试爬取，不写库 |
| `revalidate.py` | 历史快照重跑 LLM 校验 + 聚合 |
| `rerun_one_hardware.py --hardware-name <N>` | 单硬件当日重爬 + 清洗 + 聚合 |
| `reset_backend_data.py` | 清空 price_snapshots / daily_stats 并重建硬件池（**慎用**） |

---

## 注意事项

- 闲鱼已迁移至 `goofish.com`，爬虫目标 URL 已跟进
- Playwright Firefox 首次安装需下载约 100 MB
- Cookie 不填仍可运行，但部分商品价格可能不完整；遭遇强制登录拦截时必须填入
- LLM 服务不可用时后端仍可启动，但 `is_valid` 字段将保持 `null`，聚合结果会偏差
