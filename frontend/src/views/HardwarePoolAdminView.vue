<template>
  <OpsLayout
    active-nav="hardware-admin"
    system-primary="后端实时已连接"
    :system-secondary="crawlerStatus?.last_run_date ? `更新于 ${crawlerStatus.last_run_date}` : '等待首次更新'"
  >
    <template #header>
      <header class="ops-header">
        <div class="ops-header-copy">
          <h1 class="ops-header-title"><el-icon><Setting /></el-icon>订阅管理</h1>
          <p class="ops-header-subtitle">维护监测对象、搜索关键词和启停状态，保证采集池始终干净可控。</p>
        </div>
        <div class="header-actions">
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
          <div class="compose-action-slot">
            <el-button class="create-btn" type="primary" :icon="Plus" :loading="saving" @click="createItem">加入订阅</el-button>
          </div>
        </el-form>
      </el-dialog>

      <section class="table-panel">
        <div class="panel-head">
          <span>{{ items.length }} 个条目 · {{ activeCount }} 个启用</span>
          <el-input v-model="query" class="search-input" clearable placeholder="搜索名称或关键词" />
        </div>

        <div class="subscription-list">
          <div class="subscription-head">
            <span>订阅详情</span>
            <span>关键词</span>
            <span>最新统计</span>
            <span>操作</span>
          </div>

          <article v-for="item in filteredItems" :key="item.id" class="subscription-row" :class="{ idle: !item.is_active }">
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
import { ElMessage } from 'element-plus'
import { Delete, Edit, Plus, Setting } from '@element-plus/icons-vue'
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
})

const editDraft = reactive({
  name: '',
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
      cold_start: true,
    })
    ElMessage.success('已加入订阅')
    draft.name = ''
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
  padding: 18px 20px 14px;
  margin-bottom: 0;
}

.panel-head span {
  display: block;
  color: var(--paper-muted);
  font-size: 12px;
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
  grid-template-columns: minmax(220px, 1.2fr) minmax(220px, 1fr) minmax(170px, 0.8fr) minmax(190px, auto);
  gap: 18px;
  align-items: center;
}

.subscription-head {
  height: 42px;
  padding: 0 20px;
  background: var(--paper-surface-soft);
  color: var(--paper-muted);
  font-size: 12px;
  font-weight: 900;
}

.subscription-row {
  min-height: 104px;
  padding: 18px 20px;
  border-top: 1px solid var(--paper-border);
  background: var(--surface-floating);
}

.subscription-row:hover {
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
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
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
    grid-template-columns: 1fr;
    gap: 14px;
  }

  .action-cell {
    justify-content: flex-start;
    flex-wrap: wrap;
  }
}
</style>
