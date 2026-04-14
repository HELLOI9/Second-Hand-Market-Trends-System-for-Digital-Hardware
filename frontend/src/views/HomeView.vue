<template>
  <div class="home">
    <div class="page-glow" aria-hidden="true"></div>

    <header class="hero">
      <div class="hero-inner">
        <div class="hero-title-wrap">
          <p class="hero-eyebrow">SECOND-HAND MARKET PULSE</p>
          <h1 class="hero-title">
            <el-icon><Monitor /></el-icon>
            数码硬件二手行情
          </h1>
          <p class="hero-subtitle">固定硬件池 · 每日聚合 · 实时趋势观测</p>
        </div>

        <div class="hero-status">
          <span class="status-kicker">{{ displayMode === 'heatmap' ? '总览视图' : '当前栏目' }}</span>
          <strong v-if="displayMode !== 'heatmap'" class="status-value">{{ activeCategoryLabel }}</strong>
          <span class="status-update" v-if="crawlerStatus?.last_run_date">
            数据更新于 {{ crawlerStatus.last_run_date }}
          </span>
          <span class="status-update" v-else>暂无更新记录</span>
        </div>
      </div>
    </header>

    <main class="content">
      <section class="view-switch-wrap">
        <el-radio-group v-model="displayMode" size="small">
          <el-radio-button label="heatmap" value="heatmap">热力矩阵视图</el-radio-button>
          <el-radio-button label="table" value="table">表格趋势视图</el-radio-button>
          <el-radio-button label="cards" value="cards">卡片视图</el-radio-button>
        </el-radio-group>
      </section>

      <template v-if="loading">
        <div class="loading-wrap">
          <el-skeleton :rows="8" animated />
        </div>
      </template>

      <template v-else-if="displayMode === 'heatmap'">
        <section class="insights-grid">
          <el-card class="insight-card" shadow="never">
            <template #header>
              <div class="insight-title">样本活跃榜</div>
            </template>
            <ol class="rank-list" v-if="sampleRanking.length">
              <li class="rank-item" v-for="item in sampleRanking" :key="`sample-${item.id}`" @click="goToDetail(item.id, item.category)">
                <span class="rank-name">{{ item.name }}</span>
                <span class="rank-value">{{ item.latest_stats?.sample_count ?? 0 }} 件</span>
              </li>
            </ol>
            <el-empty v-else description="暂无数据" />
          </el-card>

          <el-card class="insight-card" shadow="never">
            <template #header>
              <div class="insight-title">高价位榜</div>
            </template>
            <ol class="rank-list" v-if="priceRanking.length">
              <li class="rank-item" v-for="item in priceRanking" :key="`price-${item.id}`" @click="goToDetail(item.id, item.category)">
                <span class="rank-name">{{ item.name }}</span>
                <span class="rank-value">¥{{ formatPrice(item.latest_stats?.median_price ?? 0) }}</span>
              </li>
            </ol>
            <el-empty v-else description="暂无数据" />
          </el-card>

          <el-card class="insight-card" shadow="never">
            <template #header>
              <div class="insight-title">低位机会榜</div>
            </template>
            <ol class="rank-list" v-if="opportunityRanking.length">
              <li class="rank-item" v-for="item in opportunityRanking" :key="`opp-${item.id}`" @click="goToDetail(item.id, item.category)">
                <span class="rank-name">{{ item.name }}</span>
                <span class="rank-value">{{ item.latest_stats?.sample_count ?? 0 }} 件</span>
              </li>
            </ol>
            <el-empty v-else description="暂无低位标记数据" />
          </el-card>
        </section>

        <section class="heatmap-board">
          <div class="heatmap-head">
            <h3>市场热力矩阵</h3>
            <p>颜色表示行情状态，深浅表示当日样本活跃度。点击单元格可进入详情。</p>
          </div>

          <div class="heat-legend" aria-label="热力图图例">
            <span class="legend-item"><i class="legend-dot low"></i>低位</span>
            <span class="legend-item"><i class="legend-dot normal"></i>正常</span>
            <span class="legend-item"><i class="legend-dot high"></i>偏高</span>
            <span class="legend-item"><i class="legend-dot none"></i>无数据</span>
          </div>

          <div class="heatmap-table">
            <div class="heatmap-row" v-for="row in heatmapRows" :key="row.value">
              <div class="row-label">{{ row.label }}</div>
              <div class="row-cells">
                <button
                  v-for="item in row.items"
                  :key="item.id"
                  class="heat-cell"
                  :class="`level-${heatLevel(item)}`"
                  :style="heatStyle(item)"
                  @click="goToDetail(item.id, item.category)"
                >
                  <span class="cell-top">
                    <span class="cell-name">{{ item.name }}</span>
                    <span
                      v-if="isSpecialHeatLevel(item)"
                      class="cell-level"
                      :class="`badge-${heatLevel(item)}`"
                    >
                      {{ specialHeatLabel(item) }}
                    </span>
                  </span>
                  <span class="cell-value" v-if="item.latest_stats">¥{{ formatPrice(item.latest_stats.median_price) }}</span>
                  <span class="cell-value muted" v-else>无数据</span>
                </button>
              </div>
            </div>
          </div>
        </section>
      </template>

      <template v-else-if="displayMode === 'table'">
        <section class="table-view">
          <el-tabs v-model="activeCategory" class="category-tabs table-tabs">
            <el-tab-pane v-for="cat in CATEGORY_LABELS" :key="`table-${cat.value}`" :label="cat.label" :name="cat.value">
              <el-table :data="groupedHardware[cat.value] || []" class="market-table" stripe>
                <el-table-column prop="name" label="硬件" min-width="180" />

                <el-table-column label="中位价" width="130">
                  <template #default="{ row }">
                    <span v-if="row.latest_stats">¥{{ formatPrice(row.latest_stats.median_price) }}</span>
                    <span v-else class="muted-cell">-</span>
                  </template>
                </el-table-column>

                <el-table-column label="价格区间" min-width="180">
                  <template #default="{ row }">
                    <span v-if="row.latest_stats">
                      ¥{{ formatPrice(row.latest_stats.min_price) }} - ¥{{ formatPrice(row.latest_stats.max_price) }}
                    </span>
                    <span v-else class="muted-cell">-</span>
                  </template>
                </el-table-column>

                <el-table-column label="样本数" width="90">
                  <template #default="{ row }">
                    <span v-if="row.latest_stats">{{ row.latest_stats.sample_count }}</span>
                    <span v-else class="muted-cell">-</span>
                  </template>
                </el-table-column>

                <el-table-column label="状态" width="90">
                  <template #default="{ row }">
                    <span class="level-chip" :class="`chip-${heatLevel(row)}`">
                      {{ HEAT_LEVEL_LABELS[heatLevel(row)] }}
                    </span>
                  </template>
                </el-table-column>

                <el-table-column label="趋势(30天)" min-width="220">
                  <template #default="{ row }">
                    <MiniTrendSparkline
                      :points="trendCache[row.id] ?? []"
                      :loading="Boolean(trendLoadingMap[row.id])"
                      :level="heatLevel(row)"
                    />
                  </template>
                </el-table-column>

                <el-table-column label="详情" width="88" fixed="right">
                  <template #default="{ row }">
                    <el-button link type="primary" @click="goToDetail(row.id, cat.value)">查看</el-button>
                  </template>
                </el-table-column>
              </el-table>
              <el-empty v-if="!(groupedHardware[cat.value]?.length)" description="暂无数据" />
            </el-tab-pane>
          </el-tabs>
        </section>
      </template>

      <template v-else>
        <section class="card-view">
          <el-tabs v-model="activeCategory" class="category-tabs">
            <el-tab-pane v-for="cat in CATEGORY_LABELS" :key="cat.value" :label="cat.label" :name="cat.value">
              <div class="card-grid">
                <HardwareCard
                  v-for="item in groupedHardware[cat.value] || []"
                  :key="item.id"
                  :item="item"
                  @click="goToDetail(item.id, cat.value)"
                />
              </div>
              <el-empty v-if="!(groupedHardware[cat.value]?.length)" description="暂无数据" />
            </el-tab-pane>
          </el-tabs>
        </section>
      </template>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { hardwareApi, crawlerApi } from '@/api'
import type { HardwareDetail, CrawlerStatus } from '@/api/types'
import HardwareCard from '@/components/HardwareCard.vue'
import MiniTrendSparkline from '@/components/MiniTrendSparkline.vue'

const CATEGORY_LABELS = [
  { value: 'cpu', label: 'CPU' },
  { value: 'gpu', label: '显卡' },
  { value: 'memory', label: '内存' },
  { value: 'ssd', label: '固态硬盘' },
] as const

type CategoryValue = (typeof CATEGORY_LABELS)[number]['value']
type ViewMode = 'heatmap' | 'table' | 'cards'
type HeatLevel = 'low' | 'normal' | 'high' | 'none'

const VALID_CATEGORIES = new Set<CategoryValue>(CATEGORY_LABELS.map((item) => item.value))
const HEAT_LEVEL_LABELS: Record<HeatLevel, string> = {
  low: '低位',
  normal: '正常',
  high: '偏高',
  none: '无数据',
}

function pickQueryString(value: unknown): string | undefined {
  if (Array.isArray(value)) {
    return typeof value[0] === 'string' ? value[0] : undefined
  }
  return typeof value === 'string' ? value : undefined
}

function normalizeCategory(value: unknown): CategoryValue {
  const maybe = pickQueryString(value)
  if (maybe && VALID_CATEGORIES.has(maybe as CategoryValue)) {
    return maybe as CategoryValue
  }
  return 'cpu'
}

function normalizeView(value: unknown): ViewMode {
  const maybe = pickQueryString(value)
  return maybe === 'cards' || maybe === 'table' ? maybe : 'heatmap'
}

const router = useRouter()
const route = useRoute()

const loading = ref(true)
const activeCategory = ref<CategoryValue>(normalizeCategory(route.query.category))
const displayMode = ref<ViewMode>(normalizeView(route.query.view))
const groupedHardware = ref<Record<string, HardwareDetail[]>>({})
const crawlerStatus = ref<CrawlerStatus | null>(null)
const trendCache = ref<Record<number, number[]>>({})
const trendLoadingMap = ref<Record<number, boolean>>({})
const trendInFlight = new Set<number>()

const activeCategoryLabel = computed(() => {
  return CATEGORY_LABELS.find((item) => item.value === activeCategory.value)?.label ?? 'CPU'
})

const heatmapRows = computed(() => {
  return CATEGORY_LABELS.map((cat) => ({
    ...cat,
    items: groupedHardware.value[cat.value] ?? [],
  }))
})

const hardwareWithStats = computed(() => {
  return Object.values(groupedHardware.value)
    .flat()
    .filter((item) => item.latest_stats)
})

const maxSampleCount = computed(() => {
  const counts = hardwareWithStats.value.map((item) => item.latest_stats?.sample_count ?? 0)
  return counts.length ? Math.max(...counts) : 1
})

const sampleRanking = computed(() => {
  return [...hardwareWithStats.value]
    .sort((a, b) => (b.latest_stats?.sample_count ?? 0) - (a.latest_stats?.sample_count ?? 0))
    .slice(0, 8)
})

const priceRanking = computed(() => {
  return [...hardwareWithStats.value]
    .sort((a, b) => (b.latest_stats?.median_price ?? 0) - (a.latest_stats?.median_price ?? 0))
    .slice(0, 8)
})

const opportunityRanking = computed(() => {
  return [...hardwareWithStats.value]
    .filter((item) => item.latest_stats?.price_level === 'low')
    .sort((a, b) => (b.latest_stats?.sample_count ?? 0) - (a.latest_stats?.sample_count ?? 0))
    .slice(0, 8)
})

watch(
  [displayMode, activeCategory, groupedHardware],
  () => {
    if (displayMode.value === 'table') {
      void ensureTrendsForCategory(activeCategory.value)
    }
  },
  { immediate: true },
)

watch(
  () => route.query.category,
  (nextCategory) => {
    const normalized = normalizeCategory(nextCategory)
    if (normalized !== activeCategory.value) {
      activeCategory.value = normalized
    }
  },
)

watch(
  () => route.query.view,
  (nextView) => {
    const normalized = normalizeView(nextView)
    if (normalized !== displayMode.value) {
      displayMode.value = normalized
    }
  },
)

watch(activeCategory, (nextCategory) => {
  if (normalizeCategory(route.query.category) === nextCategory) {
    return
  }
  router.replace({
    name: 'home',
    query: {
      ...route.query,
      category: nextCategory,
      view: displayMode.value,
    },
  })
})

watch(displayMode, (nextView) => {
  if (normalizeView(route.query.view) === nextView) {
    return
  }
  router.replace({
    name: 'home',
    query: {
      ...route.query,
      category: activeCategory.value,
      view: nextView,
    },
  })
})

onMounted(async () => {
  try {
    const [hardware, status] = await Promise.all([hardwareApi.list(), crawlerApi.status()])
    groupedHardware.value = hardware
    crawlerStatus.value = status
  } catch {
    ElMessage.error('加载数据失败，请检查后端服务')
  } finally {
    loading.value = false
  }
})

function formatPrice(price: number): string {
  return price >= 10000 ? `${(price / 10000).toFixed(1)}万` : Math.round(price).toLocaleString()
}

function heatLevel(item: HardwareDetail): HeatLevel {
  if (!item.latest_stats) return 'none'
  return item.latest_stats.price_level
}

function isSpecialHeatLevel(item: HardwareDetail): boolean {
  const level = heatLevel(item)
  return level === 'low' || level === 'high' || level === 'none'
}

function specialHeatLabel(item: HardwareDetail): string {
  const level = heatLevel(item)
  return HEAT_LEVEL_LABELS[level]
}

async function loadTrendForHardware(hardwareId: number): Promise<void> {
  if (trendCache.value[hardwareId] !== undefined || trendInFlight.has(hardwareId)) {
    return
  }

  trendInFlight.add(hardwareId)
  trendLoadingMap.value = { ...trendLoadingMap.value, [hardwareId]: true }

  try {
    const trend = await hardwareApi.trend(hardwareId, 30)
    trendCache.value = {
      ...trendCache.value,
      [hardwareId]: trend.trend.map((point) => point.median_price),
    }
  } catch {
    trendCache.value = {
      ...trendCache.value,
      [hardwareId]: [],
    }
  } finally {
    trendInFlight.delete(hardwareId)
    const { [hardwareId]: _removed, ...rest } = trendLoadingMap.value
    trendLoadingMap.value = rest
  }
}

async function ensureTrendsForCategory(category: CategoryValue): Promise<void> {
  const idsToLoad = (groupedHardware.value[category] ?? [])
    .filter((item) => item.latest_stats)
    .map((item) => item.id)
    .filter((id) => trendCache.value[id] === undefined && !trendInFlight.has(id))

  if (!idsToLoad.length) return

  const queue = [...idsToLoad]
  const concurrency = 4
  const workers = Array.from({ length: Math.min(concurrency, queue.length) }, async () => {
    while (queue.length) {
      const id = queue.shift()
      if (id === undefined) return
      await loadTrendForHardware(id)
    }
  })

  await Promise.all(workers)
}

function heatStyle(item: HardwareDetail): Record<string, string> {
  if (!item.latest_stats) {
    return {
      backgroundColor: 'rgba(214, 217, 223, 0.35)',
      borderColor: 'rgba(193, 200, 209, 0.8)',
      color: '#536170',
    }
  }

  const ratio = Math.max(0, Math.min(1, item.latest_stats.sample_count / maxSampleCount.value))
  const alpha = 0.32 + ratio * 0.62

  const colorMap: Record<'low' | 'normal' | 'high', {
    rgb: [number, number, number]
    textColor: string
  }> = {
    low: {
      rgb: [72, 160, 120],
      textColor: '#eefaf4',
    },
    normal: {
      rgb: [61, 112, 184],
      textColor: '#f3f8ff',
    },
    high: {
      rgb: [108, 83, 170],
      textColor: '#f7f2ff',
    },
  }

  const level = heatLevel(item)
  const { rgb, textColor } = colorMap[level as 'low' | 'normal' | 'high']
  const [r, g, b] = rgb

  return {
    backgroundColor: `rgba(${r}, ${g}, ${b}, ${alpha.toFixed(3)})`,
    borderColor: `rgba(${r}, ${g}, ${b}, 0.96)`,
    color: textColor,
  }
}

function goToDetail(id: number, category?: string) {
  const normalizedCategory = category && VALID_CATEGORIES.has(category as CategoryValue)
    ? (category as CategoryValue)
    : activeCategory.value

  router.push({
    name: 'hardware-detail',
    params: { id },
    query: {
      fromCategory: normalizedCategory,
      fromView: displayMode.value,
    },
  })
}
</script>

<style scoped>
.home {
  position: relative;
  min-height: 100vh;
  padding: 28px 22px 36px;
}

.page-glow {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(circle at 14% 0%, var(--v-soft-1) 0%, transparent 44%),
    radial-gradient(circle at 84% 20%, var(--v-soft-2) 0%, transparent 38%);
}

.hero,
.content {
  position: relative;
  z-index: 1;
}

.hero {
  max-width: 1280px;
  margin: 0 auto 16px;
}

.hero-inner {
  background: linear-gradient(132deg, #2f4b7c 0%, #355f8d 56%, #2a788e 100%);
  border: 1px solid rgba(202, 218, 235, 0.62);
  border-radius: 24px;
  padding: 26px 28px;
  box-shadow: var(--paper-shadow);
  color: #f5f7fb;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 22px;
}

.hero-eyebrow {
  letter-spacing: 0.18em;
  font-size: 11px;
  font-weight: 700;
  color: rgba(239, 244, 249, 0.88);
  margin-bottom: 10px;
}

.hero-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: clamp(24px, 2.2vw, 34px);
  line-height: 1.2;
  font-weight: 700;
}

.hero-subtitle {
  margin-top: 10px;
  color: rgba(233, 240, 248, 0.9);
  font-size: 14px;
}

.hero-status {
  min-width: 220px;
  border-radius: 18px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(224, 232, 240, 0.42);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.status-kicker {
  font-size: 12px;
  color: rgba(238, 244, 250, 0.88);
}

.status-value {
  font-size: 24px;
  line-height: 1.1;
  font-weight: 700;
}

.status-update {
  font-size: 12px;
  color: rgba(238, 244, 250, 0.92);
}

.content {
  max-width: 1280px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.view-switch-wrap {
  display: flex;
  justify-content: flex-end;
}

.view-switch-wrap :deep(.el-radio-group) {
  padding: 0;
  border-radius: 0;
  background: transparent;
  border: none;
}

.loading-wrap {
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid var(--paper-border);
  border-radius: 18px;
  padding: 16px;
}

.insights-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.insight-card {
  border: 1px solid var(--paper-border);
  border-radius: 14px;
  background: var(--paper-surface);
  box-shadow: 0 8px 18px rgba(31, 41, 55, 0.07);
}

.insight-card :deep(.el-card__header) {
  padding: 12px 14px;
}

.insight-card :deep(.el-card__body) {
  padding: 10px 14px 14px;
}

.insight-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--paper-text);
}

.rank-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rank-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 10px;
  background: var(--paper-surface-soft);
  border: 1px solid var(--paper-border);
  cursor: pointer;
  transition: background-color 0.18s ease;
}

.rank-item:hover {
  background: rgba(65, 68, 135, 0.12);
}

.rank-name {
  color: var(--paper-text);
  font-size: 13px;
  font-weight: 600;
}

.rank-value {
  color: var(--paper-muted);
  font-size: 12px;
  font-weight: 700;
}

.heatmap-board {
  border: 1px solid var(--paper-border);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: var(--paper-shadow);
  padding: 14px;
}

.heatmap-head h3 {
  font-size: 16px;
  color: var(--paper-text);
  margin-bottom: 4px;
}

.heatmap-head p {
  font-size: 12px;
  color: var(--paper-muted);
}

.heat-legend {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px 14px;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--paper-muted);
  font-weight: 600;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  display: inline-block;
  border: 1px solid transparent;
}

.legend-dot.low {
  background: rgba(72, 160, 120, 0.9);
  border-color: rgba(46, 124, 89, 0.95);
}

.legend-dot.normal {
  background: rgba(61, 112, 184, 0.9);
  border-color: rgba(40, 85, 147, 0.95);
}

.legend-dot.high {
  background: rgba(108, 83, 170, 0.9);
  border-color: rgba(76, 54, 131, 0.95);
}

.legend-dot.none {
  background: rgba(214, 217, 223, 0.95);
  border-color: rgba(170, 176, 186, 0.95);
}

.heatmap-table {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.heatmap-row {
  display: grid;
  grid-template-columns: 76px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
}

.row-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--paper-muted);
  padding-top: 6px;
}

.row-cells {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(148px, 1fr));
  gap: 8px;
}

.heat-cell {
  border: 1px solid transparent;
  border-radius: 10px;
  padding: 10px;
  text-align: left;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.heat-cell:hover {
  transform: translateY(-2px);
}

.cell-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.cell-name {
  display: block;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.3;
}

.cell-level {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
  padding: 4px 6px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.35);
  background: rgba(255, 255, 255, 0.2);
}

.badge-low,
.badge-normal,
.badge-high {
  color: rgba(255, 255, 255, 0.96);
}

.badge-none {
  color: var(--paper-muted);
  border-color: rgba(83, 97, 112, 0.25);
  background: rgba(83, 97, 112, 0.12);
}

.cell-value {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  font-weight: 600;
  opacity: 0.96;
}

.cell-value.muted {
  opacity: 0.78;
}

.level-none {
  color: var(--paper-muted);
}

.table-view {
  margin-top: 0px;
  padding-top: 8px;
  border: 1px solid var(--paper-border);
  border-radius: 15px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: var(--paper-shadow);
  overflow: hidden;
}

.market-table :deep(.el-table__header-wrapper th) {
  background: #f3f6fa;
  color: var(--paper-text);
  font-weight: 700;
}

.market-table :deep(.el-table__row) {
  cursor: default;
}

.muted-cell {
  color: var(--paper-subtle);
}

.level-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 48px;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  border: 1px solid transparent;
}

.chip-low {
  color: #1d5f3a;
  background: rgba(72, 160, 120, 0.14);
  border-color: rgba(72, 160, 120, 0.4);
}

.chip-normal {
  color: #1c4c87;
  background: rgba(61, 112, 184, 0.14);
  border-color: rgba(61, 112, 184, 0.4);
}

.chip-high {
  color: #5a3d95;
  background: rgba(108, 83, 170, 0.14);
  border-color: rgba(108, 83, 170, 0.4);
}

.chip-none {
  color: var(--paper-subtle);
  background: rgba(193, 200, 209, 0.2);
  border-color: rgba(193, 200, 209, 0.56);
}

.card-view {
  background: rgba(255, 255, 255, 0.82);
  border-radius: 22px;
  border: 1px solid var(--paper-border);
  box-shadow: var(--paper-shadow);
  backdrop-filter: blur(10px);
  padding: 12px 18px 20px;
}

.category-tabs :deep(.el-tabs__header) {
  margin-bottom: 20px;
}

.category-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.category-tabs :deep(.el-tabs__item) {
  color: var(--paper-muted);
  font-weight: 700;
  height: 38px;
  line-height: 38px;
  padding: 0 14px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.category-tabs :deep(.el-tabs__item.is-top:nth-child(2)),
.category-tabs :deep(.el-tabs__item.is-top:last-child),
.category-tabs :deep(.el-tabs__item.is-bottom:nth-child(2)),
.category-tabs :deep(.el-tabs__item.is-bottom:last-child) {
  padding: 0 14px;
}

.category-tabs :deep(.el-tabs__item.is-active) {
  color: var(--v2);
  background: var(--v-soft-1);
}

.category-tabs :deep(.el-tabs__active-bar) {
  height: 0;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 18px;
}

@media (max-width: 1080px) {
  .insights-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .home {
    padding: 18px 14px 24px;
  }

  .hero-inner {
    border-radius: 20px;
    padding: 20px;
    flex-direction: column;
    align-items: flex-start;
  }

  .hero-status {
    width: 100%;
    min-width: 0;
  }

  .view-switch-wrap {
    justify-content: flex-start;
  }

  .heatmap-row {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .row-label {
    padding-top: 0;
  }

  .row-cells {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .card-view {
    border-radius: 18px;
    padding: 10px 12px 16px;
  }

  .table-view {
    border-radius: 14px;
  }

  .card-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }
}
</style>
