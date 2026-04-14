<template>
  <el-config-provider>
    <router-view />
  </el-config-provider>
</template>

<script setup lang="ts">
import { ElConfigProvider } from 'element-plus'
</script>

<style>
:root {
  --paper-bg: #f6f7f9;
  --paper-bg-soft: #edf1f4;
  --paper-surface: #ffffff;
  --paper-surface-soft: #f8fafb;
  --paper-border: #d6d9df;
  --paper-border-strong: #c1c8d1;
  --paper-text: #1f2937;
  --paper-muted: #536170;
  --paper-subtle: #7f8a99;
  --paper-shadow: 0 14px 32px rgba(31, 41, 55, 0.08);

  --v1: #414487;
  --v2: #355f8d;
  --v3: #2a788e;
  --v4: #22a884;
  --v5: #7ad151;
  --v-soft-1: rgba(65, 68, 135, 0.14);
  --v-soft-2: rgba(42, 120, 142, 0.16);
  --v-soft-3: rgba(34, 168, 132, 0.16);

  --el-color-primary: #355f8d;
  --el-color-success: #22a884;
  --el-color-warning: #7a8f2f;
  --el-color-danger: #7c6f9c;
  --el-bg-color: #ffffff;
  --el-border-color: #d6d9df;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  min-height: 100vh;
  font-family: 'IBM Plex Sans', 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background:
    radial-gradient(circle at 10% -12%, rgba(65, 68, 135, 0.09) 0%, transparent 48%),
    radial-gradient(circle at 88% -10%, rgba(42, 120, 142, 0.08) 0%, transparent 44%),
    linear-gradient(180deg, var(--paper-bg) 0%, var(--paper-bg-soft) 100%);
  color: var(--paper-text);
}

#app {
  min-height: 100vh;
}
</style>
