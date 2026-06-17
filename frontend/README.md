# 前端说明

## 一、技术栈

| 工具                      | 用途                    |
|-------------------------|-----------------------|
| Vue 3 (Composition API) | 前端框架                  |
| TypeScript              | 类型安全                  |
| Element Plus            | UI 组件库（表格、对话框、按钮、表单等） |
| Pinia                   | 状态管理（当前使用较轻）          |
| Vue Router 4            | 路由管理                  |
| ECharts                 | 价格走势图渲染               |
| Axios                   | HTTP 请求               |
| vue3-spline             | 落地页 3D 场景封装 |
| Vite                    | 构建工具                  |

## 二、入口与路由

- `/`：落地页 `LandingPage.vue`
- `/home`：主看板首页 `HomeView.vue`
- `/hardware/:id`：硬件详情页 `HardwareDetailView.vue`
- `/deals`：今日捡漏 `DealsView.vue`
- `/alerts`：价格提醒 `AlertsView.vue`
- `/admin/hardware`：订阅管理 `HardwarePoolAdminView.vue`
- `/health/crawler`：采集健康 `CrawlerHealthView.vue`

路由定义位于 [src/router/index.ts](src/router/index.ts)。

## 三、项目结构

```txt
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── api/
│   │   ├── index.ts
│   │   └── types.ts
│   ├── assets/
│   ├── components/
│   │   ├── OpsLayout.vue
│   │   ├── HardwareCard.vue
│   │   ├── MiniTrendSparkline.vue
│   │   └── PriceTrendChart.vue
│   ├── router/
│   │   └── index.ts
│   ├── styles/
│   │   ├── theme-base.css
│   │   ├── theme-light.css
│   │   ├── theme-dark.css
│   │   └── ops-shared.css
│   └── views/
│       ├── LandingPage.vue
│       ├── HomeView.vue
│       ├── HardwareDetailView.vue
│       ├── DealsView.vue
│       ├── AlertsView.vue
│       ├── HardwarePoolAdminView.vue
│       └── CrawlerHealthView.vue
```

## 四、主题样式职责

主题入口在 [src/main.ts](src/main.ts)，按顺序加载：

```ts
import './styles/theme-base.css'
import './styles/theme-light.css'
import './styles/theme-dark.css'
```

三层职责如下：

- `theme-base.css`
  - 放跨主题共享的设计 token、通用 panel/card/table/control 规则
  - 负责“结构一致”的部分，不放强主题倾向的颜色结论
- `theme-light.css`
  - 只放浅色主题变量和浅色专属覆盖
  - 包括浅色卡片纯色、浅色详情页顶部白底等
- `theme-dark.css`
  - 只放深色主题变量和深色专属覆盖
  - 包括深色热力矩阵、深色表格、深色详情页面板等

## 五、布局与页面职责

- [src/components/OpsLayout.vue](src/components/OpsLayout.vue)
  - 统一侧边栏、顶栏、主题切换、系统状态区
  - `HomeView`、`DealsView`、`AlertsView`、`HardwarePoolAdminView`、`CrawlerHealthView` 复用该布局
- [src/views/HomeView.vue](src/views/HomeView.vue)
  - 首页总览
  - 包含热力矩阵、表格趋势、卡片视图，以及右侧今日捡漏榜
- [src/views/HardwareDetailView.vue](src/views/HardwareDetailView.vue)
  - 单硬件详情、分析卡片、价格走势图、精选样本
- [src/views/DealsView.vue](src/views/DealsView.vue)
  - 今日捡漏商品瀑布卡片
- [src/views/CrawlerHealthView.vue](src/views/CrawlerHealthView.vue)
  - 采集健康状态、最近运行、健康预警
- [src/views/LandingPage.vue](src/views/LandingPage.vue)
  - 落地页，当前通过 `vue3-spline` 加载 Spline 场景

## 七、开发说明

```bash
cd frontend
pnpm install
pnpm dev
```

默认开发地址：

- `http://localhost:5173`

开发期 `/api` 请求由 Vite 代理到后端服务。
