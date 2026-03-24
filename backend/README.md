# Backend README

本目录是“闲鱼数码硬件行情系统”的后端实现，负责：

- 维护固定硬件池
- 调用 Playwright 爬取闲鱼搜索结果
- 对商品标题做 LLM 语义清洗
- 对有效样本做离群值过滤和日级聚合
- 通过 FastAPI 对前端提供查询接口

当前实现是前后端分离架构：

- 前端目录：`../frontend`
- 后端目录：`./`

## 1. 技术栈

- `FastAPI`：HTTP API
- `SQLAlchemy + asyncpg`：异步数据库访问
- `Alembic`：数据库迁移
- `Playwright`：闲鱼页面自动化与接口拦截
- `httpx`：调用本地 LLM OpenAI 兼容接口
- `APScheduler`：定时任务
- `NumPy`：价格统计与离群值过滤

依赖定义见 [pyproject.toml](/home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend/pyproject.toml)。

## 2. 目录结构

```text
backend/
├── app/
│   ├── api/              # FastAPI 路由
│   ├── core/             # 配置、数据库、硬件池
│   ├── crawler/          # 闲鱼爬虫
│   ├── models/           # SQLAlchemy 模型
│   ├── scheduler/        # 定时任务
│   ├── schemas/          # Pydantic 输出模型
│   ├── services/         # 爬虫/LLM/聚合服务
│   └── main.py           # FastAPI 入口
├── alembic/              # 数据库迁移
├── test_crawl.py         # 单关键词抓取调试，不写数据库
├── revalidate.py         # 历史数据重跑 LLM + 聚合
├── rerun_one_hardware.py # 单个硬件“今日数据”重爬+清洗+聚合
└── README.md
```

## 3. 当前数据流

当前完整链路如下：

1. 从 [hardware_pool.py](/home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend/app/core/hardware_pool.py) 读取固定硬件池
2. 根据 `hardware.name` 在 `hardware_pool.py` 中查对应的 `search_keywords`
3. 用 `crawl_keyword()` 爬取闲鱼结果
4. `save_snapshots()` 做第一层轻量规则过滤后写入 `price_snapshots`
5. LLM 对 `price_snapshots` 逐条判定 `is_valid`
6. `compute_daily_stats()` 只取 `is_valid = true` 的样本做离群值过滤和聚合
7. 将结果写入 `daily_stats`
8. 前端只读取 `daily_stats`

### 3.1 关于 `search_keywords`

当前版本中：

- `hardware_items` 表不再存 `search_keywords`
- 搜索关键词只来自 [hardware_pool.py](/home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend/app/core/hardware_pool.py)

也就是说：

- 数据库中的 `name` 用于标识标准硬件
- 实际搜索词由 `hardware_pool.py` 提供

## 4. 数据库模型

### 4.1 `hardware_items`

定义见 [hardware.py](/home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend/app/models/hardware.py)

字段：

- `id`
- `name`
- `category`

作用：

- 固定硬件池主表
- 每一行代表一个标准监控商品

### 4.2 `price_snapshots`

定义见 [price.py](/home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend/app/models/price.py)

字段：

- `hardware_id`
- `price`
- `title`
- `item_url`
- `snapshot_date`
- `area`
- `seller`
- `image_url`
- `publish_time`
- `crawled_at`
- `is_valid`
- `validation_reason`

作用：

- 存储每条抓取商品样本
- 保存 LLM 对该样本的有效性判定

### 4.3 `daily_stats`

定义见 [price.py](/home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend/app/models/price.py)

字段：

- `hardware_id`
- `stat_date`
- `median_price`
- `avg_price`
- `min_price`
- `max_price`
- `sample_count`
- `price_level`

作用：

- 按“硬件 + 日期”聚合后的日行情
- 前端首页和趋势图直接依赖这张表

## 5. 过滤与聚合策略

实现见 [stats.py](/home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend/app/services/stats.py)

### 5.1 第一层规则过滤

发生在 `save_snapshots()`，写入数据库之前。

当前会做：

- `price >= 10`
- 过滤明显无关标题
  - 全局：`笔记本`、`游戏本`、`回收`、`出租`、`租赁`
  - 分类规则：如 SSD 的 `硬盘盒`、`转接卡` 等
- 部分类别做简单结构校验
  - 例如 SSD 容量匹配

### 5.2 第二层 LLM 过滤

实现见 [llm_validator.py](/home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend/app/services/llm_validator.py)

作用：

- 判定商品标题是否真的是目标商品
- 将结果写回 `price_snapshots.is_valid`

### 5.3 第三层离群值过滤

发生在 `compute_daily_stats()`，并且只对 `is_valid = true` 的价格生效。

当前算法：

- 优先：`log(price)` 空间上的密度聚类（DBSCAN 风格）
- 回退：`log(price)` + MAD
- 再增加一个相对主簇中位价的下限

这样比原始 IQR 更适合清理远离价格主簇的低价或高价脏样本。

## 6. 环境变量

配置定义见 [config.py](/home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend/app/core/config.py)

默认从仓库根目录 `.env` 读取。

常用项：

```env
DATABASE_URL=postgresql+asyncpg://market:market_pass@localhost:5432/market
CRAWLER_SCHEDULE=0 2 * * *
LLM_BASE_URL=http://127.0.0.1:8082
LLM_MODEL=Qwen3.5-9B-Q6_K.gguf
```

查看当前代码实际读取到的值：

```bash
cd /home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend
/home/jwdeng/miniconda3/envs/Xianyu/bin/python -c "from app.core.config import settings; print(settings.database_url); print(settings.llm_base_url); print(settings.llm_model)"
```

## 7. 启动方式

### 7.1 启动后端 API

```bash
cd /home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend
/home/jwdeng/miniconda3/envs/Xianyu/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

### 7.2 运行数据库迁移

```bash
cd /home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend
/home/jwdeng/miniconda3/envs/Xianyu/bin/alembic upgrade head
```

## 8. API 接口说明

路由入口见：

- [main.py](/home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend/app/main.py)
- [hardware.py](/home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend/app/api/hardware.py)
- [crawler.py](/home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend/app/api/crawler.py)
- [validator.py](/home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend/app/api/validator.py)

默认基地址：

```text
http://127.0.0.1:8000
```

### 8.1 健康检查

```http
GET /health
```

示例：

```bash
curl http://127.0.0.1:8000/health
```

### 8.2 获取全部硬件及最新统计

```http
GET /api/hardware
```

示例：

```bash
curl http://127.0.0.1:8000/api/hardware
```

返回：

- 按 `category` 分组
- 每个硬件包含 `latest_stats`

### 8.3 获取单个硬件详情

```http
GET /api/hardware/{hardware_id}
```

POSIX 用法：

```bash
curl http://127.0.0.1:8000/api/hardware/<hardware_id>
```

示例：

```bash
curl http://127.0.0.1:8000/api/hardware/1
```

### 8.4 获取趋势数据

```http
GET /api/hardware/{hardware_id}/trend?days=30
```

限制：

- `days` 只支持 `7 / 30 / 90`

POSIX 用法：

```bash
curl "http://127.0.0.1:8000/api/hardware/<hardware_id>/trend?days=<7|30|90>"
```

示例：

```bash
curl "http://127.0.0.1:8000/api/hardware/1/trend?days=30"
```

### 8.5 获取爬虫状态

```http
GET /api/crawler/status
```

示例：

```bash
curl http://127.0.0.1:8000/api/crawler/status
```

### 8.6 触发完整爬虫流程

```http
POST /api/crawler/run
```

当前执行链路：

- 全量爬虫
- 全部爬完后逐条 LLM 校验
- 最后统一聚合

示例：

```bash
curl -X POST http://127.0.0.1:8000/api/crawler/run
```

### 8.7 单关键词测试爬虫，不写数据库

```http
GET /api/crawler/test?keyword=RTX%204090&pages=3
```

POSIX 用法：

```bash
curl "http://127.0.0.1:8000/api/crawler/test?keyword=<urlencoded_keyword>&pages=<N>"
```

参数：

- `keyword`：必填，URL 编码后的搜索关键词
- `pages`：可选，页数，范围 `1-5`

示例：

```bash
curl "http://127.0.0.1:8000/api/crawler/test?keyword=RTX%204090&pages=3"
```

### 8.8 查看 LLM 校验状态

```http
GET /api/validator/status
```

示例：

```bash
curl http://127.0.0.1:8000/api/validator/status
```

### 8.9 手动触发 LLM 校验后台任务

```http
POST /api/validator/run?limit=100
```

POSIX 用法：

```bash
curl -X POST "http://127.0.0.1:8000/api/validator/run?limit=<N>"
```

参数：

- `limit`：可选，本次最多处理多少条未校验快照，默认 `100`

示例：

```bash
curl -X POST "http://127.0.0.1:8000/api/validator/run?limit=100"
```

## 9. 调试命令

### 9.1 单关键词抓取，不写数据库

POSIX 用法：

```bash
python test_crawl.py <keyword> [--pages <N>]
```

参数：

- `<keyword>`：必填，闲鱼搜索关键词，例如 `i7-14700K`
- `--pages <N>`：可选，最大翻页数，默认 `1`

示例：

```bash
cd /home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend
/home/jwdeng/miniconda3/envs/Xianyu/bin/python test_crawl.py "i7-14700K" --pages 3
```

### 9.2 历史数据重跑 LLM

POSIX 用法：

```bash
python revalidate.py [--hardware-id <ID> | --hardware-name <NAME>] [--date <YYYY-MM-DD>] [--limit <N>] [--force] [--skip-stats] [--verbose-llm]
```

参数：

- `--hardware-id <ID>`：可选，只处理某个硬件
- `--hardware-name <NAME>`：可选，只处理某个硬件
- `--date <YYYY-MM-DD>`：可选，只处理某一天
- `--limit <N>`：可选，最多处理多少条
- `--force`：可选，连已校验样本也重新跑
- `--skip-stats`：可选，只做 LLM 校验，不重算聚合
- `--verbose-llm`：可选，打印每条 LLM 请求与响应 JSON

约束：

- `--hardware-id` 与 `--hardware-name` 可以单独使用，也可以同时使用
- 如果同时使用，两者必须匹配同一个硬件

示例：

```bash
/home/jwdeng/miniconda3/envs/Xianyu/bin/python revalidate.py --hardware-name "RTX 4090" --date 2026-03-24 --limit 5 --verbose-llm
```

全量未校验数据：

```bash
/home/jwdeng/miniconda3/envs/Xianyu/bin/python revalidate.py
```

强制重跑：

```bash
/home/jwdeng/miniconda3/envs/Xianyu/bin/python revalidate.py --force
```

### 9.3 只重跑某个硬件今天的数据

POSIX 用法：

```bash
python rerun_one_hardware.py (--hardware-id <ID> | --hardware-name <NAME>) [--pages <N>] [--verbose-llm]
```

参数：

- `--hardware-id <ID>`：可选，数据库中的 `hardware_items.id`
- `--hardware-name <NAME>`：可选，数据库中的 `hardware_items.name`
- `--pages <N>`：可选，最大翻页数，默认 `3`
- `--verbose-llm`：可选，打印每条 LLM 请求与响应 JSON

约束：

- `--hardware-id` 和 `--hardware-name` 至少要提供一个
- 如果两个都提供，必须指向同一个硬件
- 只会删除并重跑“今天”的数据，不会影响其他日期

示例：

```bash
/home/jwdeng/miniconda3/envs/Xianyu/bin/python rerun_one_hardware.py --hardware-name "i7-14700K"
```

指定页数：

```bash
/home/jwdeng/miniconda3/envs/Xianyu/bin/python rerun_one_hardware.py --hardware-name "i7-14700K" --pages 3
```

打印 LLM 请求/响应：

```bash
/home/jwdeng/miniconda3/envs/Xianyu/bin/python rerun_one_hardware.py --hardware-name "i7-14700K" --verbose-llm
```

### 9.4 清空业务数据并重跑今日全量链路

```bash
cd /home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend

psql postgresql://market:market_pass@localhost:5432/market <<'SQL'
TRUNCATE TABLE daily_stats RESTART IDENTITY CASCADE;
TRUNCATE TABLE price_snapshots RESTART IDENTITY CASCADE;
SQL

/home/jwdeng/miniconda3/envs/Xianyu/bin/python - <<'PY'
import asyncio
import logging

from app.core.database import AsyncSessionLocal
from app.services.crawler_service import run_full_crawl

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

async def main():
    async with AsyncSessionLocal() as db:
        summary = await run_full_crawl(db)
        print("\nFINAL SUMMARY:")
        print(summary)

asyncio.run(main())
PY
```

## 10. 数据库查看命令

### 10.1 测试数据库连接

```bash
pg_isready -h localhost -p 5432
```

```bash
psql postgresql://market:market_pass@localhost:5432/market -c 'select 1;'
```

### 10.2 查看某天原始样本量

```bash
psql postgresql://market:market_pass@localhost:5432/market <<'SQL'
select snapshot_date, count(*) as snapshot_count
from price_snapshots
where snapshot_date = date '2026-03-24'
group by snapshot_date
order by snapshot_date;
SQL
```

### 10.3 查看某个硬件某天的 valid/invalid 分布

```bash
psql postgresql://market:market_pass@localhost:5432/market <<'SQL'
select h.name, p.snapshot_date, p.is_valid, count(*) as cnt
from price_snapshots p
join hardware_items h on h.id = p.hardware_id
where h.name = 'i7-14700K'
  and p.snapshot_date = date '2026-03-24'
group by h.name, p.snapshot_date, p.is_valid
order by p.is_valid;
SQL
```

### 10.4 查看某个硬件某天的标题和判定理由

```bash
PAGER=cat psql postgresql://market:market_pass@localhost:5432/market <<'SQL'
select h.name, p.price, p.is_valid, p.validation_reason, left(p.title, 80) as title
from price_snapshots p
join hardware_items h on h.id = p.hardware_id
where h.name = 'i7-14700K'
  and p.snapshot_date = date '2026-03-24'
order by p.id;
SQL
```

### 10.5 查看聚合结果

```bash
psql postgresql://market:market_pass@localhost:5432/market <<'SQL'
select h.name, d.stat_date, d.median_price, d.avg_price, d.sample_count, d.price_level
from daily_stats d
join hardware_items h on h.id = d.hardware_id
where d.stat_date = date '2026-03-24'
order by h.category, h.name;
SQL
```
