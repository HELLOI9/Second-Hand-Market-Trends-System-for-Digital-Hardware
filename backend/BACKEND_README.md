# Backend Debug Guide

本文档记录当前项目后端常用的调试命令，包括：

- 手动启动后端
- 手动爬虫但不写数据库
- 单硬件重跑今日数据
- 数据库查看与清理
- API 接口调用

默认约定：

- 项目根目录：`/home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware`
- 后端目录：`/home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend`
- Python 环境：`/home/jwdeng/miniconda3/envs/Xianyu/bin/python`
- PostgreSQL：`postgresql://market:market_pass@localhost:5432/market`

额外说明：

- `hardware_items` 表现在只保存标准硬件信息，如 `id / name / category`
- 实际用于闲鱼搜索的关键词不再存数据库
- 搜索关键词统一来自 [hardware_pool.py](/home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend/app/core/hardware_pool.py)

## 1. 进入后端目录

```bash
cd /home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend
```

## 2. 启动后端服务

```bash
/home/jwdeng/miniconda3/envs/Xianyu/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

## 3. 手动爬虫调试

### 3.1 单关键词爬取，不写数据库

```bash
/home/jwdeng/miniconda3/envs/Xianyu/bin/python test_crawl.py "i7-14700K" --pages 3
```

说明：

- `--pages` 控制最大翻页数
- 只打印抓取结果，不写数据库

### 3.2 查看更详细的页面调试信息

```bash
/home/jwdeng/miniconda3/envs/Xianyu/bin/python debug_crawler.py "RTX 4090"
```

这个脚本会打印：

- 是否加载到首页
- 是否命中搜索接口
- `resultList` 数量
- 第一条搜索响应体结构

### 3.3 手动重跑历史 LLM 校验

```bash
/home/jwdeng/miniconda3/envs/Xianyu/bin/python revalidate.py --hardware-name "RTX 4090" --date 2026-03-20 --limit 5 --verbose-llm
```

全量未校验数据重跑：

```bash
/home/jwdeng/miniconda3/envs/Xianyu/bin/python revalidate.py
```

强制把已校验数据也重新跑一遍：

```bash
/home/jwdeng/miniconda3/envs/Xianyu/bin/python revalidate.py --force
```

### 3.4 单独重跑某个硬件“今天”的数据

说明：

- 只删除今天的数据，不动其他日期
- 先删除这个硬件今天的 `price_snapshots` 和 `daily_stats`
- 然后重新爬取、重新做 LLM 校验、重新聚合
- 真正用于搜索的关键词来自 `hardware_pool.py`，不是数据库字段

```bash
/home/jwdeng/miniconda3/envs/Xianyu/bin/python rerun_one_hardware.py --hardware-name "i7-14700K"
```

指定页数：

```bash
/home/jwdeng/miniconda3/envs/Xianyu/bin/python rerun_one_hardware.py --hardware-name "i7-14700K" --pages 3
```

输出详细 LLM 请求/响应：

```bash
/home/jwdeng/miniconda3/envs/Xianyu/bin/python rerun_one_hardware.py --hardware-name "i7-14700K" --verbose-llm
```

## 4. 数据库查看命令

### 4.1 测试数据库连接

```bash
pg_isready -h localhost -p 5432
```

```bash
psql postgresql://market:market_pass@localhost:5432/market -c 'select 1;'
```

### 4.2 查看某天抓到了多少原始样本

```bash
psql postgresql://market:market_pass@localhost:5432/market -c "
select snapshot_date, count(*) as snapshot_count
from price_snapshots
where snapshot_date = date '2026-03-24'
group by snapshot_date
order by snapshot_date;
"
```

### 4.3 查看某个硬件某天的 valid/invalid 分布

```bash
psql postgresql://market:market_pass@localhost:5432/market -c "
select h.name, p.snapshot_date, p.is_valid, count(*) as cnt
from price_snapshots p
join hardware_items h on h.id = p.hardware_id
where h.name = 'i7-14700K'
  and p.snapshot_date = date '2026-03-24'
group by h.name, p.snapshot_date, p.is_valid
order by p.is_valid;
"
```

### 4.4 查看某个硬件某天的标题和 LLM 判定理由

```bash
psql postgresql://market:market_pass@localhost:5432/market -c "
select h.name, p.price, p.is_valid, p.validation_reason, left(p.title, 80) as title
from price_snapshots p
join hardware_items h on h.id = p.hardware_id
where h.name = 'PCIe 3.0 2TB'
  and p.snapshot_date = date '2026-03-24'
order by p.id;
"
```

### 4.5 查看当前 daily_stats 聚合结果

```bash
psql postgresql://market:market_pass@localhost:5432/market -c "
select h.name, d.stat_date, d.median_price, d.avg_price, d.sample_count, d.price_level
from daily_stats d
join hardware_items h on h.id = d.hardware_id
where d.stat_date = date '2026-03-20'
order by h.category, h.name;
"
```

### 4.6 删除 2026-03-18 到 2026-03-20 的历史数据

```bash
psql postgresql://market:market_pass@localhost:5432/market <<'SQL'
DELETE FROM daily_stats
WHERE stat_date BETWEEN DATE '2026-03-18' AND DATE '2026-03-20';

DELETE FROM price_snapshots
WHERE snapshot_date BETWEEN DATE '2026-03-18' AND DATE '2026-03-20';
SQL
```

## 5. API 调用命令

默认假设后端运行在 `http://127.0.0.1:8000`

### 5.1 健康检查

```bash
curl http://127.0.0.1:8000/health
```

### 5.2 获取所有硬件列表

```bash
curl http://127.0.0.1:8000/api/hardware
```

### 5.3 获取单个硬件详情

```bash
curl http://127.0.0.1:8000/api/hardware/1
```

### 5.4 获取硬件趋势数据

```bash
curl "http://127.0.0.1:8000/api/hardware/1/trend?days=30"
```

### 5.5 查看爬虫状态

```bash
curl http://127.0.0.1:8000/api/crawler/status
```

### 5.6 手动触发完整爬虫流程

说明：当前主流程已经是：

- 全量爬虫
- 全部爬完后逐条 LLM 校验
- 最后统一聚合

```bash
curl -X POST http://127.0.0.1:8000/api/crawler/run
```

### 5.7 单关键词测试爬虫接口，不写数据库

```bash
curl "http://127.0.0.1:8000/api/crawler/test?keyword=RTX%204090&pages=3"
```

### 5.8 查看 LLM 校验状态

```bash
curl http://127.0.0.1:8000/api/validator/status
```

### 5.9 手动触发 LLM 校验后台任务

```bash
curl -X POST "http://127.0.0.1:8000/api/validator/run?limit=100"
```

## 6. 常见问题

### 6.1 `pnpm dev` 在根目录报没有 `package.json`

因为前端的 `package.json` 在 `frontend/` 下，不在仓库根目录。

正确启动前端：

```bash
cd /home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/frontend
pnpm dev
```

### 6.2 日志里出现“无价格数据，跳过聚合”

当前语义更准确地说是：

- 该 `hardware + date` 经过 LLM 过滤后，没有 `is_valid = true` 的样本

现在代码已经改成：

- 有旧 `daily_stats` 时，会删除旧聚合
- 没旧聚合时，直接跳过
