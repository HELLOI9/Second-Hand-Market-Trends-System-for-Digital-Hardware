# Backend README

后端实现「闲鱼数码硬件行情系统」的核心链路：

**爬取（Playwright）→ 规则过滤 → LLM 语义校验 → 离群值过滤 + 日聚合 → REST API**

前后端分离架构，前端在 `../frontend`。

## 1. 技术栈

| 角色 | 选型 |
|---|---|
| HTTP API | FastAPI |
| 数据库 | PostgreSQL 16 + SQLAlchemy 2.x async + asyncpg |
| 数据库迁移 | Alembic |
| 爬虫 | Playwright (Firefox)，拦截闲鱼 mtop 接口 |
| LLM 调用 | httpx + OpenAI 兼容协议 |
| 定时任务 | APScheduler |
| 统计聚合 | NumPy（log 空间 DBSCAN / MAD） |
| 配置 | pydantic-settings |

依赖定义见 [pyproject.toml](pyproject.toml)。

## 2. 目录结构

```text
backend/
├── app/
│   ├── api/              # FastAPI 路由（hardware / crawler / validator）
│   ├── core/             # 配置、数据库、硬件池
│   ├── crawler/          # 闲鱼爬虫
│   ├── models/           # SQLAlchemy 模型
│   ├── scheduler/        # APScheduler 定时任务
│   ├── schemas/          # Pydantic 输出模型
│   ├── services/         # 爬虫 / LLM / 聚合服务
│   └── main.py           # FastAPI 入口
├── alembic/              # 数据库迁移
├── test_crawl.py         # 单关键词抓取调试（不写库）
├── revalidate.py         # 历史快照重跑 LLM + 聚合
├── rerun_one_hardware.py # 单硬件当日重跑
├── reset_backend_data.py # 清空业务数据并按硬件池重建
├── Debug_Manual.md       # 维护脚本简版手册
└── README.md
```

## 3. 数据流

```
hardware_pool.py
       │
       ▼ (search_keywords)
crawl_keyword()                    # Playwright 抓闲鱼搜索
       │
       ▼
save_snapshots()                   # 第一层规则过滤 → price_snapshots
       │
       ▼
LLM validator                      # is_valid + validation_reason
       │
       ▼
compute_daily_stats()              # 第三层离群值过滤 + 聚合 → daily_stats
       │
       ▼
GET /api/hardware                  # 前端只读 daily_stats
```

### 关于 `search_keywords`

- `hardware_items` 表**不存** `search_keywords`
- 搜索关键词只来自 [hardware_pool.py](app/core/hardware_pool.py)
- 数据库的 `name` 用于标识标准硬件，实际搜索词由硬件池提供

## 4. 数据库模型

### 4.1 `hardware_items` — 固定硬件池主表

定义见 [hardware.py](app/models/hardware.py)。字段：`id` / `name` / `category`。每行代表一个标准监控商品。

### 4.2 `price_snapshots` — 抓取样本

定义见 [price.py](app/models/price.py)。字段：

| 字段 | 说明 |
|---|---|
| `hardware_id` | 外键 |
| `price` / `title` / `item_url` | 商品基础信息 |
| `area` / `seller` / `image_url` | 来源元数据 |
| `publish_time` / `crawled_at` / `snapshot_date` | 时间维度 |
| `is_valid` / `validation_reason` | LLM 判定结果 |

### 4.3 `daily_stats` — 日聚合行情

定义见 [price.py](app/models/price.py)。字段：`hardware_id` / `stat_date` / `median_price` / `avg_price` / `min_price` / `max_price` / `sample_count` / `price_level`。

前端首页与趋势图直接依赖这张表。

## 5. 三层过滤策略

### 5.1 规则过滤（写库前）

发生在 [stats.py](app/services/stats.py) 的 `save_snapshots()`：

- `price >= 10`
- 黑词：`笔记本` / `游戏本` / `回收` / `出租` / `租赁`
- 分类规则：如 SSD 排除 `硬盘盒` / `转接卡`，并做容量结构校验

### 5.2 LLM 语义校验

实现见 [llm_validator.py](app/services/llm_validator.py)：判定标题是否真为目标商品，结果写入 `price_snapshots.is_valid`。

### 5.3 离群值过滤（聚合前）

发生在 `compute_daily_stats()`，**仅对 `is_valid = true`** 的样本：

- 优先：`log(price)` 空间密度聚类（DBSCAN 风格）
- 回退：`log(price)` + MAD
- 加一层"相对主簇中位价的下限"防止极端低价

比原始 IQR 更适合清理远离主簇的脏样本。

## 6. 环境变量

配置定义见 [config.py](app/core/config.py)，从仓库根目录 `.env` 读取（首次 `cp .env.example .env`）。常用项：

```env
DATABASE_URL=postgresql+asyncpg://market:change-me@localhost:5432/market
CRAWLER_SCHEDULE=0 2 * * *
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-xxxx
FRONTEND_PORT=5173
```

完整字段见根目录 `.env.example`。查看实际生效值：

```bash
python -c "from app.core.config import settings; print(settings.database_url, settings.llm_base_url, settings.llm_model)"
```

## 7. 启动

首次：

```bash
cd backend
alembic upgrade head
```

日常：

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

健康检查：`curl http://127.0.0.1:8000/health`

## 8. API 接口

基址 `http://127.0.0.1:8000`。Swagger 在线文档：`/docs`。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 |
| GET | `/api/hardware` | 全部硬件 + 最新统计（按 category 分组） |
| GET | `/api/hardware/{id}` | 单硬件详情 |
| GET | `/api/hardware/{id}/trend?days=7\|30\|90` | 趋势数据，`days` 仅支持三档 |
| GET | `/api/crawler/status` | 最近爬虫状态 |
| POST | `/api/crawler/run` | 手动触发完整链路（爬取 → 校验 → 聚合） |
| GET | `/api/crawler/test?keyword=&pages=` | 单关键词测试爬虫，**不写库**，`pages` 1-5 |
| GET | `/api/validator/status` | LLM 校验进度 |
| POST | `/api/validator/run?limit=100` | 手动触发 LLM 校验，`limit` 默认 100 |

示例：

```bash
curl http://127.0.0.1:8000/api/hardware
curl "http://127.0.0.1:8000/api/hardware/1/trend?days=30"
curl "http://127.0.0.1:8000/api/crawler/test?keyword=RTX%204090&pages=3"
curl -X POST http://127.0.0.1:8000/api/crawler/run
curl -X POST "http://127.0.0.1:8000/api/validator/run?limit=100"
```

路由实现：[main.py](app/main.py) / [api/hardware.py](app/api/hardware.py) / [api/crawler.py](app/api/crawler.py) / [api/validator.py](app/api/validator.py)。

## 9. 维护脚本

四个 CLI 工具，详细参数与示例见 [Debug_Manual.md](Debug_Manual.md)：

| 脚本 | 用途 |
|---|---|
| `test_crawl.py <keyword>` | 单关键词抓取调试，不写库 |
| `revalidate.py [--hardware-name] [--date]` | 历史快照重跑 LLM + 聚合 |
| `rerun_one_hardware.py --hardware-name <N>` | 单硬件当日重爬 + 清洗 + 聚合 |
| `reset_backend_data.py` | 清空 `price_snapshots` / `daily_stats` 并按硬件池重建 `hardware_items`（**慎用**） |

## 10. 数据库查看（psql）

设置连接参数：

```bash
export DB_HOST=localhost DB_PORT=5432 DB_USER=market DB_NAME=market
export PGPASSWORD='<your_db_password>'
```

测试连接：

```bash
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c 'select 1;'
```

某天原始样本量：

```bash
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<'SQL'
select snapshot_date, count(*) as snapshot_count
from price_snapshots
where snapshot_date = date '2026-03-24'
group by snapshot_date;
SQL
```

某硬件某天 valid/invalid 分布：

```bash
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<'SQL'
select h.name, p.is_valid, count(*) as cnt
from price_snapshots p
join hardware_items h on h.id = p.hardware_id
where h.name = 'i7-14700K' and p.snapshot_date = date '2026-03-24'
group by h.name, p.is_valid
order by p.is_valid;
SQL
```

某硬件某天的标题与判定理由：

```bash
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<'SQL'
select h.name, p.price, p.is_valid, p.validation_reason, left(p.title, 80) as title
from price_snapshots p
join hardware_items h on h.id = p.hardware_id
where h.name = 'i7-14700K' and p.snapshot_date = date '2026-03-24'
order by p.id;
SQL
```

聚合结果：

```bash
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<'SQL'
select h.name, d.stat_date, d.median_price, d.avg_price, d.sample_count, d.price_level
from daily_stats d
join hardware_items h on h.id = d.hardware_id
where d.stat_date = date '2026-03-24'
order by h.category, h.name;
SQL
```
