# Backend — 二手数码硬件行情系统后端

实现完整数据链路：

**爬取（Playwright/Firefox）→ 规则过滤 → LLM 语义校验 → 离群值过滤 + 日聚合 → REST API**

前后端分离，前端在 `../frontend`。

## 1. 技术栈

| 角色 | 选型 |
|---|---|
| HTTP API | FastAPI + uvicorn |
| 数据库 | PostgreSQL 16 + SQLAlchemy 2.x async + asyncpg |
| 迁移 | Alembic |
| 爬虫 | Playwright（Firefox），拦截闲鱼 mtop XHR |
| LLM 调用 | httpx + OpenAI 兼容协议（chat/completions 或 responses 风格） |
| 定时任务 | APScheduler |
| 统计聚合 | NumPy（log 空间密度聚类 / MAD） |
| 配置 | pydantic-settings |

依赖定义见 [pyproject.toml](pyproject.toml)。

## 2. 目录结构

```text
backend/
├── app/
│   ├── api/              # 路由：hardware / crawler / validator / deals / alerts / health / config
│   ├── core/            # config / database / auth / timezone / hardware_pool
│   ├── crawler/         # 闲鱼爬虫（xianyu.py）
│   ├── models/          # SQLAlchemy 模型（hardware / price / alert）
│   ├── scheduler/       # APScheduler 定时任务
│   ├── schemas/         # Pydantic 输出模型
│   ├── services/        # 爬取 / 清洗聚合 / LLM / 捡漏 / 健康 / 通知
│   └── main.py          # FastAPI 入口
├── alembic/             # 数据库迁移（0001 → 0008）
├── test_crawl.py        # 单关键词抓取调试（不写库）
├── revalidate.py        # 历史快照重跑 LLM + 聚合
├── rerun_one_hardware.py# 单硬件当日重跑
├── reset_backend_data.py# 清空业务数据并按硬件池重建
├── Debug_Manual.md
└── README.md
```

## 3. 数据流

```
hardware_pool.py (name / search_keywords / validation_rule)
        │
        ▼  primary search_keyword
crawl_keyword()                # Playwright(Firefox) 抓闲鱼搜索，拦截 mtop XHR
        │
        ▼
save_snapshots()               # 第一层：规则过滤 → price_snapshots
        │
        ▼
LLM validator                  # 第二层：语义校验 → is_valid + validation_reason
        │                      #         （注入该商品 validation_rule 作为最高优先级约束）
        ▼
compute_daily_stats()          # 第三层：离群值过滤 + 聚合 → daily_stats
        │
        ▼
GET /api/hardware              # 前端只读 daily_stats（按全站锚点日取数）
```

## 4. 数据库模型

### 4.1 `hardware_items` — 固定硬件池主表

定义见 [app/models/hardware.py](app/models/hardware.py)：

| 字段 | 说明 |
|---|---|
| `id` / `name` / `category` | 标识与分类（cpu / gpu / memory / ssd / …） |
| `search_keywords` | `TEXT[]`，爬虫实际使用的搜索词（取第一个为主关键词） |
| `validation_rule` | 可空，该商品专属的 LLM 筛选规则（最高优先级注入提示词） |
| `is_active` | 软删除 / 启停开关 |
| `created_at` / `updated_at` | 时间戳（CST） |

> 默认硬件池与各商品筛选规则定义在 [app/core/hardware_pool.py](app/core/hardware_pool.py)，
> `reset_backend_data.py` 与 `/api/hardware/reset` 会据此重建，因此默认商品的规则可长期保留；
> 用户新增的非默认商品不在池中，重置后不保留。

### 4.2 `price_snapshots` — 抓取样本

定义见 [app/models/price.py](app/models/price.py)：

| 字段 | 说明 |
|---|---|
| `hardware_id` | 外键 |
| `price` / `title` / `item_url` | 商品基础信息 |
| `area` / `seller` / `image_url` | 来源元数据 |
| `publish_time` / `crawled_at` / `snapshot_date` | 时间维度 |
| `is_valid` / `validation_reason` | LLM 判定结果（`null` 表示未校验） |

### 4.3 `daily_stats` — 日聚合行情

字段：`hardware_id` / `stat_date` / `median_price` / `avg_price` / `min_price` / `max_price` / `sample_count` / `price_level`。前端首页与趋势图直接依赖这张表。

### 4.4 `price_alerts` / `crawl_runs`

提醒规则与采集运行记录，定义见 [app/models/alert.py](app/models/alert.py) 及迁移 `0007_p0_features`。

## 5. 三层过滤策略

### 5.1 规则过滤（写库前）

发生在 [app/services/stats.py](app/services/stats.py) 的 `save_snapshots()`：价格下限、黑词、分类结构校验（如 SSD 容量匹配）、同日同标题去重。

### 5.2 LLM 语义校验

实现见 [app/services/llm_validator.py](app/services/llm_validator.py)：判定标题是否真为目标商品，写入 `is_valid` / `validation_reason`。

提示词由 `VALIDATION_PROMPT`（品类通用规则）+ 该商品 `validation_rule`（专属规则，最高优先级）拼成。
若商品未配置规则，提示词与不带规则时逐字节一致，完全向后兼容。支持 `chat_completions` 与 `responses` 两种 API 风格（`LLM_API_STYLE`）。

### 5.3 离群值过滤（聚合前）

发生在 `compute_daily_stats()`，**仅对 `is_valid = true`** 的样本：优先 `log(price)` 空间密度聚类，回退 `log(price)` + MAD，并加一层相对主簇中位价的下限，清理远离主簇的脏样本。

### 5.4 行情判定

`_compute_price_level()`：历史样本少于 5 天返回 `normal`；否则按 `(今日中位价 − 最近30天中位价) / 30天中位价` 判定，`≤ −10%` 为 `low`，`≥ +10%` 为 `high`，其间 `normal`。

## 6. 环境变量

配置定义见 [app/core/config.py](app/core/config.py)，从仓库根目录 `.env` 读取（首次 `cp .env.example .env`）。常用项：

```env
DATABASE_URL=postgresql+asyncpg://market:change-me@localhost:5432/market
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-xxxx
LLM_API_STYLE=chat_completions       # 或 responses
LLM_VALIDATION_ENABLED=true
ADMIN_TOKEN=dev-admin-token
CRAWLER_SCHEDULE_TIMES=02:00          # 多个时间点逗号分隔，如 "02:00,14:00"
FRONTEND_PORT=5173
# CORS_ORIGINS=http://localhost:5173
```

查看实际生效值：

```bash
uv run python -c "from app.core.config import settings; print(settings.database_url, settings.llm_base_url, settings.llm_model)"
```

## 7. 启动

首次：

```bash
cd backend
uv sync                       # 或 pip install -e .
uv run playwright install firefox
uv run alembic upgrade head
```

日常：

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

健康检查：`curl http://127.0.0.1:8000/health` · 在线文档：`/docs`

定时采集由 APScheduler 在启动时按 `CRAWLER_SCHEDULE_TIMES` 注册（见 [app/scheduler/jobs.py](app/scheduler/jobs.py)）。

## 8. API 接口

基址 `http://127.0.0.1:8000`，全部业务接口前缀 `/api`。需鉴权者在请求头加 `X-Admin-Token: <ADMIN_TOKEN>`。

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|:---:|---|
| GET | `/health` | | 服务健康检查 |
| GET | `/api/hardware` | | 全部活跃硬件 + 锚点日统计，按 category 分组 |
| GET | `/api/hardware/admin` | ✓ | 管理员视图（含停用、`search_keywords`、`validation_rule`） |
| POST | `/api/hardware` | ✓ | 新增硬件（可带 `validation_rule`、`cold_start`） |
| PATCH | `/api/hardware/{id}` | ✓ | 编辑硬件 |
| DELETE | `/api/hardware/{id}` | ✓ | 软删除（置 `is_active=false`） |
| POST | `/api/hardware/{id}/restore` | ✓ | 恢复软删除 |
| POST | `/api/hardware/{id}/crawl` | ✓ | 单硬件后台采集（BackgroundTasks） |
| POST | `/api/hardware/{id}/crawl-now` | | 单硬件立即采集（独立线程，返回 run_id） |
| GET | `/api/hardware/{id}/crawl-progress` | | 单硬件采集进度 |
| GET | `/api/hardware/{id}` | | 单硬件详情 + 最新统计（含 `latest_run_date` / `stats_is_stale`） |
| GET | `/api/hardware/{id}/trend?days=7\|30\|90` | | 价格趋势 |
| GET | `/api/hardware/{id}/samples?limit=8` | | 精选有效样本 |
| POST | `/api/hardware/reset` | ✓ | 清空业务数据并按硬件池重建 |
| GET | `/api/crawler/status` | | 最近采集状态 |
| POST | `/api/crawler/run?force=false` | | 触发全量采集（爬取 → 校验 → 聚合） |
| POST | `/api/crawler/pause` | | 暂停当前采集 |
| GET | `/api/crawler/test?keyword=&pages=1..5` | | 单关键词测试，**不写库** |
| GET | `/api/validator/status` | | LLM 校验进度 |
| POST | `/api/validator/run?limit=100` | | 手动触发 LLM 校验 |
| GET | `/api/deals/today?limit=20` | | 今日捡漏列表 |
| GET | `/api/alerts` | | 价格提醒列表 |
| POST | `/api/alerts` | | 新增提醒 |
| PATCH | `/api/alerts/{id}` | | 更新提醒 |
| DELETE | `/api/alerts/{id}` | | 删除提醒 |
| POST | `/api/alerts/{id}/test` | | 测试通知发送 |
| GET | `/api/health/crawler` | | 采集健康详情 |
| GET | `/api/config` | ✓ | 读取运行时配置 |
| PATCH | `/api/config` | ✓ | 更新配置（写回 `.env`） |
| POST | `/api/config/test-llm` | ✓ | 测试 LLM 连通性 |
| POST | `/api/config/test-db` | ✓ | 测试数据库连通性 |
| GET / POST / DELETE | `/api/config/cookies` | ✓ | 闲鱼 Cookie 状态 / 上传 / 删除 |

示例：

```bash
curl http://127.0.0.1:8000/api/hardware
curl "http://127.0.0.1:8000/api/hardware/1/trend?days=30"
curl "http://127.0.0.1:8000/api/crawler/test?keyword=RTX%204090&pages=3"
curl -X POST http://127.0.0.1:8000/api/crawler/run
curl -X POST "http://127.0.0.1:8000/api/validator/run?limit=100"
curl -H "X-Admin-Token: dev-admin-token" http://127.0.0.1:8000/api/hardware/admin
```

## 9. 维护脚本

详细参数见 [Debug_Manual.md](Debug_Manual.md)：

| 脚本 | 用途 |
|---|---|
| `test_crawl.py <keyword>` | 单关键词抓取调试，不写库 |
| `revalidate.py [--hardware-name] [--date]` | 历史快照重跑 LLM + 聚合 |
| `rerun_one_hardware.py --hardware-name <N>` | 单硬件当日重爬 + 清洗 + 聚合 |
| `reset_backend_data.py` | 清空 `price_snapshots` / `daily_stats` 并按硬件池重建 `hardware_items`（**慎用**） |

## 10. 数据库查看（psql）

```bash
export DB_HOST=localhost DB_PORT=5432 DB_USER=market DB_NAME=market
export PGPASSWORD='<your_db_password>'
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c 'select 1;'
```

某硬件某天的标题与判定理由：

```bash
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<'SQL'
select h.name, p.price, p.is_valid, p.validation_reason, left(p.title, 80) as title
from price_snapshots p
join hardware_items h on h.id = p.hardware_id
where h.name = 'i7-14700K' and p.snapshot_date = current_date
order by p.id;
SQL
```

聚合结果：

```bash
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<'SQL'
select h.name, d.stat_date, d.median_price, d.sample_count, d.price_level
from daily_stats d
join hardware_items h on h.id = d.hardware_id
where d.stat_date = current_date
order by h.category, h.name;
SQL
```
