# 项目优化与迭代计划

面向「闲鱼数码硬件行情系统」当前版本的下一阶段路线图。按 **投入产出比** 与 **用户感知价值** 排序，每项给出动机、改动面、依赖、风险。

---

## 优先级总览

| 优先级 | 方向 | 估时 | 依赖 |
| --- | --- | --- | --- |
| P0 | 1. 硬件池可编辑 + 价格订阅 + 推送 | 3-5 天 | 无 |
| P0 | 4. 「今日捡漏」页 | 2-3 天 | 无 |
| P0 | 9. 爬虫健康监控 | 2-3 天 | 无 |
| P1 | 2. 二手 vs 新品价比 | 1-2 周 | JD/淘宝接口 |
| P1 | 3. 多数据源容灾（转转） | 1-2 周 | 转转抓取调研 |
| P1 | 5. 品类指数 | 3-5 天 | 无 |
| P2 | 6. 跨硬件性价比对比 | 1 周 | 性能基准数据 |
| P2 | 7. 新品发布后二手曲线 | 3-5 天 | 发布日期数据 |
| P2 | 8. 地区价差热图 | 3-5 天 | 无（字段已存） |
| P2 | 10. 数据增长应对 | 视量级 | 无 |

---

## P0 — 立刻能做、收益最大

### 1. 硬件池可编辑 + 价格订阅 + 推送

**动机**：当前系统是被动看板，且硬件池写死在代码里（`backend/app/core/hardware_pool.py`，78 个硬件常量）。本次把整条「**用户决策闭环**」补齐：用户从前端自定义硬件池 → 订阅自己关心的硬件或品类 → 价格命中条件后自动推送。两件事放在一起做，是因为它们共用 `hardware_items` 表扩展、API 鉴权层、前端管理页。

**目标产出**
- 用户能从前端增 / 改 / 软删硬件，新硬件**立即冷启动一次爬取**
- 用户能在硬件详情页或订阅页设阈值与渠道，命中后自动推送
- 不引入用户系统：管理动作走 `ADMIN_TOKEN` header；订阅本身不鉴权（chat_id / webhook URL 即身份）

**关键决策（已确认）**

| # | 决策 | 选择 |
|---|---|---|
| Q1 | 硬件池字段迁库范围 | **只迁主表**：`hardware_items` 加 `search_keywords TEXT[]` 与 `is_active`；过滤规则（黑词、容量校验）保留在 `stats.py:40-74`，本期不暴露给 UI |
| Q2 | 删除策略 | **软删**：`is_active=false`，爬虫跳过 inactive 硬件，历史 `price_snapshots` / `daily_stats` 保留，UI 可恢复 |
| Q3 | 订阅模型 | **单表统一字段**：`price_alerts.scope_type ENUM('hardware','category','all') + scope_value TEXT` |
| Q4 | 管理权限 + 冷启动 | **Admin token + 立即冷启动**：`ADMIN_TOKEN` header 校验；新增硬件后台异步触发一次单硬件爬取 |
| Q5 | 推送渠道 | Telegram + 通用 Webhook（插件式，邮件 / 微信留接口不实现） |

**数据模型**

```sql
-- 扩展 hardware_items
ALTER TABLE hardware_items
  ADD COLUMN search_keywords TEXT[] NOT NULL DEFAULT '{}',
  ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE,
  ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT now(),
  ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT now();

-- 新增 price_alerts
CREATE TABLE price_alerts (
  id SERIAL PRIMARY KEY,
  scope_type VARCHAR(16) NOT NULL,        -- 'hardware' | 'category' | 'all'
  scope_value TEXT,                       -- hardware_id 字符串 / category 名 / NULL
  rule_type VARCHAR(20) NOT NULL,         -- 'below_price' | 'below_median_pct' | 'level_low'
  threshold FLOAT,                        -- 具体价 / 偏离比例（0.15=低于中位 15%）/ level_low 不需要
  channel VARCHAR(16) NOT NULL,           -- 'telegram' | 'webhook'
  channel_target TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  last_fired_at TIMESTAMP,
  cooldown_hours INT NOT NULL DEFAULT 24,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX ON price_alerts (scope_type, scope_value, is_active);
CREATE INDEX ON price_alerts (channel, channel_target);
```

**改动面**

后端新增：
- `app/models/alert.py`、`app/services/hardware_pool_service.py`、`app/services/notifier.py`、`app/services/alerts_service.py`、`app/api/alerts.py`、`app/core/auth.py`
- `alembic/versions/0003_hardware_pool_editable_and_alerts.py`（含从 `HARDWARE_POOL` 回填 `search_keywords` 的数据迁移）

后端修改：
- `app/models/hardware.py`：加字段
- `app/core/config.py`：加 `admin_token`、`telegram_bot_token`
- `app/services/crawler_service.py`：`run_full_crawl` 过滤 `is_active=true`；新增 `run_single_hardware_crawl`（抽自 `rerun_one_hardware.py:135-189`）；Phase 3 调 `evaluate_alerts_after_crawl`
- `app/api/hardware.py`：加 `POST` / `PATCH` / `DELETE` / `restore` / `crawl` 五个端点（admin 鉴权）；删 `HARDWARE_ORDER` 对常量的依赖
- `rerun_one_hardware.py`：`search_keywords` 改从 `hw.search_keywords` 取

前端新增：
- `views/HardwarePoolAdminView.vue`（路由 `/admin/hardware`，token 存 localStorage）
- `views/AlertsView.vue`（路由 `/alerts?target=xxx`，按 channel_target 隔离）
- `HardwareDetailView.vue` 加「订阅」按钮（弹窗快速创建针对当前硬件的 alert）

**API 矩阵**

| Method | Path | 鉴权 | 说明 |
|---|---|---|---|
| POST | `/api/hardware` | admin | `{name, category, search_keywords[], cold_start: bool=true}` |
| PATCH | `/api/hardware/{id}` | admin | 改 name / category / search_keywords |
| DELETE | `/api/hardware/{id}` | admin | 软删 |
| POST | `/api/hardware/{id}/restore` | admin | 恢复 |
| POST | `/api/hardware/{id}/crawl` | admin | 手动触发单硬件冷启动 |
| POST | `/api/alerts` | 无 | 创建 |
| GET | `/api/alerts?channel_target=` | 无 | 必传 target，变相隔离 |
| PATCH | `/api/alerts/{id}` | 无 | 更新 |
| DELETE | `/api/alerts/{id}` | 无 | 删除 |
| POST | `/api/alerts/{id}/test` | 无 | 立即发一条测试推送 |

**复用点**

- `rerun_one_hardware.py:135-189` 单硬件全链路 → 抽到 `crawler_service.run_single_hardware_crawl`
- `validate_snapshot_rows_sequential` (`llm_validator.py`)、`compute_daily_stats` (`stats.py`) → 单硬件冷启动直接复用
- FastAPI `BackgroundTasks` → 冷启动异步触发，`api/crawler.py` 已有该模式
- `PriceLevel` 枚举 → `level_low` rule 判定

**风险**

- 频繁触发：`last_fired_at + cooldown_hours` 冷却（默认 24h）
- 凭据脱敏：`channel_target` 写库 OK，但日志里必须脱敏（chat_id 中段、webhook URL 路径打码）
- 误删硬件：软删默认；UI 用 confirm dialog；token 校验失败 401
- 多关键词：`search_keywords` 是数组但本期只用第 0 个，多关键词调度留下次

**估时**：3-5 天（A 数据模型 0.5 / B 服务层 1.5 / C API 0.5 / E 前端 1-2 / 联调文档 0.5）

**详细设计稿**：`.claude/plans/1-api-llm-2-macos-win-linux-3-fluffy-badger.md`

---

### 4. 「今日捡漏」首页板块

**动机**：用户进站第一件事就是想看「今天有没有便宜的」。数据已经在库里，前端 + 一个聚合接口即可。

**实现**
- 新接口 `GET /api/deals/today`
- SQL 思路：今日 `price_snapshots` 中 `is_valid=true` 且 `price ≤ 该硬件 30 天中位价 × 0.85`，按折价率排序
- 返回每条样本（硬件名、价格、折价率、闲鱼链接、地区）

**前端**：首页顶部加「今日捡漏 TOP 20」卡片列表，点击直跳闲鱼。

**风险**：闲鱼链接的有效期、是否要登录。当前 `item_url` 已存全量链接，不构成阻塞。

---

### 9. 爬虫健康监控

**动机**：cookies 失效是高频痛点，事后才发现意味着丢一天数据。提前告警能直接转为可用率。

**改动**
- `daily_stats` 旁加 `crawl_runs` 表，记录每次跑批的：开始/结束时间、成功/失败/跳过数、失败明细 JSON
- 健康规则：
  - 连续 2 天 0 样本的硬件 → 告警
  - 单硬件样本数比上周同期下降 ≥ 70% → 告警
  - cookies 文件 mtime > 30 天 → 提示更新
- `/api/crawler/status` 返回上述指标
- 前端新增「健康面板」（管理员视图）

**风险**：误报率。先收紧阈值（70%、连续 2 天）再放开。

---

## P1 — 真正的差异化

### 2. 二手 vs 新品价比

**动机**：决策关键不是绝对价，而是「相对新品折价率」。这是 ZOL、什么值得买等竞品没法直接给出的。

**数据模型**
```sql
CREATE TABLE retail_prices (
  id SERIAL PRIMARY KEY,
  hardware_id INT NOT NULL REFERENCES hardware_items(id),
  source VARCHAR(20) NOT NULL,         -- 'jd' | 'taobao' | 'manual'
  price FLOAT NOT NULL,
  snapshot_date DATE NOT NULL,
  url TEXT,
  UNIQUE(hardware_id, source, snapshot_date)
);
```

**改动**
- 新爬虫 `app/crawler/jd.py`、`taobao.py`（或人工维护一个 manual 来源）
- 详情页加「折价率 = 1 - 二手中位价/新品价」+ 历史折价率分位数
- 推荐：折价率 > 30% 标「划算」、< 10% 标「不划算」

**风险**：JD/淘宝反爬，建议先做 manual 维护版本（每月人工录一次官价就够），自动化放后面。

---

### 3. 多数据源容灾（转转）

**动机**：当前 100% 依赖闲鱼 cookies，单点失效。加转转作为第二源，价格还能交叉验证（同一硬件两源中位价偏差 > 20% 自动标红）。

**改动**
- `price_snapshots` 加 `source` 字段（默认 `xianyu`），迁移补 default
- 新增 `app/crawler/zhuanzhuan.py`，输出同样的 `RawItem`
- `crawler_service` 同时调度两源
- 聚合逻辑保持一致（按硬件聚合即可），但前端可分别看
- 详情页加「源对比」标签

**风险**：转转字段差异。预计 1-2 天调研页面结构，1 周打通。

---

### 5. 品类指数

**动机**：「显卡市场近 30 天 -8%」这种叙事易于在小红书/B 站传播，是低成本的引流内容。

**实现**
- 接口 `GET /api/index?category=gpu&days=30`
- 算法：当日所有 GPU `daily_stats.median_price` 取几何平均（避免 5090 拉爆均值），归一化到基准日 = 100
- 前端首页顶部加 4 个迷你指数（CPU / GPU / 内存 / SSD）

**风险**：硬件池变动会影响指数连续性。建议固定基准日的硬件集合，新硬件只算自己上市后的子指数。

---

## P2 — 长期差异化

### 6. 跨硬件性价比对比

**前置**：引入 PassMark / 3DMark / Geekbench 数据（一次性入库或人工维护）。

**实现**
- 新表 `performance_benchmarks(hardware_id, benchmark_type, score)`
- 详情页加「单分价 = 二手中位价 / 跑分」
- 工具页：选 2-3 个硬件横向对比（含跑分、单分价、折价率）

---

### 7. 新品发布后的二手曲线

**前置**：`hardware_items` 加 `release_date` 字段。

**实现**
- 详情页趋势图按「上市后 N 天」对齐，可叠加同代不同型号
- 内容运营友好（「RTX 5080 上市 90 天二手贬值 22%」）

---

### 8. 地区价差热图

**动机**：`area` 字段当前抓了但没用，沉默成本。

**实现**
- 接口 `GET /api/hardware/{id}/by-area?days=30`
- 前端用 ECharts 地图组件画热力图
- 适合内容输出：「北上广 RTX 4090 比内陆贵 8%」

**注意**：`area` 字段是闲鱼用户填写的自由文本，需要先做归一化（北京/北京市/京 → 北京）。

---

### 10. 数据增长应对

**触发条件**：`daily_stats` 行数 > 50 万 或 首页加载 > 1 秒。

**方案**
- 新增 `latest_daily_stats` 物化视图或汇总表，每次聚合后写入
- 首页查询直接读这个表，避免子查询 max(stat_date)
- 历史数据冷归档（90 天前的 `price_snapshots` 移到 archive 表，daily_stats 保留全量）

---

## 落地建议

**第一个迭代周期（2 周）建议**：P0 全做完
1. Day 1-3：今日捡漏 + 爬虫健康监控（前后端均小改，先快速出价值）
2. Day 4-10：价格订阅 + Telegram 推送（含 alerts 表迁移、CRUD、订阅前端）
3. Day 11-14：联调 + 上线

**第二个迭代周期（3-4 周）**：P1 二选一
- 如果有时间维护：做「转转多源」（提升数据可靠性，长期价值大）
- 如果想快速变现/传播：做「二手 vs 新品价比」+「品类指数」（适合做内容）

**P2 留作素材库**，等用户反馈最强的那一项再启动。

---

## 不建议立刻做

- **用户系统**：当前是单用户工具，加注册登录会大幅提高使用门槛。订阅功能可以先用「Telegram chat_id 直填」绕过。
- **App / 小程序**：移动端用 Vue 现有页面 PWA 化即可。
- **拓展到非数码品类**：核心算法对硬件强假设（型号精确、价格分布单峰），换品类要重写大半，不在路线图内。
