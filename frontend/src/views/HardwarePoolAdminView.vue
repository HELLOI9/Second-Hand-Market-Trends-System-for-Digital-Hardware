<template>
  <OpsLayout
    active-nav="hardware-admin"
  >
    <template #header>
      <header class="ops-header">
        <div class="ops-header-copy">
          <h1 class="ops-header-title"><el-icon><Setting /></el-icon>订阅管理</h1>
          <p class="ops-header-subtitle">维护监测对象、搜索关键词和启停状态，保证采集池始终干净可控。</p>
        </div>
        <div class="header-actions">
          <el-button type="danger" plain :icon="RefreshLeft" @click="confirmReset">重置数据库</el-button>
          <el-button type="primary" :icon="Plus" @click="creatingVisible = true">创建新订阅</el-button>
        </div>
      </header>
    </template>

      <el-dialog v-model="creatingVisible" title="新建订阅" width="620px">
        <el-form :model="draft" label-position="top" class="compose-grid">
          <el-form-item label="对象名称">
            <el-input v-model="draft.name" placeholder=" " />
          </el-form-item>
          <el-form-item label="搜索关键词">
            <el-input v-model="keywordText" placeholder="多个关键词用逗号隔开" />
          </el-form-item>
          <el-form-item label="筛选规则（选填）">
            <el-input
              v-model="draft.validation_rule"
              type="textarea"
              :rows="3"
              placeholder="针对本商品的特别筛选规则，会作为最高优先级约束加入 LLM 校验提示词。例如：只要带原包装盒的；排除矿卡；显存必须是 16G。"
            />
          </el-form-item>
          <div class="compose-action-slot">
            <el-button class="create-btn" type="primary" :icon="Plus" :loading="saving" @click="createItem">加入订阅</el-button>
          </div>
        </el-form>
      </el-dialog>

      <section class="table-panel">
        <div class="panel-head">
          <div class="panel-head-left">
            <el-checkbox
              :model-value="isAllSelected"
              :indeterminate="isIndeterminate"
              @change="toggleSelectAll"
            />
            <span v-if="selectedIds.size === 0">{{ items.length }} 个条目 · {{ activeCount }} 个启用</span>
            <span v-else>已选 {{ selectedIds.size }} 个</span>
          </div>
          <div class="panel-head-right">
            <template v-if="selectedIds.size > 0">
              <el-button size="small" @click="batchEnable">批量启用</el-button>
              <el-button size="small" @click="batchDisable">批量停用</el-button>
              <el-button size="small" type="danger" plain @click="batchDelete">批量删除</el-button>
            </template>
            <el-input v-model="query" class="search-input" clearable placeholder="搜索名称或关键词" />
          </div>
        </div>

        <div class="subscription-list">
          <div class="subscription-head">
            <span class="check-col"></span>
            <span>订阅详情</span>
            <span>关键词</span>
            <span>最新统计</span>
            <span>操作</span>
          </div>

          <article v-for="item in filteredItems" :key="item.id" class="subscription-row" :class="{ idle: !item.is_active, selected: selectedIds.has(item.id) }">
            <div class="check-col">
              <el-checkbox
                :model-value="selectedIds.has(item.id)"
                @change="(v: boolean) => toggleSelect(item.id, v)"
              />
            </div>

            <div class="detail-cell">
              <div class="item-title">
                <h3>{{ item.name }}</h3>
                <el-tag :type="item.is_active ? 'success' : 'info'" effect="light" round>
                  {{ item.is_active ? '监测中' : '已停用' }}
                </el-tag>
              </div>
            </div>

            <div class="keyword-cell">
              <el-tag v-for="word in item.search_keywords" :key="`${item.id}-${word}`" effect="plain">
                {{ word }}
              </el-tag>
            </div>

            <div class="stats-cell">
              <template v-if="item.latest_stats">
                <strong>{{ item.latest_stats.sample_count }} 件</strong>
                <span>最新一轮收集样本 · {{ item.latest_stats.stat_date }}</span>
              </template>
              <template v-else>
                <strong>-</strong>
                <span>暂无统计</span>
              </template>
            </div>

            <div class="action-cell">
              <el-switch
                :model-value="item.is_active"
                :loading="saving"
                @change="(value: string | number | boolean) => toggleItem(item, Boolean(value))"
              />
              <el-button class="icon-action" :icon="Edit" text title="编辑" @click="openEdit(item)" />
              <el-button class="icon-action" :icon="Delete" text title="删除" @click="disableItem(item)" />
            </div>
          </article>

          <el-empty v-if="!filteredItems.length" description="暂无订阅对象" />
        </div>
      </section>

      <el-dialog v-model="editingVisible" title="编辑对象" width="620px">
        <el-form :model="editDraft" label-position="top" class="compose-grid">
          <el-form-item label="对象名称">
            <el-input v-model="editDraft.name" />
          </el-form-item>
          <el-form-item label="搜索关键词">
            <el-input v-model="editKeywordText" />
          </el-form-item>
          <el-form-item label="筛选规则（选填）">
            <el-input
              v-model="editDraft.validation_rule"
              type="textarea"
              :rows="3"
              placeholder="针对本商品的特别筛选规则，会作为最高优先级约束加入 LLM 校验提示词。"
            />
          </el-form-item>
          <el-form-item label="状态">
            <el-switch v-model="editDraft.is_active" active-text="启用" inactive-text="停用" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="editingVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button>
        </template>
      </el-dialog>
  </OpsLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Plus, RefreshLeft, Setting } from '@element-plus/icons-vue'
import { crawlerApi, hardwareApi } from '@/api'
import type { CrawlerStatus, HardwareDetail } from '@/api/types'
import OpsLayout from '@/components/OpsLayout.vue'

const ADMIN_TOKEN = 'dev-admin-token'
const DEFAULT_CATEGORY = 'general'

const loading = ref(false)
const saving = ref(false)
const query = ref('')
const crawlerStatus = ref<CrawlerStatus | null>(null)
const items = ref<HardwareDetail[]>([])
const keywordText = ref('')
const editKeywordText = ref('')
const creatingVisible = ref(false)
const editingVisible = ref(false)
const editingId = ref<number | null>(null)

const draft = reactive({
  name: '',
  validation_rule: '',
})

const editDraft = reactive({
  name: '',
  validation_rule: '',
  is_active: true,
})

const activeCount = computed(() => items.value.filter((item) => item.is_active).length)
const filteredItems = computed(() => {
  const text = query.value.trim().toLowerCase()
  const source = text
    ? items.value.filter((item) => {
    return `${item.name} ${item.search_keywords.join(' ')}`.toLowerCase().includes(text)
  })
    : items.value
  return [...source].sort((a, b) => {
    if (a.is_active !== b.is_active) return a.is_active ? -1 : 1
    return a.id - b.id
  })
})

// ── 全选 / 批量 ────────────────────────────────
const selectedIds = ref<Set<number>>(new Set())

const isAllSelected = computed(() =>
  filteredItems.value.length > 0 && filteredItems.value.every((i) => selectedIds.value.has(i.id))
)
const isIndeterminate = computed(() =>
  filteredItems.value.some((i) => selectedIds.value.has(i.id)) && !isAllSelected.value
)

function toggleSelectAll(val: boolean) {
  if (val) {
    filteredItems.value.forEach((i) => selectedIds.value.add(i.id))
  } else {
    selectedIds.value.clear()
  }
  selectedIds.value = new Set(selectedIds.value)
}

function toggleSelect(id: number, val: boolean) {
  const next = new Set(selectedIds.value)
  if (val) next.add(id)
  else next.delete(id)
  selectedIds.value = next
}

async function batchEnable() {
  const targets = items.value.filter((i) => selectedIds.value.has(i.id) && !i.is_active)
  if (!targets.length) { ElMessage.info('所选条目均已启用'); return }
  saving.value = true
  await Promise.all(targets.map((i) => hardwareApi.restore(ADMIN_TOKEN, i.id)))
  selectedIds.value = new Set()
  await loadItems()
  ElMessage.success(`已启用 ${targets.length} 个`)
  saving.value = false
}

async function batchDisable() {
  const targets = items.value.filter((i) => selectedIds.value.has(i.id) && i.is_active)
  if (!targets.length) { ElMessage.info('所选条目均已停用'); return }
  saving.value = true
  await Promise.all(targets.map((i) => hardwareApi.remove(ADMIN_TOKEN, i.id)))
  selectedIds.value = new Set()
  await loadItems()
  ElMessage.success(`已停用 ${targets.length} 个`)
  saving.value = false
}

async function batchDelete() {
  const targets = items.value.filter((i) => selectedIds.value.has(i.id))
  if (!targets.length) return
  try {
    await ElMessageBox.confirm(`确认删除选中的 ${targets.length} 个条目？此操作不可撤销。`, '批量删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  saving.value = true
  await Promise.all(targets.map((i) => hardwareApi.remove(ADMIN_TOKEN, i.id)))
  selectedIds.value = new Set()
  await loadItems()
  ElMessage.success(`已删除 ${targets.length} 个`)
  saving.value = false
}

async function confirmReset() {
  try {
    await ElMessageBox.confirm(
      '此操作将清空所有价格快照、每日统计、采集记录，并按默认硬件池重建订阅列表。确认继续？',
      '重置数据库',
      {
        confirmButtonText: '确认重置',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger',
      },
    )
  } catch {
    return
  }
  saving.value = true
  try {
    const res = await hardwareApi.reset(ADMIN_TOKEN)
    ElMessage.success(`重置完成，已重建 ${res.inserted} 个硬件条目`)
    await loadItems()
  } catch {
    ElMessage.error('重置失败')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadItems(), loadCrawlerStatus()])
})

function parseKeywords(text: string, fallback: string): string[] {
  const words = text.split(/[,\n，]/).map((word) => word.trim()).filter(Boolean)
  return words.length ? words : [fallback]
}

async function loadItems() {
  loading.value = true
  try {
    items.value = await hardwareApi.adminList(ADMIN_TOKEN)
  } catch {
    ElMessage.error('加载订阅列表失败')
  } finally {
    loading.value = false
  }
}

async function loadCrawlerStatus() {
  try {
    crawlerStatus.value = await crawlerApi.status()
  } catch {
    crawlerStatus.value = null
  }
}

async function createItem() {
  if (!draft.name.trim()) {
    ElMessage.warning('请填写对象名称')
    return
  }
  saving.value = true
  try {
    await hardwareApi.create(ADMIN_TOKEN, {
      name: draft.name.trim(),
      category: DEFAULT_CATEGORY,
      search_keywords: parseKeywords(keywordText.value, draft.name.trim()),
      validation_rule: draft.validation_rule.trim() || null,
      cold_start: true,
    })
    ElMessage.success('已加入订阅')
    draft.name = ''
    draft.validation_rule = ''
    keywordText.value = ''
    creatingVisible.value = false
    await loadItems()
  } catch {
    ElMessage.error('新增失败')
  } finally {
    saving.value = false
  }
}

function openEdit(item: HardwareDetail) {
  editingId.value = item.id
  editDraft.name = item.name
  editDraft.is_active = item.is_active
  editDraft.validation_rule = item.validation_rule ?? ''
  editKeywordText.value = item.search_keywords.join(', ')
  editingVisible.value = true
}

async function saveEdit() {
  if (!editingId.value || !editDraft.name.trim()) return
  saving.value = true
  try {
    await hardwareApi.update(ADMIN_TOKEN, editingId.value, {
      name: editDraft.name.trim(),
      search_keywords: parseKeywords(editKeywordText.value, editDraft.name.trim()),
      validation_rule: editDraft.validation_rule.trim() || null,
      is_active: editDraft.is_active,
    })
    ElMessage.success('已保存')
    editingVisible.value = false
    await loadItems()
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function disableItem(item: HardwareDetail) {
  await hardwareApi.remove(ADMIN_TOKEN, item.id)
  ElMessage.success('已停用')
  await loadItems()
}

async function restoreItem(item: HardwareDetail) {
  await hardwareApi.restore(ADMIN_TOKEN, item.id)
  ElMessage.success('已恢复')
  await loadItems()
}

async function toggleItem(item: HardwareDetail, active: boolean) {
  if (active === item.is_active) return
  if (active) {
    await restoreItem(item)
  } else {
    await disableItem(item)
  }
}

async function crawlItem(item: HardwareDetail) {
  await hardwareApi.crawl(ADMIN_TOKEN, item.id)
  ElMessage.success(`已启动 ${item.name} 的单项采集`)
}

function formatPrice(price: number): string {
  return price >= 10000 ? `${(price / 10000).toFixed(1)}万` : Math.round(price).toLocaleString()
}
</script>

<style scoped>
.header-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.compose-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 18px;
  align-items: stretch;
}

.compose-grid :deep(.el-form-item) {
  margin-bottom: 0;
}

.compose-action-slot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.create-btn {
  height: 40px;
  padding: 0 18px;
  border-radius: var(--radius-control);
  font-weight: 900;
}

.table-panel {
  padding: 0;
  overflow: hidden;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 20px;
  margin-bottom: 0;
}

.panel-head-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.panel-head-left span {
  color: var(--paper-muted);
  font-size: 12px;
}

.panel-head-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.search-input {
  max-width: 320px;
}

.keyword-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.subscription-list {
  border-top: 1px solid var(--paper-border);
}

.subscription-head,
.subscription-row {
  display: grid;
  grid-template-columns: 40px minmax(200px, 1.2fr) minmax(200px, 1fr) minmax(160px, 0.8fr) 220px;
  gap: 18px;
  align-items: center;
}

.check-col {
  display: flex;
  align-items: center;
  justify-content: center;
}

.subscription-head {
  height: 42px;
  padding: 0 20px;
  background: var(--paper-surface-soft);
  color: var(--paper-muted);
  font-size: 12px;
  font-weight: 900;
}

.subscription-head span:last-child {
  display: flex;
  justify-content: center;
  width: 100%;
  text-align: center;
}

.subscription-row {
  min-height: 104px;
  padding: 18px 20px;
  border-top: 1px solid var(--paper-border);
  background: var(--surface-floating);
}

.subscription-row.selected {
  background: var(--paper-surface-soft);
}

.subscription-row.selected:hover {
  background: var(--surface-soft-hover);
}



.subscription-row.idle {
  color: var(--paper-subtle);
}

.detail-cell {
  min-width: 0;
}

.item-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.item-title h3 {
  min-width: 0;
  overflow: hidden;
  color: var(--text-strong);
  font-size: 17px;
  font-weight: 950;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-subline {
  display: block;
  margin-top: 8px;
  color: var(--paper-subtle);
  font-size: 12px;
  font-weight: 800;
}

.keyword-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  min-width: 0;
}

.keyword-cell :deep(.el-tag) {
  max-width: 100%;
  border-color: var(--paper-border);
  background: var(--paper-surface-soft);
  color: var(--paper-muted);
  font-weight: 800;
}

.stats-cell {
  min-width: 0;
}

.stats-cell strong {
  display: block;
  color: var(--text-strong);
  font-size: 16px;
  font-weight: 950;
}

.stats-cell span {
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

@media (max-width: 900px) {
  .ops-header,
  .panel-head {
    flex-direction: column;
    align-items: stretch;
  }

  .header-actions,
  .search-input {
    width: 100%;
    max-width: none;
  }

  .compose-grid {
    grid-template-columns: 1fr;
  }

  .subscription-head {
    display: none;
  }

  .subscription-row {
    grid-template-columns: 40px 1fr;
    gap: 14px;
  }

  .subscription-row .keyword-cell,
  .subscription-row .stats-cell {
    grid-column: 2;
  }

  .subscription-row .action-cell {
    grid-column: 2;
    justify-content: center;
  }
}
</style>
