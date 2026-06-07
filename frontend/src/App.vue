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
  --paper-bg: #f7f9fc;
  --paper-bg-soft: #eef3f8;
  --paper-surface: #ffffff;
  --paper-surface-soft: #f8fafc;
  --paper-border: #e4eaf2;
  --paper-border-strong: #ccd6e2;
  --paper-text: #172033;
  --paper-muted: #58687f;
  --paper-subtle: #8a9ab0;
  --paper-shadow: 0 18px 36px rgba(16, 27, 49, 0.07);

  --v1: #101b31;
  --v2: #2f6fed;
  --v3: #0f9f78;
  --v4: #ff9f1c;
  --v5: #8b5cf6;
  --v-soft-1: rgba(16, 27, 49, 0.08);
  --v-soft-2: rgba(47, 111, 237, 0.12);
  --v-soft-3: rgba(15, 159, 120, 0.12);

  --el-color-primary: #101b31;
  --el-color-success: #0f9f78;
  --el-color-warning: #ff9f1c;
  --el-color-danger: #ef4444;
  --el-bg-color: #ffffff;
  --el-border-color: #e4eaf2;
  --el-border-radius-base: 7px;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  min-height: 100vh;
  font-family: 'IBM Plex Sans', 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: linear-gradient(180deg, var(--paper-bg) 0%, var(--paper-bg-soft) 100%);
  color: var(--paper-text);
}

#app {
  min-height: 100vh;
}
</style>
