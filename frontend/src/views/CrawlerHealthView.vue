<template>
  <div class="ops-page">
    <aside class="ops-sidebar">
      <RouterLink class="brand" :to="{ name: 'home' }">
        <span class="brand-mark"><el-icon><Lightning /></el-icon></span>
        <div>
          <strong>Market Pulse</strong>
          <span>Second-hand Market</span>
        </div>
      </RouterLink>
      <nav class="ops-nav">
        <RouterLink :to="{ name: 'home' }"><el-icon><Grid /></el-icon><span>监控概览</span></RouterLink>
        <RouterLink :to="{ name: 'deals' }"><el-icon><Aim /></el-icon><span>今日捡漏</span></RouterLink>
        <RouterLink :to="{ name: 'hardware-admin' }"><el-icon><Setting /></el-icon><span>订阅管理</span></RouterLink>
        <RouterLink :to="{ name: 'alerts' }"><el-icon><Bell /></el-icon><span>价格提醒</span></RouterLink>
        <RouterLink class="active" :to="{ name: 'crawler-health' }"><el-icon><Monitor /></el-icon><span>爬虫健康</span></RouterLink>
      </nav>

      <div class="system-card">
        <span class="system-label">系统状态</span>
        <strong><i></i>后端实时已连接</strong>
        <span>{{ health?.latest_run?.started_at ? `更新于 ${formatDate(health.latest_run.started_at)}` : '等待首次更新' }}</span>
      </div>
    </aside>

    <main class="ops-main">
      <header class="ops-header">
        <div>
          <p>CRAWLER HEALTH</p>
          <h1>爬虫健康监控</h1>
          <span v-if="lastRefreshedAt" class="refresh-stamp">页面刷新于 {{ lastRefreshedAt }}</span>
        </div>
        <el-button type="primary" :icon="Refresh" :loading="loading" @click="loadHealth(false, true)">刷新状态</el-button>
      </header>

      <template v-if="health">
        <section class="health-grid">
          <article class="health-card" :class="health.status">
            <span>总体状态</span>
            <strong>{{ health.status === 'ok' ? '正常' : '需关注' }}</strong>
            <small>{{ health.alerts.length }} 条预警</small>
          </article>
          <article class="health-card">
            <span>启用对象</span>
            <strong>{{ health.active_hardware }}</strong>
            <small>参与行情采集</small>
          </article>
          <article class="health-card">
            <span>Cookie</span>
            <strong>{{ health.cookie_exists ? `${health.cookie_age_days ?? 0}天` : '缺失' }}</strong>
            <small>{{ health.cookie_exists ? '距上次更新' : '需要补充 cookies.json' }}</small>
          </article>
          <article class="health-card">
            <span>采集轮次</span>
            <strong>{{ health.run_count }}</strong>
            <small>{{ health.latest_run?.status ?? '暂无运行记录' }}</small>
          </article>
        </section>

        <section class="run-panel">
          <div class="panel-head">
            <div>
              <h2>最近一次运行</h2>
              <span>{{ health.latest_run?.started_at ? formatDateTime(health.latest_run.started_at) : '暂无' }}</span>
            </div>
            <el-tag v-if="health.latest_run" :type="runTagType" round>
              {{ health.latest_run.status }}
            </el-tag>
          </div>

          <div v-if="health.latest_run" class="run-summary">
            <div><span>成功</span><strong>{{ health.latest_run.success }}</strong></div>
            <div><span>失败</span><strong>{{ health.latest_run.failed }}</strong></div>
            <div><span>跳过</span><strong>{{ health.latest_run.skipped }}</strong></div>
            <div><span>结束时间</span><strong class="time-value">{{ health.latest_run.ended_at ? formatDateTime(health.latest_run.ended_at) : '-' }}</strong></div>
          </div>
        </section>

        <section class="run-panel">
          <div class="panel-head">
            <div>
              <h2>健康预警</h2>
              <span>样本断档、样本骤降与 Cookie 可用性</span>
            </div>
          </div>
          <div v-if="health.alerts.length" class="alert-stack">
            <article v-for="alert in health.alerts" :key="`${alert.hardware}-${alert.message}`" class="health-alert" :class="alert.level">
              <el-icon><WarningFilled /></el-icon>
              <div>
                <strong>{{ alert.hardware ?? '系统' }}</strong>
                <span>{{ alert.message }}</span>
              </div>
            </article>
          </div>
          <el-empty v-else description="当前没有健康预警" />
        </section>
      </template>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { healthApi } from '@/api'
import type { CrawlerHealth } from '@/api/types'

const loading = ref(false)
const health = ref<CrawlerHealth | null>(null)
const lastRefreshedAt = ref('')
let refreshTimer: number | undefined

const isRunning = computed(() => {
  const status = health.value?.latest_run?.status
  return status === 'running' || status === 'crawling' || status === 'validating' || status === 'aggregating'
})

const runTagType = computed(() => {
  const status = health.value?.latest_run?.status
  if (status === 'success') return 'success'
  if (status === 'partial' || status === 'failed') return 'warning'
  return 'info'
})

onMounted(async () => {
  await loadHealth()
  refreshTimer = window.setInterval(() => {
    if (isRunning.value) {
      void loadHealth(true)
    }
  }, 3000)
})

onUnmounted(() => {
  if (refreshTimer) {
    window.clearInterval(refreshTimer)
  }
})

async function loadHealth(silent = false, notify = false) {
  if (!silent) loading.value = true
  try {
    health.value = await healthApi.crawler()
    lastRefreshedAt.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
    if (!silent && notify) {
      ElMessage.success('健康状态已刷新')
    }
  } catch {
    if (!silent) ElMessage.error('加载健康监控失败')
  } finally {
    if (!silent) loading.value = false
  }
}

function formatDate(value: string): string {
  return value.slice(0, 10)
}

function formatDateTime(value: string): string {
  const normalized = value.includes('T') ? value : value.replace(' ', 'T')
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return value.replace('T', ' ').slice(0, 19).replace(/-/g, '/')

  const pad = (num: number) => String(num).padStart(2, '0')
  return `${date.getFullYear()}/${pad(date.getMonth() + 1)}/${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

</script>

<style scoped>
@import './ops-shared.css';

.health-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
  margin-bottom: 18px;
}

.health-card,
.run-panel {
  border: 1px solid var(--paper-border);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: var(--paper-shadow);
}

.health-card {
  padding: 20px;
}

.health-card span,
.health-card small {
  display: block;
  color: #7b8798;
  font-size: 12px;
  font-weight: 700;
}

.health-card strong {
  display: block;
  margin: 8px 0;
  font-size: 28px;
}

.health-card.ok strong {
  color: #16845f;
}

.health-card.warning strong {
  color: #a06512;
}

.run-panel {
  padding: 20px;
  margin-bottom: 18px;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 14px;
}

.panel-head h2 {
  font-size: 18px;
}

.panel-head span {
  display: block;
  margin-top: 3px;
  color: #7b8798;
  font-size: 12px;
}

.refresh-stamp {
  display: block;
  margin-top: 6px;
  color: #7b8798;
  font-size: 12px;
  font-weight: 700;
}

.run-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.run-summary div {
  border: 1px solid #e6ebf2;
  border-radius: 8px;
  padding: 12px;
  background: #f8fafc;
}

.run-summary span,
.run-summary strong {
  display: block;
}

.run-summary span {
  color: #7b8798;
  font-size: 12px;
}

.run-summary strong {
  margin-top: 5px;
  font-size: 18px;
}

.run-summary .time-value {
  white-space: nowrap;
  font-size: 16px;
}

.alert-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.health-alert {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  border: 1px solid #e6ebf2;
  border-radius: 8px;
  padding: 12px;
  background: #f8fafc;
}

.health-alert.error {
  border-color: rgba(124, 111, 156, 0.34);
  background: rgba(124, 111, 156, 0.08);
}

.health-alert.warning {
  border-color: rgba(160, 101, 18, 0.25);
  background: rgba(160, 101, 18, 0.08);
}

.health-alert strong,
.health-alert span {
  display: block;
}

.health-alert span {
  margin-top: 3px;
  color: #64748b;
  font-size: 13px;
}

@media (max-width: 1000px) {
  .health-grid,
  .run-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .health-grid,
  .run-summary {
    grid-template-columns: 1fr;
  }
}
</style>
