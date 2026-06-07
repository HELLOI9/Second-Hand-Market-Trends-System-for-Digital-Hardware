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
        <RouterLink class="active" :to="{ name: 'alerts' }"><el-icon><Bell /></el-icon><span>价格提醒</span></RouterLink>
        <RouterLink :to="{ name: 'crawler-health' }"><el-icon><Monitor /></el-icon><span>爬虫健康</span></RouterLink>
      </nav>

      <div class="system-card">
        <span class="system-label">系统状态</span>
        <strong><i></i>后端实时已连接</strong>
        <span>{{ crawlerStatus?.last_run_date ? `更新于 ${crawlerStatus.last_run_date}` : '等待首次更新' }}</span>
      </div>
    </aside>

    <main class="ops-main">
      <header class="ops-header">
        <div>
          <p>PRICE ALERTS</p>
          <h1>价格提醒</h1>
        </div>
        <div class="target-box">
          <el-button type="primary" :icon="Plus" @click="creatingVisible = true">创建新提醒</el-button>
        </div>
      </header>

      <el-dialog v-model="creatingVisible" title="创建新提醒" width="620px">
        <el-form :model="draft" label-position="top" class="alert-grid">
          <el-form-item label="商品">
            <el-select v-model="selectedHardwareId" filterable placeholder=" ">
              <el-option
                v-for="item in hardwareOptions"
                :key="item.id"
                :label="item.name"
                :value="String(item.id)"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="价格阈值">
            <el-input v-model="minPriceText" inputmode="decimal" :placeholder="priceThresholdPlaceholder" />
          </el-form-item>
          <el-form-item label="通道">
            <el-select v-model="draft.channel">
              <el-option label="Webhook" value="webhook" />
              <el-option label="Telegram" value="telegram" />
            </el-select>
          </el-form-item>
          <el-form-item label="推送地址">
            <el-input v-model="channelTarget" placeholder="Webhook URL 或 Telegram chat_id" @change="saveTarget" />
          </el-form-item>
          <div class="alert-action-slot">
            <el-button type="primary" :icon="Plus" :loading="saving" @click="createAlert">创建提醒</el-button>
          </div>
        </el-form>
      </el-dialog>

      <section class="alert-list">
        <div class="panel-head">
          <div>
            <h2>提醒列表</h2>
            <span>{{ alerts.length }} 条订阅 · {{ activeCount }} 条启用</span>
          </div>
        </div>

        <div class="alert-table">
          <div class="alert-head">
            <span>状态</span>
            <span>提醒对象</span>
            <span>规则</span>
            <span>通道</span>
            <span>最近触发</span>
            <span>操作</span>
          </div>

          <article v-for="alert in sortedAlerts" :key="alert.id" class="alert-row" :class="{ idle: !alert.is_active }">
            <div class="status-cell">
              <el-switch
                :model-value="alert.is_active"
                @change="(value: string | number | boolean) => setAlertActive(alert, Boolean(value))"
              />
              <strong :class="{ active: alert.is_active }">{{ alert.is_active ? 'ACTIVE' : 'IDLE' }}</strong>
            </div>

            <div class="alert-object">
              <h3>{{ scopeText(alert) }}</h3>
              <el-tag :type="alert.is_active ? 'success' : 'info'" effect="light" round>
                {{ alert.is_active ? '提醒中' : '已暂停' }}
              </el-tag>
            </div>

            <div class="rule-cell">
              <strong>{{ ruleText(alert) }}</strong>
              <span>价格低于阈值时提醒</span>
            </div>

            <div class="channel-cell">
              <strong>{{ alert.channel }}</strong>
              <span>{{ alert.channel_target }}</span>
            </div>

            <div class="time-cell">
              <strong>{{ alert.last_fired_at ? formatDateTime(alert.last_fired_at) : '-' }}</strong>
              <span>{{ alert.last_fired_at ? '最近一次触发' : '尚未触发' }}</span>
            </div>

            <div class="action-cell">
              <el-button
                v-if="alert.is_active"
                class="run-toggle danger"
                :icon="Close"
                @click="setAlertActive(alert, false)"
              >
                停止
              </el-button>
              <el-button
                v-else
                class="run-toggle"
                type="primary"
                :icon="VideoPlay"
                @click="setAlertActive(alert, true)"
              >
                启动
              </el-button>
              <el-button class="icon-action" :icon="Edit" text title="编辑" @click="editAlert(alert)" />
              <el-button class="icon-action" :icon="Delete" text title="删除" @click="deleteAlert(alert)" />
            </div>
          </article>

          <el-empty v-if="!alerts.length" description="暂无提醒" />
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Close, Delete, Edit, Plus, VideoPlay } from '@element-plus/icons-vue'
import { alertsApi, crawlerApi, hardwareApi } from '@/api'
import type { AlertPayload, CrawlerStatus, HardwareDetail, PriceAlert } from '@/api/types'

const TARGET_KEY = 'hardware-alert-target'
const route = useRoute()
const channelTarget = ref(localStorage.getItem(TARGET_KEY) ?? '')
const alerts = ref<PriceAlert[]>([])
const hardwareOptions = ref<HardwareDetail[]>([])
const loading = ref(false)
const saving = ref(false)
const crawlerStatus = ref<CrawlerStatus | null>(null)
const selectedHardwareId = ref(typeof route.query.hardwareId === 'string' ? route.query.hardwareId : '')
const minPriceText = ref('')
const creatingVisible = ref(false)

const draft = reactive<AlertPayload>({
  scope_type: 'hardware',
  scope_value: selectedHardwareId.value,
  rule_type: 'below_price',
  threshold: null,
  channel: 'webhook',
  channel_target: channelTarget.value,
  cooldown_hours: 24,
  is_active: true,
})

const activeCount = computed(() => alerts.value.filter((alert) => alert.is_active).length)
const sortedAlerts = computed(() => {
  return [...alerts.value].sort((a, b) => {
    if (a.is_active !== b.is_active) return a.is_active ? -1 : 1
    return b.id - a.id
  })
})
const selectedHardware = computed(() => {
  return hardwareOptions.value.find((item) => String(item.id) === selectedHardwareId.value) ?? null
})
const priceThresholdPlaceholder = computed(() => {
  const median = selectedHardware.value?.latest_stats?.median_price
  return median ? `中位价 ¥${formatPrice(median)}` : '中位价'
})

watch(channelTarget, (value) => {
  draft.channel_target = value
})

onMounted(() => {
  void loadHardwareOptions()
  void loadCrawlerStatus()
  void loadAlerts()
})

async function loadHardwareOptions() {
  try {
    const grouped = await hardwareApi.list()
    hardwareOptions.value = Object.values(grouped).flat().filter((item) => item.is_active)
  } catch {
    ElMessage.error('加载订阅商品失败')
  }
}

async function loadCrawlerStatus() {
  try {
    crawlerStatus.value = await crawlerApi.status()
  } catch {
    crawlerStatus.value = null
  }
}

function saveTarget() {
  localStorage.setItem(TARGET_KEY, channelTarget.value)
}

async function loadAlerts() {
  saveTarget()
  loading.value = true
  try {
    alerts.value = await alertsApi.list(channelTarget.value.trim() || undefined)
  } catch {
    ElMessage.error('加载提醒失败')
  } finally {
    loading.value = false
  }
}

async function createAlert() {
  if (!channelTarget.value.trim()) {
    ElMessage.warning('先填写通知地址')
    return
  }
  if (!selectedHardwareId.value) {
    ElMessage.warning('请选择商品')
    return
  }
  const threshold = Number(minPriceText.value)
  if (!Number.isFinite(threshold) || threshold <= 0) {
    ElMessage.warning('请填写阈值')
    return
  }
  saving.value = true
  try {
    await alertsApi.create({
      ...draft,
      scope_type: 'hardware',
      scope_value: selectedHardwareId.value,
      rule_type: 'below_price',
      threshold,
      channel_target: channelTarget.value.trim(),
      cooldown_hours: 24,
    })
    ElMessage.success('已创建提醒')
    creatingVisible.value = false
    await loadAlerts()
  } catch {
    ElMessage.error('创建失败')
  } finally {
    saving.value = false
  }
}

async function toggleAlert(alert: PriceAlert) {
  await alertsApi.update(alert.id, { is_active: alert.is_active })
  ElMessage.success(alert.is_active ? '已启用' : '已暂停')
}

async function setAlertActive(alert: PriceAlert, active: boolean) {
  if (alert.is_active === active) return
  const previous = alert.is_active
  alert.is_active = active
  try {
    await toggleAlert(alert)
  } catch {
    alert.is_active = previous
    ElMessage.error('更新状态失败')
  }
}

function editAlert(alert: PriceAlert) {
  selectedHardwareId.value = alert.scope_value ?? ''
  minPriceText.value = alert.threshold ? String(alert.threshold) : ''
  draft.channel = alert.channel
  channelTarget.value = alert.channel_target
  saveTarget()
  creatingVisible.value = true
  ElMessage.info('已填入上方表单，可按需调整后创建新提醒')
}

async function deleteAlert(alert: PriceAlert) {
  await alertsApi.remove(alert.id)
  ElMessage.success('已删除')
  await loadAlerts()
}

function scopeText(alert: PriceAlert): string {
  if (alert.scope_type === 'all') return '全部对象'
  const item = hardwareOptions.value.find((option) => String(option.id) === alert.scope_value)
  return item?.name ?? `对象 ID：${alert.scope_value}`
}

function ruleText(alert: PriceAlert): string {
  if (alert.rule_type === 'below_price') return `低于最低值 ¥${alert.threshold}`
  if (alert.rule_type === 'below_median_pct') return `低于30天中位 ${alert.threshold}%`
  return '行情低位'
}

function formatPrice(price: number): string {
  return price >= 10000 ? `${(price / 10000).toFixed(1)}万` : Math.round(price).toLocaleString()
}

function formatDateTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${date.getFullYear()}/${String(date.getMonth() + 1).padStart(2, '0')}/${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}
</script>

<style scoped>
@import './ops-shared.css';

.target-box {
  display: flex;
  justify-content: flex-end;
}

.alert-list {
  border: 1px solid var(--paper-border);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: var(--paper-shadow);
}

.alert-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 18px;
  align-items: stretch;
}

.alert-grid :deep(.el-form-item) {
  margin-bottom: 0;
}

.alert-grid :deep(.el-select),
.alert-grid :deep(.el-input) {
  width: 100%;
}

.alert-action-slot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.alert-action-slot .el-button {
  height: 32px;
}

.alert-list {
  padding: 0;
  overflow: hidden;
}

.panel-head {
  padding: 18px 20px 14px;
  margin-bottom: 0;
}

.panel-head h2 {
  font-size: 18px;
  font-weight: 900;
  color: #101b31;
}

.panel-head span {
  display: block;
  margin-top: 3px;
  color: #7b8798;
  font-size: 12px;
}

.alert-table {
  border-top: 1px solid #e8edf4;
}

.alert-head,
.alert-row {
  display: grid;
  grid-template-columns: 96px minmax(210px, 1.1fr) minmax(190px, 1fr) minmax(190px, 0.9fr) minmax(160px, 0.8fr) minmax(190px, auto);
  gap: 18px;
  align-items: center;
}

.alert-head {
  height: 42px;
  padding: 0 20px;
  background: #f8fafc;
  color: #7a8799;
  font-size: 12px;
  font-weight: 900;
}

.alert-row {
  min-height: 104px;
  padding: 18px 20px;
  border-top: 1px solid #edf1f6;
  background: #ffffff;
}

.alert-row:hover {
  background: #fbfcff;
}

.alert-row.idle {
  color: #8a97aa;
}

.status-cell {
  display: flex;
  flex-direction: column;
  gap: 9px;
  align-items: flex-start;
}

.status-cell strong {
  color: #a3afbf;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.08em;
}

.status-cell strong::before {
  content: '';
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-right: 6px;
  border-radius: 999px;
  background: currentColor;
  vertical-align: 1px;
}

.status-cell strong.active {
  color: #16a56f;
}

.alert-object {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.alert-object h3 {
  min-width: 0;
  overflow: hidden;
  color: #101b31;
  font-size: 17px;
  font-weight: 950;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rule-cell,
.channel-cell,
.time-cell {
  min-width: 0;
}

.rule-cell strong,
.channel-cell strong,
.time-cell strong {
  display: block;
  overflow: hidden;
  color: #26364d;
  font-size: 15px;
  font-weight: 950;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rule-cell span,
.channel-cell span,
.time-cell span {
  display: block;
  margin-top: 6px;
  overflow: hidden;
  color: #8a97aa;
  font-size: 12px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.action-cell {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  align-items: center;
}

.action-cell :deep(.el-button) {
  margin-left: 0;
  font-weight: 900;
}

.run-toggle {
  width: 86px;
  height: 36px;
  border: 0;
  border-radius: 8px;
  background: #eef3f8;
  color: #8a97aa;
}

.run-toggle.danger {
  background: #ef4444;
  color: #ffffff;
  box-shadow: 0 8px 18px rgba(239, 68, 68, 0.2);
}

.run-toggle.danger:hover,
.run-toggle.danger:focus {
  background: #dc2626;
  color: #ffffff;
}

.icon-action {
  width: 32px;
  height: 32px;
  padding: 0;
  color: #93a2b7;
}

.icon-action:hover,
.icon-action:focus {
  color: #101b31;
  background: #f3f6fa;
}

@media (max-width: 1100px) {
  .alert-grid {
    grid-template-columns: 1fr;
  }

  .alert-head {
    display: none;
  }

  .alert-row {
    grid-template-columns: 1fr;
    gap: 14px;
  }

  .action-cell {
    justify-content: flex-start;
    flex-wrap: wrap;
  }
}

@media (max-width: 900px) {
  .target-box,
  .alert-grid {
    width: 100%;
    grid-template-columns: 1fr;
  }
}
</style>
