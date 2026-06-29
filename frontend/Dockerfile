# 前端开发服务器镜像（Vite dev server，自带 /api 代理到 backend 容器）
FROM node:20-slim

WORKDIR /app

# 固定 pnpm 10（匹配 lockfileVersion 9.0），避免 corepack 默认版本与 lock 不兼容
RUN npm install -g pnpm@10

# 先装依赖（利用 Docker 层缓存：lockfile 不变就不重装）
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# 源码由 compose 以挂载方式注入，这里不 COPY，保证热更新
EXPOSE 5173

CMD ["pnpm", "dev", "--host", "0.0.0.0", "--port", "5173"]
