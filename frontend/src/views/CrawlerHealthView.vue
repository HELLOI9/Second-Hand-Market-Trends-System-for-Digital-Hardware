<template>
  <OpsLayout
    active-nav="crawler-health"
  >
    <template #header>
      <header class="ops-header">
        <div class="ops-header-copy">
          <h1 class="ops-header-title"><el-icon><Monitor /></el-icon>采集健康</h1>
          <p class="ops-header-subtitle">
            样本断档、采集轮次和 Cookie 可用性都会在这里统一展示。
            <template v-if="lastRefreshedAt">页面刷新于 {{ lastRefreshedAt }}</template>
          </p>
        </div>
        <el-button type="primary" :icon="Refresh" :loading="loading" @click="loadHealth(false, true)">刷新状态</el-button>
      </header>
    </template>

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
            <small>{{ health.latest_run ? formatRunStatus(health.latest_run.status) : '暂无运行记录' }}</small>
          </article>
        </section>

        <section class="run-panel">
          <div class="panel-head">
            <div>
              <h2>最近一次运行</h2>
              <span>{{ health.latest_run?.started_at ? formatDateTime(health.latest_run.started_at) : '暂无' }}</span>
            </div>
            <el-tag v-if="health.latest_run" :type="runTagType" round>
              {{ formatRunStatus(health.latest_run.status) }}
            </el-tag>
          </div>

          <div v-if="health.latest_run" class="run-summary">
            <div><span>成功</span><strong>{{ health.latest_run.success }}</strong></div>
            <div><span>失败</span><strong>{{ health.latest_run.failed }}</strong></div>
            <div><span>跳过</span><strong>{{ health.latest_run.skipped }}</strong></div>
            <div><span>结束时间</span><strong class="time-value">{{ health.latest_run.ended_at ? formatDateTime(health.latest_run.ended_at) : '-' }}</strong></div>
          </div>

          <template v-if="isRunning && health.latest_run?.progress">
            <div class="progress-block">
              <!-- 爬取进度 -->
              <div class="progress-row">
                <div class="progress-meta">
                  <span class="progress-label">
                    <strong>爬取</strong>
                    <template v-if="health.latest_run.progress.current_hardware">
                      · {{ health.latest_run.progress.current_hardware }}
                    </template>
                  </span>
                  <span class="progress-pct">{{ health.latest_run.progress.crawl_done }} / {{ health.latest_run.progress.crawl_total }}</span>
                </div>
                <el-progress
                  :percentage="health.latest_run.progress.crawl_percent"
                  :status="progressStatus"
                  stroke-width="10"
                  color="#6366f1"
                />
              </div>
              <!-- LLM 校验进度 -->
              <div class="progress-row">
                <div class="progress-meta">
                  <span class="progress-label">
                    <strong>LLM 校验</strong>
                    <template v-if="health.latest_run.progress.llm_current_hardware">
                      · {{ health.latest_run.progress.llm_current_hardware }}
                    </template>
                    <template v-else>
                      · 等待中
                    </template>
                  </span>
                  <span class="progress-pct">
                    <template v-if="health.latest_run.progress.llm_current_done != null">
                      当前硬件 {{ health.latest_run.progress.llm_current_done }} / {{ health.latest_run.progress.llm_current_total }}
                    </template>
                    <template v-else>-</template>
                  </span>
                </div>
                <el-progress
                  :percentage="health.latest_run.progress.llm_current_total ? Math.round((health.latest_run.progress.llm_current_done ?? 0) / health.latest_run.progress.llm_current_total * 100) : 0"
                  stroke-width="10"
                  color="#10b981"
                />
              </div>
            </div>
          </template>
        </section>

        <!-- 单硬件采集进度 -->
        <section v-if="health.active_hw_crawls?.length" class="run-panel">
          <div class="panel-head">
            <div>
              <h2>单硬件采集</h2>
              <span>当前正在执行的单硬件采集任务</span>
            </div>
          </div>
          <div class="hw-crawl-list">
            <article v-for="hwc in health.active_hw_crawls" :key="hwc.hardware_id" class="hw-crawl-item">
              <div class="hw-crawl-name">{{ hwc.hardware_name }}</div>
              <template v-if="hwc.progress">
                <div class="progress-row">
                  <div class="progress-meta">
                    <span class="progress-label"><strong>爬取</strong></span>
                    <span class="progress-pct">{{ hwc.progress.crawl_done }} / {{ hwc.progress.crawl_total }}</span>
                  </div>
                  <el-progress
                    :percentage="hwc.progress.crawl_percent"
                    stroke-width="10"
                    color="#6366f1"
                  />
                </div>
                <div class="progress-row">
                  <div class="progress-meta">
                    <span class="progress-label"><strong>LLM 校验</strong></span>
                    <span class="progress-pct">
                      <template v-if="hwc.progress.llm_current_done != null">
                        {{ hwc.progress.llm_current_done }} / {{ hwc.progress.llm_current_total }}
                      </template>
                      <template v-else>等待中</template>
                    </span>
                  </div>
                  <el-progress
                    :percentage="hwc.progress.llm_percent"
                    stroke-width="10"
                    color="#10b981"
                  />
                </div>
              </template>
              <div v-else class="hw-crawl-waiting">准备中…</div>
            </article>
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
  </OpsLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Monitor, Refresh } from '@element-plus/icons-vue'
import { healthApi } from '@/api'
import type { CrawlerHealth } from '@/api/types'
import OpsLayout from '@/components/OpsLayout.vue'

const loading = ref(false)
const health = ref<CrawlerHealth | null>(null)
const lastRefreshedAt = ref('')
let refreshTimer: number | undefined

const isRunning = computed(() => {
  const status = health.value?.latest_run?.status
  const fullRunActive = status === 'running' || status === 'crawling'
  const hwCrawlActive = (health.value?.active_hw_crawls?.length ?? 0) > 0
  return fullRunActive || hwCrawlActive
})

const runTagType = computed(() => {
  const status = health.value?.latest_run?.status
  if (status === 'success') return 'success'
  if (status === 'partial' || status === 'failed') return 'warning'
  if (status === 'interrupted') return 'danger'
  return 'info'
})

const progressStatus = computed(() => {
  const status = health.value?.latest_run?.status
  if (status === 'success') return 'success'
  if (status === 'partial' || status === 'failed') return 'warning'
  return ''
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

function formatRunStatus(status: string): string {
  const labels: Record<string, string> = {
    success: '成功',
    partial: '部分完成',
    failed: '失败',
    running: '运行中',
    crawling: '采集中',
    interrupted: '已中断',
  }
  return labels[status] ?? status
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
.health-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
  margin-bottom: 18px;
}

.health-card,
.run-panel {
  border: 1px solid var(--paper-border);
  border-radius: var(--radius-card);
  background: var(--surface-floating);
  box-shadow: var(--paper-shadow);
}

.health-card {
  padding: 20px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.health-card span,
.health-card small {
  display: block;
  color: var(--paper-muted);
  font-size: 12px;
  font-weight: 700;
}

.health-card strong {
  display: block;
  margin: 8px 0;
  font-size: 28px;
  color: var(--text-strong);
}

.health-card.ok strong {
  color: var(--text-success);
}

.health-card.warning strong {
  color: var(--text-warning);
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
  color: var(--paper-muted);
  font-size: 12px;
}

.refresh-stamp {
  display: block;
  margin-top: 6px;
  color: var(--paper-muted);
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
  padding: 12px;
}

.run-summary span,
.run-summary strong {
  display: block;
}

.run-summary span {
  color: var(--paper-muted);
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

.progress-block {
  margin-top: 16px;
  padding: 14px 16px;
  border: 1px solid var(--paper-border);
  border-radius: var(--radius-card);
  background: var(--paper-surface-soft);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.progress-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.progress-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: var(--paper-muted);
}

.progress-label strong {
  color: var(--paper-text);
  font-size: 12px;
  font-weight: 900;
}

.progress-pct {
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
  color: var(--paper-muted);
}

.progress-row :deep(.el-progress__text) {
  font-size: 11px !important;
  font-weight: 800;
  color: var(--el-color-primary) !important;
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
  border: 1px solid var(--paper-border);
  border-radius: var(--radius-card);
  padding: 12px;
  background: var(--paper-surface-soft);
}

.health-alert.error {
  border-color: rgba(124, 111, 156, 0.34);
  background: rgba(124, 111, 156, 0.12);
}

.health-alert.warning {
  border-color: rgba(160, 101, 18, 0.25);
  background: rgba(160, 101, 18, 0.12);
}

.health-alert strong,
.health-alert span {
  display: block;
}

.health-alert span {
  margin-top: 3px;
  color: var(--paper-muted);
  font-size: 13px;
}

.hw-crawl-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.hw-crawl-item {
  padding: 14px 16px;
  border: 1px solid var(--paper-border);
  border-radius: var(--radius-card);
  background: var(--paper-surface-soft);
}

.hw-crawl-item h3 {
  font-size: 14px;
  margin-bottom: 10px;
}

.hw-crawl-item h3 .el-tag {
  margin-left: 8px;
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
