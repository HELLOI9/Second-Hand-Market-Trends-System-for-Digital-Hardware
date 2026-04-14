# 测试说明

## 目录结构

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
├── reset_backend_data.py # 清除数据库中所有硬件的所有数据
└── README.md
```

## 数据流动完整链路

当前完整链路如下：

1. 从 [hardware_pool.py](/home/jwdeng/project/Second-Hand-Market-Trends-System-for-Digital-Hardware/backend/app/core/hardware_pool.py) 读取固定硬件池
2. 根据 `hardware.name` 在 `hardware_pool.py` 中查对应的 `search_keywords`
3. 用 `crawl_keyword()` 爬取闲鱼结果
4. `save_snapshots()` 做第一层轻量规则过滤后写入 `price_snapshots`
5. LLM 对 `price_snapshots` 逐条判定 `is_valid`
6. `compute_daily_stats()` 只取 `is_valid = true` 的样本做离群值过滤和聚合
7. 将结果写入 `daily_stats`
8. 前端只读取 `daily_stats`并绘图显示

## 调试命令

### 单关键词抓取，不写数据库

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

### 历史数据重跑 LLM

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

### 重跑今日某个硬件

只重跑某个硬件今天的数据

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

### 清除整个数据库并重写硬件池（慎用！）

```bash
/home/jwdeng/miniconda3/envs/Xianyu/bin/python reset_backend_data.py
```