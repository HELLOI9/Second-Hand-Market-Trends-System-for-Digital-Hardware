<template>
  <OpsLayout
    active-nav="alerts"
  >
    <template #header>
      <header class="ops-header">
        <div class="ops-header-copy">
          <h1 class="ops-header-title"><el-icon><Bell /></el-icon>价格提醒</h1>
          <p class="ops-header-subtitle">统一管理价格阈值、邮箱地址和最近触发状态。</p>
        </div>
        <div class="target-box">
          <el-button type="primary" :icon="Plus" @click="openCreateDialog">创建新提醒</el-button>
        </div>
      </header>
    </template>

      <el-dialog
        v-model="creatingVisible"
        title="创建新提醒"
        width="620px"
        class="alert-create-dialog"
        modal-class="alert-create-overlay"
        transition=""
      >
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
          <el-form-item label="邮箱地址">
            <el-input v-model="channelTarget" placeholder="收件邮箱，例如 name@example.com" />
          </el-form-item>
          <div class="alert-action-slot">
            <el-button type="primary" :icon="Plus" :loading="saving" @click="createAlert">创建提醒</el-button>
          </div>
        </el-form>
      </el-dialog>

      <section class="alert-list">
        <div class="panel-head">
          <span>{{ alerts.length }} 条订阅 · {{ activeCount }} 条启用</span>
        </div>

        <div class="alert-table">
          <div class="alert-head">
            <span>提醒对象</span>
            <span>规则</span>
            <span>通道</span>
            <span>最近触发</span>
            <span>操作</span>
          </div>

          <article v-for="alert in sortedAlerts" :key="alert.id" class="alert-row" :class="{ idle: !alert.is_active }">
            <div class="alert-object">
              <h3>{{ scopeText(alert) }}</h3>
              <el-tag :type="alert.is_active ? 'success' : 'info'" effect="light" round>
                {{ alert.is_active ? '提醒中' : '已暂停' }}
              </el-tag>
            </div>

            <div class="rule-cell">
              <strong>{{ ruleText(alert) }}</strong>
              <span>今日最低价低于阈值时提醒</span>
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
              <el-switch
                :model-value="alert.is_active"
                @change="(value: string | number | boolean) => setAlertActive(alert, Boolean(value))"
              />
              <el-button class="icon-action" :icon="Edit" text title="编辑" @click="editAlert(alert)" />
              <el-button class="icon-action" :icon="Delete" text title="删除" @click="deleteAlert(alert)" />
            </div>
          </article>

          <el-empty v-if="!alerts.length" description="暂无提醒" />
        </div>
      </section>
  </OpsLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Bell, Delete, Edit, Plus } from '@element-plus/icons-vue'
import { alertsApi, crawlerApi, hardwareApi } from '@/api'
import type { AlertPayload, CrawlerStatus, HardwareDetail, PriceAlert } from '@/api/types'
import OpsLayout from '@/components/OpsLayout.vue'

const route = useRoute()
const channelTarget = ref('')
const alerts = ref<PriceAlert[]>([])
const allHardwareOptions = ref<HardwareDetail[]>([])
const hardwareOptions = ref<HardwareDetail[]>([])
const loading = ref(false)
const saving = ref(false)
const crawlerStatus = ref<CrawlerStatus | null>(null)
const selectedHardwareId = ref(typeof route.query.hardwareId === 'string' ? route.query.hardwareId : '')
const minPriceText = ref('')
const isCreateRoute = route.query.mode === 'create'
const creatingVisible = ref(isCreateRoute)
const consumedCreateQuery = ref(false)

const draft = reactive<AlertPayload>({
  scope_type: 'hardware',
  scope_value: selectedHardwareId.value,
  rule_type: 'below_price',
  threshold: null,
  channel: 'email',
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
  void initPage()
})

async function initPage() {
  prepareCreateDialogFromQuery()
  await loadHardwareOptions()
  await Promise.all([loadCrawlerStatus(), loadAlerts()])
  completeCreateDialogFromQuery()
}

async function loadHardwareOptions() {
  try {
    const items = await hardwareApi.adminList('dev-admin-token')
    allHardwareOptions.value = items
    hardwareOptions.value = items.filter((item) => item.is_active)
  } catch {
    ElMessage.error('加载订阅商品失败')
  }
}

function prepareCreateDialogFromQuery() {
  if (consumedCreateQuery.value || route.query.mode !== 'create') return
  consumedCreateQuery.value = true

  const hardwareId = typeof route.query.hardwareId === 'string' ? route.query.hardwareId : ''
  if (hardwareId) {
    selectedHardwareId.value = hardwareId
  }

  const median = selectedHardware.value?.latest_stats?.median_price
  minPriceText.value = median ? String(Math.round(median)) : ''
  draft.channel = 'email'
  channelTarget.value = ''
  draft.channel_target = ''

  const cleanUrl = hardwareId ? `/alerts?hardwareId=${encodeURIComponent(hardwareId)}` : '/alerts'
  window.history.replaceState(window.history.state, '', cleanUrl)

  creatingVisible.value = true
}

function completeCreateDialogFromQuery() {
  if (!isCreateRoute) return
  const median = selectedHardware.value?.latest_stats?.median_price
  if (!minPriceText.value && median) {
    minPriceText.value = String(Math.round(median))
  }
}

function openCreateDialog() {
  selectedHardwareId.value = ''
  minPriceText.value = ''
  draft.channel = 'email'
  channelTarget.value = ''
  draft.channel_target = ''
  creatingVisible.value = true
}

async function loadCrawlerStatus() {
  try {
    crawlerStatus.value = await crawlerApi.status()
  } catch {
    crawlerStatus.value = null
  }
}

function validateEmailTarget(target: string): string | null {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(target) ? null : '请填写有效邮箱地址'
}

async function loadAlerts() {
  loading.value = true
  try {
    alerts.value = await alertsApi.list()
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
  const targetError = validateEmailTarget(channelTarget.value.trim())
  if (targetError) {
    ElMessage.warning(targetError)
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
      channel: 'email',
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
  const item = allHardwareOptions.value.find((option) => String(option.id) === alert.scope_value)
  return item?.name ?? `对象 ID：${alert.scope_value}`
}

function ruleText(alert: PriceAlert): string {
  if (alert.rule_type === 'below_price') return `低于价格阈值 ¥${alert.threshold}`
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
.target-box {
  display: flex;
  justify-content: flex-end;
}

.alert-list {
  border: 1px solid var(--paper-border);
  border-radius: var(--radius-card);
  background: var(--surface-floating);
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

.panel-head span {
  display: block;
  color: var(--paper-muted);
  font-size: 12px;
}

.alert-table {
  border-top: 1px solid var(--paper-border);
}

.alert-head,
.alert-row {
  display: grid;
  grid-template-columns: minmax(210px, 1.15fr) minmax(190px, 1fr) minmax(190px, 0.9fr) minmax(160px, 0.8fr) 220px;
  gap: 18px;
  align-items: center;
}

.alert-head {
  height: 42px;
  padding: 0 20px;
  background: var(--paper-surface-soft);
  color: var(--paper-muted);
  font-size: 12px;
  font-weight: 900;
}

.alert-head span:last-child {
  display: flex;
  justify-content: center;
  width: 100%;
  text-align: center;
}

.alert-row {
  min-height: 104px;
  padding: 18px 20px;
  border-top: 1px solid var(--paper-border);
  background: var(--surface-floating);
}

.alert-row:hover {
  background: var(--surface-soft-hover);
}

.alert-row.idle {
  color: var(--paper-subtle);
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
  color: var(--text-strong);
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
  color: var(--text-strong);
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
  color: var(--paper-subtle);
  font-size: 12px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.action-cell {
  display: grid;
  grid-template-columns: 40px 32px 32px;
  justify-content: center;
  gap: 12px;
  align-items: center;
  flex-wrap: nowrap;
}

.action-cell :deep(.el-button) {
  margin-left: 0;
  font-weight: 900;
}

.run-toggle {
  width: 86px;
  height: 36px;
  border: 0;
  border-radius: var(--radius-control);
  background: var(--paper-surface-soft);
  color: var(--paper-subtle);
}

.run-toggle.danger {
  background: #ef4444;
  color: #ffffff;
  box-shadow: var(--shadow-control);
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
  color: var(--paper-subtle);
}

.icon-action:hover,
.icon-action:focus {
  color: var(--text-strong);
  background: var(--paper-surface-soft);
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
    justify-content: center;
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

<style>
.alert-create-dialog {
  background: #ffffff;
  opacity: 1 !important;
}

.alert-create-overlay {
  background-color: rgba(0, 0, 0, 0.5) !important;
}

.alert-create-overlay .el-dialog,
.alert-create-overlay .el-dialog__body,
.alert-create-overlay .el-form {
  opacity: 1 !important;
}
</style>
