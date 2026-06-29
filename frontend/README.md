# Frontend — 二手数码硬件行情系统前端

Vue 3 + TypeScript 单页应用，消费后端 `/api`，提供行情看板、详情分析、捡漏、提醒、订阅管理与配置等界面。

## 一、技术栈

| 工具 | 用途 |
|---|---|
| Vue 3（Composition API） | 前端框架 |
| TypeScript | 类型安全 |
| Vite | 构建 / 开发服务器 |
| Element Plus | UI 组件库 |
| ECharts | 走势图 / 环图 / 热力矩阵渲染 |
| Pinia | 状态管理（当前较轻） |
| Vue Router 4 | 路由 |
| Axios | HTTP 请求 |
| vue3-spline | 落地页 3D 场景 |

## 二、入口与路由

路由定义见 [src/router/index.ts](src/router/index.ts)：

| 路由 | 组件 | 页面 |
|---|---|---|
| `/` | `LandingPage.vue` | 落地页（Spline 3D） |
| `/home` | `HomeView.vue` | 主看板 |
| `/hardware/:id` | `HardwareDetailView.vue` | 硬件详情 |
| `/deals` | `DealsView.vue` | 今日捡漏 |
| `/alerts` | `AlertsView.vue` | 价格提醒 |
| `/admin/hardware` | `HardwarePoolAdminView.vue` | 订阅管理 |
| `/health/crawler` | `CrawlerHealthView.vue` | 采集健康 |
| `/config` | `ConfigView.vue` | 运行时配置 |

## 三、项目结构

```txt
frontend/
├── Dockerfile               # Docker 镜像定义（Node 20 + pnpm 10 + Vite dev）
├── .dockerignore
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts           # Vite 配置（proxy 可通过 VITE_API_PROXY_TARGET 覆盖）
└── src/
    ├── main.ts
    ├── App.vue
    ├── api/
    │   ├── index.ts         # Axios 实例 + 各接口封装
    │   └── types.ts         # 与后端 schema 对应的 TS 类型
    ├── assets/
    ├── components/
    │   ├── OpsLayout.vue     # 统一侧栏 / 顶栏 / 主题切换 / 系统状态
    │   ├── HardwareCard.vue
    │   ├── MiniTrendSparkline.vue
    │   └── PriceTrendChart.vue
    ├── router/
    │   └── index.ts
    ├── styles/
    │   ├── theme-base.css    # 跨主题共享 token / 结构
    │   ├── theme-light.css   # 浅色变量与覆盖
    │   ├── theme-dark.css    # 深色变量与覆盖
    │   └── ops-shared.css    # 运维页共享样式
    └── views/
        ├── LandingPage.vue
        ├── HomeView.vue
        ├── HardwareDetailView.vue
        ├── DealsView.vue
        ├── AlertsView.vue
        ├── HardwarePoolAdminView.vue
        ├── CrawlerHealthView.vue
        └── ConfigView.vue
```

## 四、主题样式职责

主题入口在 [src/main.ts](src/main.ts)，按顺序加载 `theme-base` → `theme-light` → `theme-dark`：

- **theme-base.css** — 跨主题共享的设计 token 与通用 panel/card/table/control 结构，不放强主题倾向的颜色结论。
- **theme-light.css** — 仅浅色变量与浅色专属覆盖。
- **theme-dark.css** — 仅深色变量与深色专属覆盖。

## 五、页面职责

- **OpsLayout.vue** — 统一侧栏、顶栏、主题切换、系统状态区；被 `HomeView` / `DealsView` / `AlertsView` / `HardwarePoolAdminView` / `CrawlerHealthView` / `ConfigView` 复用。
- **HomeView.vue** — 首页总览：热力矩阵、表格趋势、卡片视图、行情分布环图、右侧今日捡漏榜。
- **HardwareDetailView.vue** — 单硬件详情、量化分析卡片、价格走势图、精选样本；当统计为旧数据时以红色「⚠ 旧数据」标注。
- **HardwarePoolAdminView.vue** — 订阅管理：增删改、启停、**筛选规则编辑**、单项立即采集、重置数据库。
- **DealsView.vue** — 今日捡漏瀑布卡片。
- **AlertsView.vue** — 价格提醒规则管理与测试发送。
- **CrawlerHealthView.vue** — 采集健康状态、最近运行、健康预警。
- **ConfigView.vue** — 运行时配置（LLM / 数据库 / Cookie / 调度），连通性测试。
- **LandingPage.vue** — 落地页，`vue3-spline` 加载 Spline 场景。

## 六、与后端的关键约定

- 接口封装见 [src/api/index.ts](src/api/index.ts)，类型见 [src/api/types.ts](src/api/types.ts)。
- 管理类操作通过请求头 `X-Admin-Token` 鉴权（默认 `dev-admin-token`）。
- 聚合视图按**全站锚点日**取数：`HardwareDetail.latest_stats` 为 `null` 即「今日无数据」，显示灰色；
  详情页用 `latest_run_date` 与 `stats_is_stale` 判断是否为旧数据并红字标注。
- 订阅管理的「筛选规则（选填）」对应 `HardwareDetail.validation_rule`，编辑时回填、为空提交 `null`。

## 七、开发与构建

### 本地开发（推荐）

```bash
cd frontend
pnpm install
pnpm dev          # 开发，默认 http://localhost:5173
```

开发期 `/api` 请求由 Vite 代理到后端（见 [vite.config.ts](vite.config.ts)）：
- **本地**：默认代理到 `http://127.0.0.1:8000`
- **Docker**：容器内通过环境变量 `VITE_API_PROXY_TARGET=http://backend:8000` 指向 backend 服务

需先启动后端：

```bash
# 本地后端
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 或 Docker 后端
docker compose up backend
```

### 构建

```bash
pnpm build        # 类型检查（vue-tsc）+ 生产构建
pnpm preview      # 预览构建产物
```

构建产物在 `dist/`，可用任意静态服务器托管（如 nginx），并配置 `/api` 反向代理到后端。

### Docker 部署

见根目录 [README.md](../README.md) 的 Docker 章节。容器内：
- 使用 Vite dev server（支持热重载）
- `node_modules` 用 named volume 隔离，避免被宿主 bind mount 覆盖
- 环境变量 `VITE_API_PROXY_TARGET` 注入，指向 `backend:8000`

## 八、环境变量

### `VITE_API_PROXY_TARGET`

覆盖 Vite dev server 的 `/api` 代理目标。

- **本地开发**：不设（默认 `http://127.0.0.1:8000`）
- **Docker**：`docker-compose.yml` 注入 `http://backend:8000`

示例：

```bash
# 本地开发时指向远程后端
VITE_API_PROXY_TARGET=http://192.168.1.100:8000 pnpm dev

# Docker compose 已自动注入，无需手动设置
```

## 九、常见问题

### API 请求 404？

检查后端是否在 `http://127.0.0.1:8000` 运行：

```bash
curl http://127.0.0.1:8000/health
```

如果后端在其他地址，设置 `VITE_API_PROXY_TARGET`：

```bash
VITE_API_PROXY_TARGET=http://localhost:9000 pnpm dev
```

### 类型检查报错？

确保 TypeScript 与 Vue 版本兼容，清除缓存重试：

```bash
rm -rf node_modules/.vite
pnpm install
pnpm dev
```

### Docker 环境前端无法访问后端？

检查 `docker-compose.yml` 是否正确注入 `VITE_API_PROXY_TARGET`：

```bash
docker compose config | grep VITE_API_PROXY_TARGET
```

应显示：`VITE_API_PROXY_TARGET: http://backend:8000`

### 主题切换不生效？

主题通过 `localStorage` 持久化，清除浏览器缓存或检查控制台报错。

## 十、Docker 相关

### 容器内路径

- 工作目录：`/app`
- 源码：bind mount 自 `./frontend`（支持热重载）
- node_modules：named volume `frontend_node_modules`（隔离宿主）

### 常用 Docker 命令

```bash
# 重启前端（代码改动通常不需要，Vite 自动热重载）
docker compose restart frontend

# 查看前端日志
docker compose logs -f frontend

# 进入前端容器 shell
docker compose exec frontend sh

# 重新安装依赖（修改 package.json 后）
docker compose exec frontend pnpm install

# 完全重建前端镜像
docker compose build --no-cache frontend
```
