<template>
  <OpsLayout
    class="dashboard-shell"
    active-nav="home"
    main-class="main-area"
  >
    <template #header>
      <header class="ops-header">
        <div class="ops-header-copy">
          <h1 class="ops-header-title"><el-icon><Grid /></el-icon>监控概览</h1>
          <p class="ops-header-subtitle">这里展示订阅对象、聚合价格与最近采集结果的真实汇总。</p>
        </div>
        <div class="crawl-actions">
          <button class="primary-action" :disabled="runningCrawl || isCrawlRunning" @click="triggerCrawl">
            <el-icon><Refresh /></el-icon>
            {{ crawlButtonText }}
          </button>
          <button v-if="isCrawlRunning" class="pause-action" :disabled="pausingCrawl" @click="pauseCrawl">
            <el-icon><VideoPause /></el-icon>
            {{ pausingCrawl ? '暂停中' : '暂停' }}
          </button>
        </div>
      </header>
    </template>

        <template v-if="loading">
          <div class="loading-panel">
            <el-skeleton :rows="10" animated />
          </div>
        </template>

        <template v-else>
          <section v-if="shouldShowCrawlProgress && visibleCrawlProgress" class="crawl-progress-panel">
            <div class="progress-head">
              <div>
                <h2>采集进度</h2>
                <span>
                  {{ phaseLabel(visibleCrawlProgress.phase) }}
                  <template v-if="visibleCrawlProgress.current_hardware">
                    · 当前 {{ visibleCrawlProgress.current_hardware }}
                  </template>
                </span>
              </div>
              <strong>{{ visibleCrawlProgress.percent }}%</strong>
            </div>
            <el-progress
              :percentage="visibleCrawlProgress.percent"
              :status="progressStatus"
              :stroke-width="12"
            />
            <div class="progress-meta">
              <span>{{ visibleCrawlProgress.processed }} / {{ visibleCrawlProgress.total }} 个对象</span>
              <span v-if="visibleCrawlProgress.llm_total > 0">
                LLM 校验 {{ visibleCrawlProgress.llm_done }} / {{ visibleCrawlProgress.llm_total }}
              </span>
              <span v-else>成功 {{ crawlerHealth?.latest_run?.success ?? 0 }} · 失败 {{ crawlerHealth?.latest_run?.failed ?? 0 }} · 跳过 {{ crawlerHealth?.latest_run?.skipped ?? 0 }}</span>
            </div>
          </section>

          <section class="metric-grid">
            <article v-for="metric in overviewMetrics" :key="metric.label" :class="['metric-card', `tone-${metric.tone}`]">
              <div>
                <span>{{ metric.label }}</span>
                <strong>{{ metric.value }}</strong>
                <small>{{ metric.detail }}</small>
              </div>
              <span class="metric-icon" :class="metric.tone"><el-icon><component :is="metric.icon" /></el-icon></span>
            </article>
          </section>

          <section class="dashboard-grid">
            <div class="primary-column">
              <!-- 今日捡漏 + 大盘环图 -->
              <section class="deals-panel">
                <!-- 左：捡漏排行榜 -->
                <div class="deals-col">
                  <div class="deals-panel-head">
                    <h3><el-icon><Aim /></el-icon>今日捡漏</h3>
                    <button class="all-log-btn-sm" @click="goToDeals">全部 <el-icon><ArrowRight /></el-icon></button>
                  </div>
                  <div v-if="isCrawlRunning" class="deals-panel-empty">
                    <el-empty :image-size="40" description="采集中，稍后生成" />
                  </div>
                  <div v-else-if="dealRanking.length" class="deals-ranking">
                    <a
                      v-for="(deal, idx) in dealRanking"
                      :key="`${deal.hardware_id}-${deal.item_url}`"
                      class="rank-item"
                      :href="deal.item_url || undefined"
                      target="_blank"
                      rel="noreferrer"
                    >
                      <span class="rank-no" :class="idx < 3 ? `top-${idx + 1}` : ''">{{ idx + 1 }}</span>
                      <span class="rank-name">{{ deal.hardware_name }}</span>
                      <strong class="rank-price">¥{{ formatPrice(deal.price) }}</strong>
                      <em class="rank-badge">-{{ Math.round(deal.discount_rate * 100) }}%</em>
                    </a>
                  </div>
                  <div v-else class="deals-panel-empty">
                    <el-empty :image-size="40" description="暂无捡漏候选" />
                  </div>
                </div>

                <!-- 右：行情分布环图 -->
                <div class="donut-col">
                  <div class="deals-panel-head">
                    <h3><el-icon><DataAnalysis /></el-icon>行情分布</h3>
                  </div>
                  <div class="donut-body">
                    <v-chart class="donut-chart" :option="marketDonutOption" autoresize />
                    <div class="donut-stats">
                      <div v-for="s in marketStatusStats" :key="s.label" class="donut-stat-item">
                        <i class="donut-dot" :style="{ background: s.color }"></i>
                        <span>{{ s.label }}</span>
                        <strong>{{ s.count }}</strong>
                      </div>
                    </div>
                  </div>
                </div>
              </section>

              <section class="market-panel">
                <div class="toolbar">
                  <div class="view-tabs">
                    <button :class="{ active: displayMode === 'heatmap' }" @click="displayMode = 'heatmap'">
                      <el-icon><Grid /></el-icon>热力矩阵
                    </button>
                    <button :class="{ active: displayMode === 'table' }" @click="displayMode = 'table'">
                      <el-icon><Tickets /></el-icon>表格趋势
                    </button>
                    <button :class="{ active: displayMode === 'cards' }" @click="displayMode = 'cards'">
                      <el-icon><Postcard /></el-icon>卡片视图
                    </button>
                  </div>
                </div>

                <template v-if="displayMode === 'heatmap'">
                  <div class="heatmap-head">
                    <div>
                      <h3>市场热力矩阵</h3>
                      <p>颜色表示行情状态，深浅表示当日样本活跃度。点击单元格可进入详情。</p>
                    </div>
                    <div class="heat-legend" aria-label="热力图图例">
                      <span><i class="legend-dot low"></i>低位</span>
                      <span><i class="legend-dot normal"></i>正常</span>
                      <span><i class="legend-dot high"></i>偏高</span>
                      <span><i class="legend-dot none"></i>无数据</span>
                    </div>
                  </div>

                  <div class="heatmap-table">
                    <div class="heatmap-row" v-for="row in visibleHeatmapRows" :key="row.value">
                      <div class="row-label">{{ row.label }}</div>
                      <div class="row-cells">
                        <button
                          v-for="item in row.items"
                          :key="item.id"
                          class="heat-cell"
                          :class="`level-${heatLevel(item)}`"
                          :style="heatStyle(item)"
                          @click="goToDetail(item.id)"
                        >
                          <span class="cell-top">
                            <span class="cell-name">{{ item.name }}</span>
                            <span v-if="isSpecialHeatLevel(item)" class="cell-level">{{ specialHeatLabel(item) }}</span>
                          </span>
                          <span class="cell-value" v-if="item.latest_stats">¥{{ formatPrice(item.latest_stats.median_price) }}</span>
                          <span class="cell-value muted" v-else>无数据</span>
                        </button>
                      </div>
                    </div>
                  </div>
                </template>

                <template v-else-if="displayMode === 'table'">
                  <el-table :data="filteredHardware" class="market-table" stripe size="small">
                    <el-table-column prop="name" label="对象" min-width="70" />
                    <el-table-column label="中位价" width="92">
                      <template #default="{ row }">
                        <span v-if="row.latest_stats">¥{{ formatPrice(row.latest_stats.median_price) }}</span>
                        <span v-else class="muted-cell">-</span>
                      </template>
                    </el-table-column>
                    <el-table-column label="价格区间" width="138">
                      <template #default="{ row }">
                        <span v-if="row.latest_stats">
                          ¥{{ formatPrice(row.latest_stats.min_price) }} - ¥{{ formatPrice(row.latest_stats.max_price) }}
                        </span>
                        <span v-else class="muted-cell">-</span>
                      </template>
                    </el-table-column>
                    <el-table-column label="样本" width="58" align="center">
                      <template #default="{ row }">
                        <span v-if="row.latest_stats">{{ row.latest_stats.sample_count }}</span>
                        <span v-else class="muted-cell">-</span>
                      </template>
                    </el-table-column>
                    <el-table-column label="状态" width="68" align="center">
                      <template #default="{ row }">
                        <span class="level-chip" :class="`chip-${heatLevel(row)}`">
                          {{ HEAT_LEVEL_LABELS[heatLevel(row)] }}
                        </span>
                      </template>
                    </el-table-column>
                    <el-table-column label="趋势" width="210">
                      <template #default="{ row }">
                        <div class="compact-sparkline">
                          <MiniTrendSparkline
                            :points="trendCache[row.id]?.median ?? []"
                            :median-points="trendCache[row.id]?.median ?? []"
                            :avg-points="trendCache[row.id]?.avg ?? []"
                            :loading="Boolean(trendLoadingMap[row.id])"
                            :level="heatLevel(row)"
                            :height="34"
                          />
                        </div>
                      </template>
                    </el-table-column>
                    <el-table-column label="详情" width="60" fixed="right" align="center">
                      <template #default="{ row }">
                        <el-button link type="primary" @click="goToDetail(row.id)">查看</el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                </template>

                <template v-else>
                  <div class="card-grid">
                    <HardwareCard
                      v-for="item in filteredHardware"
                      :key="item.id"
                      :item="item"
                      @click="goToDetail(item.id)"
                    />
                  </div>
                </template>

                <el-empty v-if="!filteredHardware.length" description="暂无匹配数据" />
              </section>
            </div>
          </section>
        </template>
  </OpsLayout>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { hardwareApi, crawlerApi, dealsApi, healthApi } from '@/api'
import type { HardwareDetail, CrawlerStatus, DealItem, CrawlerHealth } from '@/api/types'
import HardwareCard from '@/components/HardwareCard.vue'
import MiniTrendSparkline from '@/components/MiniTrendSparkline.vue'
import OpsLayout from '@/components/OpsLayout.vue'

use(CanvasRenderer)
use(PieChart)
use(TooltipComponent)
use(LegendComponent)

type ViewMode = 'heatmap' | 'table' | 'cards'
type HeatLevel = 'low' | 'normal' | 'high' | 'none'

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

function normalizeView(value: unknown): ViewMode {
  const maybe = pickQueryString(value)
  return maybe === 'cards' || maybe === 'table' ? maybe : 'heatmap'
}

const router = useRouter()
const route = useRoute()

const loading = ref(true)
const runningCrawl = ref(false)
const pausingCrawl = ref(false)
const displayMode = ref<ViewMode>(normalizeView(route.query.view))
const searchQuery = ref('')
const groupedHardware = ref<Record<string, HardwareDetail[]>>({})
const crawlerStatus = ref<CrawlerStatus | null>(null)
const crawlerHealth = ref<CrawlerHealth | null>(null)
const dealItems = ref<DealItem[]>([])
const trendCache = ref<Record<number, { avg: number[]; median: number[] }>>({})
const trendLoadingMap = ref<Record<number, boolean>>({})
const trendInFlight = new Set<number>()
let progressTimer: number | undefined

const allHardware = computed(() => Object.values(groupedHardware.value).flat())

const hardwareWithStats = computed(() => allHardware.value.filter((item) => item.latest_stats))

const crawlProgress = computed(() => crawlerHealth.value?.latest_run?.progress ?? null)

const visibleCrawlProgress = computed(() => {
  if (crawlProgress.value) return crawlProgress.value
  if (!runningCrawl.value) return null
  return {
    phase: 'running',
    percent: 0,
    processed: 0,
    total: activeHardwareCount.value || totalHardware.value || 0,
    current_hardware: null,
    crawl_percent: 0,
    crawl_done: 0,
    crawl_total: 0,
    llm_percent: 0,
    llm_done: 0,
    llm_total: 0,
    llm_current_hardware: null,
    llm_current_done: null,
    llm_current_total: null,
  }
})

const isCrawlRunning = computed(() => {
  const phase = crawlProgress.value?.phase
  return phase === 'running' || phase === 'crawling' || phase === 'validating' || phase === 'aggregating'
})

const shouldShowCrawlProgress = computed(() => isCrawlRunning.value || runningCrawl.value)

const crawlButtonText = computed(() => {
  if (runningCrawl.value) return '监测启动中'
  if (isCrawlRunning.value) return '采集中'
  return '开始新监测'
})

const progressStatus = computed(() => {
  const phase = crawlProgress.value?.phase
  if (phase === 'success') return 'success'
  if (phase === 'partial' || phase === 'failed' || phase === 'interrupted') return 'warning'
  return undefined
})

const filteredHardware = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  const source = allHardware.value
  if (!query) return source
  return source.filter((item) => {
    return `${item.name} ${item.search_keywords.join(' ')}`.toLowerCase().includes(query)
  })
})

const visibleHeatmapRows = computed(() => {
  return [{
    value: 'all',
    label: '全部订阅',
    items: filteredHardware.value,
  }].filter((row) => row.items.length)
})

const maxSampleCount = computed(() => {
  const counts = hardwareWithStats.value.map((item) => item.latest_stats?.sample_count ?? 0)
  return counts.length ? Math.max(...counts) : 1
})

const totalHardware = computed(() => allHardware.value.length)
const totalWithStats = computed(() => hardwareWithStats.value.length)
const totalMissing = computed(() => Math.max(0, totalHardware.value - totalWithStats.value))
const totalSamples = computed(() => {
  return hardwareWithStats.value.reduce((sum, item) => sum + (item.latest_stats?.sample_count ?? 0), 0)
})

const activeHardwareCount = computed(() => allHardware.value.filter((item) => item.is_active).length)

const overviewMetrics = computed(() => [
  {
    label: '启用订阅',
    value: activeHardwareCount.value,
    detail: `${totalHardware.value} 个对象 · ${totalMissing.value} 个待补充`,
    icon: 'Grid',
    tone: 'blue',
  },
  {
    label: '今日样本',
    value: totalSamples.value,
    detail: `${totalWithStats.value} 个对象已有行情`,
    icon: 'Search',
    tone: 'green',
  },
  {
    label: '捡漏候选',
    value: dealItems.value.length,
    detail: '来自今日有效样本',
    icon: 'Aim',
    tone: 'amber',
  },
  {
    label: '监测轮次',
    value: crawlerHealth.value?.run_count ?? 0,
    detail: crawlerHealth.value?.latest_run?.status ? `最近 ${phaseLabel(crawlerHealth.value.latest_run.status)}` : '等待首次运行',
    icon: 'Monitor',
    tone: 'purple',
  },
])

// 按折扣力度从大到小排列（最容易捡漏的排前面）
const dealRanking = computed(() => {
  return [...dealItems.value]
    .sort((a, b) => b.discount_rate - a.discount_rate)
})

type StatEntry = { label: string; color: string; count: number; value: string }

const marketStatusStats = computed<StatEntry[]>(() => {
  const counts = { low: 0, normal: 0, high: 0, none: 0 }
  for (const item of allHardware.value) {
    const level = item.latest_stats?.price_level ?? 'none'
    counts[level as keyof typeof counts]++
  }
  return [
    { label: '低位', color: 'rgb(59,130,246)',    count: counts.low,    value: 'low' },
    { label: '正常', color: 'rgb(229,179,25)',    count: counts.normal, value: 'normal' },
    { label: '偏高', color: 'rgb(221,102,71)',    count: counts.high,   value: 'high' },
    { label: '无数据', color: 'rgba(0,0,0,0.15)', count: counts.none,   value: 'none' },
  ]
})

const marketDonutOption = computed(() => {
  const stats = marketStatusStats.value
  const total = stats.reduce((sum, s) => sum + s.count, 0)
  return {
    tooltip: {
      trigger: 'item',
      formatter: (p: { name: string; value: number; percent: number }) =>
        `${p.name}: ${p.value} 个 (${p.percent}%)`,
    },
    legend: { show: false },
    series: [
      {
        type: 'pie',
        radius: ['52%', '78%'],
        center: ['50%', '50%'],
        avoidLabelOverlap: false,
        label: { show: false },
        emphasis: {
          scale: true,
          scaleSize: 6,
          label: { show: false },
        },
        data: total === 0
          ? [{ value: 1, name: '暂无数据', itemStyle: { color: 'rgba(0,0,0,0.08)' } }]
          : stats
              .filter(s => s.count > 0)
              .map(s => ({ value: s.count, name: s.label, itemStyle: { color: s.color } })),
      },
    ],
  }
})


const focusItem = computed(() => {
  const sortedFiltered = [...filteredHardware.value]
    .filter((item) => item.latest_stats)
    .sort((a, b) => (b.latest_stats?.sample_count ?? 0) - (a.latest_stats?.sample_count ?? 0))
  if (sortedFiltered.length) return sortedFiltered[0]

  return [...hardwareWithStats.value]
    .sort((a, b) => (b.latest_stats?.sample_count ?? 0) - (a.latest_stats?.sample_count ?? 0))[0] ?? null
})

watch(
  [displayMode, groupedHardware],
  () => {
    if (displayMode.value === 'table') {
      void ensureTrendsForVisibleItems()
    }
  },
  { immediate: true },
)

watch(focusItem, (item) => {
  if (item?.latest_stats) {
    void loadTrendForHardware(item.id)
  }
})

watch(isCrawlRunning, (isRunning, wasRunning) => {
  if (!isRunning && wasRunning) {
    // Crawl just finished — do a final full reload so metrics update immediately
    void loadDashboardData(true)
  }
})

watch(
  () => route.query.view,
  (nextView) => {
    const normalized = normalizeView(nextView)
    if (normalized !== displayMode.value) {
      displayMode.value = normalized
    }
  },
)

watch(displayMode, (nextView) => {
  if (normalizeView(route.query.view) === nextView) {
    return
  }
  router.replace({
    name: 'home',
    query: {
      view: nextView,
    },
  })
})

const SCROLL_KEY = 'home-scroll-top'

onBeforeRouteLeave((to) => {
  if (to.name === 'hardware-detail') {
    const container = document.querySelector('.ops-workspace')
    if (container) sessionStorage.setItem(SCROLL_KEY, String((container as HTMLElement).scrollTop))
  }
})

onMounted(async () => {
  await loadDashboardData()
  const saved = sessionStorage.getItem(SCROLL_KEY)
  if (saved) {
    sessionStorage.removeItem(SCROLL_KEY)
    void nextTick(() => {
      const container = document.querySelector('.ops-workspace')
      if (container) (container as HTMLElement).scrollTop = Number(saved)
    })
  }
  progressTimer = window.setInterval(() => {
    void refreshCrawlerHealth().then(() => {
      if (isCrawlRunning.value) {
        void loadDashboardData(true)
      }
    })
  }, 3000)
})

onUnmounted(() => {
  if (progressTimer) {
    window.clearInterval(progressTimer)
  }
})

async function loadDashboardData(silent = false): Promise<void> {
  try {
    const [hardware, status, deals, health] = await Promise.all([hardwareApi.list(), crawlerApi.status(), dealsApi.today(100), healthApi.crawler()])
    groupedHardware.value = hardware
    crawlerStatus.value = status
    dealItems.value = deals
    crawlerHealth.value = health
    if (focusItem.value?.latest_stats) {
      void loadTrendForHardware(focusItem.value.id)
    }
  } catch {
    if (!silent) ElMessage.error('加载数据失败，请检查后端服务')
  } finally {
    if (!silent) loading.value = false
  }
}

async function refreshCrawlerHealth(): Promise<void> {
  try {
    crawlerHealth.value = await healthApi.crawler()
  } catch {
    // Keep the last known progress visible while a transient refresh fails.
  }
}

async function triggerCrawl(): Promise<void> {
  if (runningCrawl.value) return
  if (isCrawlRunning.value) {
    ElMessage.warning('当前已有采集任务正在运行，完成后才能开始新一轮监测')
    return
  }
  runningCrawl.value = true
  try {
    const result = await crawlerApi.run(true)
    await refreshCrawlerHealth()
    void loadDashboardData(true)
    if (result.status === 'running') {
      ElMessage.warning(result.summary.message ?? '当前已有采集任务正在运行')
      return
    }
    ElMessage.success('已启动新一轮真实采集')
  } catch {
    ElMessage.error('启动监测失败')
  } finally {
    runningCrawl.value = false
  }
}

async function pauseCrawl(): Promise<void> {
  if (pausingCrawl.value) return
  pausingCrawl.value = true
  try {
    const result = await crawlerApi.pause()
    await refreshCrawlerHealth()
    if (result.status === 'idle') {
      ElMessage.info(result.summary.message ?? '当前没有正在运行的采集任务')
      return
    }
    ElMessage.success(result.summary.message ?? '已暂停当前采集任务')
  } catch {
    ElMessage.error('暂停监测失败')
  } finally {
    pausingCrawl.value = false
  }
}

function phaseLabel(phase: string): string {
  const labels: Record<string, string> = {
    running: '准备中',
    crawling: '正在采集',
    validating: '正在校验',
    aggregating: '正在聚合',
    success: '已完成',
    partial: '部分完成',
    failed: '失败',
    interrupted: '已中断',
  }
  return labels[phase] ?? phase
}

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
      [hardwareId]: {
        avg: trend.trend.map((point) => point.avg_price),
        median: trend.trend.map((point) => point.median_price),
      },
    }
  } catch {
    trendCache.value = {
      ...trendCache.value,
      [hardwareId]: { avg: [], median: [] },
    }
  } finally {
    trendInFlight.delete(hardwareId)
    const { [hardwareId]: _removed, ...rest } = trendLoadingMap.value
    trendLoadingMap.value = rest
  }
}

async function ensureTrendsForVisibleItems(): Promise<void> {
  const idsToLoad = filteredHardware.value
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
    return {}
  }

  const ratio = Math.max(0, Math.min(1, item.latest_stats.sample_count / maxSampleCount.value))
  const fillAlpha = 0.14 + ratio * 0.2
  const borderAlpha = Math.min(fillAlpha + 0.18, 0.52)

  return {
    '--heat-fill-alpha': fillAlpha.toFixed(3),
    '--heat-border-alpha': borderAlpha.toFixed(3),
  }
}

function goToDetail(id: number) {
  router.push({
    name: 'hardware-detail',
    params: { id },
    query: {
      fromView: displayMode.value,
    },
  })
}

function goToDeals() {
  router.push({ name: 'deals' })
}
</script>

<style scoped>
.dashboard-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: var(--sidebar-width) minmax(0, 1fr);
  background: var(--layout-page-gradient);
  color: var(--paper-text);
}

.activity-item i {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: var(--text-success);
}

.search-box {
  width: min(720px, 56vw);
  height: 40px;
  border: 1px solid var(--paper-border);
  border-radius: var(--radius-card);
  background: var(--surface-floating);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 12px;
  color: #8090a4;
}

.hardware-jump-select {
  flex: 1;
  min-width: 0;
}

.hardware-jump-select :deep(.el-select__wrapper) {
  min-height: 36px;
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
}

.hardware-jump-select :deep(.el-select__placeholder),
.hardware-jump-select :deep(.el-select__input) {
  color: var(--paper-subtle);
  font-size: 13px;
  font-weight: 700;
}

.hardware-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  min-width: 0;
}

.hardware-option span {
  min-width: 0;
  overflow: hidden;
  color: var(--text-strong);
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hardware-option small {
  flex: 0 0 auto;
  color: var(--paper-subtle);
  font-size: 12px;
  font-weight: 800;
}

/* 标题样式统一由 ops-shared.css 中的 .ops-header 系列类管理 */

.crawl-actions {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
}

.primary-action {
  height: 40px;
  border: 0;
  border-radius: var(--radius-control);
  background: var(--text-strong);
  color: var(--surface-floating);
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 16px;
  font-size: 13px;
  font-weight: 800;
  box-shadow: var(--shadow-control);
  cursor: pointer;
}

.primary-action:disabled {
  opacity: 0.65;
  cursor: default;
}

.pause-action {
  height: 36px;
  border: 1px solid var(--paper-border);
  border-radius: var(--radius-control);
  background: var(--surface-floating);
  color: var(--paper-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 14px;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.pause-action:hover {
  border-color: #bfcada;
  background: var(--paper-surface-soft);
  color: var(--text-strong);
}

.pause-action:disabled {
  opacity: 0.6;
  cursor: default;
}

.metric-card {
  min-height: 122px;
  padding: 22px 24px;
  display: flex;
  justify-content: space-between;
  gap: 14px;
}

.loading-panel,
.crawl-progress-panel {
  border: 1px solid var(--paper-border);
  border-radius: var(--radius-card);
  background: var(--surface-floating);
  box-shadow: var(--paper-shadow);
}

.crawl-progress-panel {
  padding: 18px;
  margin-bottom: 20px;
}

.progress-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.progress-head h2 {
  font-size: 18px;
}

.progress-head span,
.progress-meta {
  color: #7b8798;
  font-size: 12px;
  font-weight: 700;
}

.progress-head strong {
  color: var(--el-color-primary);
  font-size: 20px;
  font-weight: 800;
}

.progress-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-top: 10px;
  color: #7b8798;
}

.crawl-progress-panel :deep(.el-progress__text) {
  font-size: 11px !important;
  font-weight: 800;
  color: var(--el-color-primary) !important;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.metric-card span,
.metric-card small {
  color: var(--dashboard-metric-muted);
  font-size: 12px;
  font-weight: 800;
}

.metric-card strong {
  display: block;
  margin: 8px 0 14px;
  color: var(--dashboard-metric-text);
  font-size: 29px;
}

.metric-card {
  position: relative;
  overflow: hidden;
  border: 0 !important;
  box-shadow: var(--detail-panel-shadow) !important;
}

.metric-card::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.22), transparent 48%);
  pointer-events: none;
}

.metric-card.tone-blue {
  background: var(--dashboard-metric-card-blue) !important;
}

.metric-card.tone-green {
  background: var(--dashboard-metric-card-green) !important;
}

.metric-card.tone-amber {
  background: var(--dashboard-metric-card-amber) !important;
}

.metric-card.tone-purple {
  background: var(--dashboard-metric-card-purple) !important;
}

.metric-icon {
  width: auto;
  height: auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 27px;
  background: transparent !important;
  color: var(--dashboard-metric-icon);
  box-shadow: none;
}

.metric-icon.blue,
.metric-icon.green,
.metric-icon.amber,
.metric-icon.purple {
  color: var(--dashboard-metric-icon);
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 30px;
  align-items: start;
}

.primary-column {
  display: flex;
  flex-direction: column;
  gap: 24px;
  min-width: 0;
}

.focus-panel {
  padding: 26px 24px 24px;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--paper-border);
}

.panel-head h2 {
  font-size: 20px;
  margin-bottom: 8px;
}

.panel-head p {
  color: var(--paper-muted);
  font-size: 13px;
}

.fresh-pill {
  align-self: flex-start;
  border-radius: 999px;
  background: var(--v-soft-2);
  color: var(--chip-normal-text);
  padding: 7px 11px;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin: 22px 0 24px;
}

.summary-cards article {
  padding: 18px;
  border: 1px solid var(--paper-border);
  border-radius: var(--radius-card);
  background: var(--paper-surface-soft);
  box-shadow: none;
}

.summary-cards span,
.summary-cards small {
  display: block;
  color: var(--paper-muted);
  font-size: 12px;
  font-weight: 800;
}

.summary-cards strong {
  display: block;
  margin: 12px 0 8px;
  color: var(--text-strong);
  font-size: 26px;
}

.curve-card {
  min-height: 202px;
  border: 1px solid var(--paper-border);
  border-radius: var(--radius-card);
  background: var(--paper-surface-soft);
  padding: 18px 20px;
}

.curve-head {
  display: flex;
  justify-content: space-between;
  color: var(--paper-muted);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.26em;
}

.curve-head div {
  letter-spacing: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.dot {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  display: inline-block;
}

.dot.avg { background: var(--chart-spark-avg); }
.dot.mid { background: var(--chart-spark-median); }

.market-panel {
  padding: 18px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 14px;
  margin-bottom: 18px;
}

.view-tabs,
.view-tabs button {
  height: 34px;
  border: 0;
  background: transparent;
  color: var(--paper-muted);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 12px;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.heatmap-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.heatmap-head h3 {
  font-size: 16px;
  margin-bottom: 4px;
}

.heatmap-head p,
.muted-cell {
  color: var(--paper-muted);
  font-size: 12px;
}

.heat-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  color: var(--paper-muted);
  font-size: 12px;
  font-weight: 700;
}

.heat-legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.legend-dot {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  display: inline-block;
}

.legend-dot.low { background: rgb(var(--heat-low-rgb)); }
.legend-dot.normal { background: rgb(var(--heat-normal-rgb)); }
.legend-dot.high { background: rgb(var(--heat-high-rgb)); }
.legend-dot.none { background: var(--paper-border-strong); }

.heatmap-table {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.heatmap-row {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 12px;
}

.row-label {
  padding-top: 10px;
  color: var(--paper-muted);
  font-size: 12px;
  font-weight: 900;
}

.row-cells {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(138px, 1fr));
  gap: 9px;
}

.heat-cell {
  min-height: 72px;
  border: 1px solid var(--heat-cell-none-border);
  border-radius: var(--radius-card);
  padding: 10px;
  background: var(--heat-cell-none-bg);
  color: var(--heat-cell-none-text);
  text-align: left;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}

.heat-cell.level-low,
.heat-cell.level-normal,
.heat-cell.level-high {
  color: var(--heat-cell-text);
}

.heat-cell.level-low {
  background: rgba(var(--heat-low-rgb), var(--heat-fill-alpha, 0.18));
  border-color: rgba(var(--heat-low-rgb), var(--heat-border-alpha, 0.32));
}

.heat-cell.level-normal {
  background: rgba(var(--heat-normal-rgb), var(--heat-fill-alpha, 0.18));
  border-color: rgba(var(--heat-normal-rgb), var(--heat-border-alpha, 0.32));
}

.heat-cell.level-high {
  background: rgba(var(--heat-high-rgb), var(--heat-fill-alpha, 0.18));
  border-color: rgba(var(--heat-high-rgb), var(--heat-border-alpha, 0.32));
}

.heat-cell:hover {
  transform: translateY(-2px);
  box-shadow: var(--heat-cell-hover-shadow);
}

.cell-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 7px;
}

.cell-name {
  display: block;
  font-size: 12px;
  font-weight: 900;
  line-height: 1.3;
}

.cell-level {
  flex-shrink: 0;
  padding: 3px 5px;
  border-radius: 999px;
  background: var(--badge-neutral-bg);
  color: var(--badge-neutral-text);
  font-size: 10px;
  font-weight: 900;
}

.cell-value {
  display: block;
  margin-top: 8px;
  font-size: 13px;
  font-weight: 900;
}

.cell-value.muted {
  color: var(--paper-subtle);
}

.market-table :deep(.el-table__header-wrapper),
.market-table :deep(.el-table__header),
.market-table :deep(thead),
.market-table :deep(thead tr) {
  background: var(--table-head-wrapper-bg) !important;
}

.market-table :deep(.el-table__header-wrapper th) {
  background: var(--table-head-bg) !important;
  color: var(--table-head-color) !important;
  border-bottom: var(--table-head-border) !important;
  font-weight: 900;
}

.market-table :deep(.el-table__header-wrapper th .cell) {
  color: var(--table-head-color) !important;
}

.market-table :deep(.el-table__header-wrapper th .cell *),
.market-table :deep(.el-table__fixed-header-wrapper th .cell),
.market-table :deep(.el-table__fixed-header-wrapper th .cell *),
.market-table :deep(thead th),
.market-table :deep(thead th *) {
  color: var(--table-head-color) !important;
}

.market-table :deep(.el-table__fixed-header-wrapper),
.market-table :deep(.el-table__fixed-right .el-table__fixed-header-wrapper),
.market-table :deep(.el-table__fixed-left .el-table__fixed-header-wrapper) {
  background: var(--table-head-wrapper-bg) !important;
}

.market-table :deep(.el-table__inner-wrapper),
.market-table :deep(.el-table__body-wrapper),
.market-table :deep(.el-scrollbar__view),
.market-table :deep(.el-table__fixed),
.market-table :deep(.el-table__fixed-right) {
  background: var(--table-wrapper-bg) !important;
}

.market-table :deep(.el-table__inner-wrapper::before) {
  background: var(--table-cell-border) !important;
}

.market-table :deep(.el-table__cell) {
  padding: 6px 0;
}

.market-table :deep(.el-table__row),
.market-table :deep(.el-table__row > td.el-table__cell) {
  background: var(--table-row-bg) !important;
}

.market-table :deep(.el-table__body tr.el-table__row--striped > td.el-table__cell) {
  background: var(--table-row-striped-bg) !important;
}

.market-table :deep(.el-table-fixed-column--right),
.market-table :deep(.el-table-fixed-column--left) {
  background: var(--table-fixed-bg) !important;
}

.market-table :deep(.el-table__body td.el-table__cell),
.market-table :deep(.el-table__body td.el-table__cell .cell),
.market-table :deep(.el-table__body td.el-table__cell .cell *) {
  color: var(--paper-text) !important;
}

.market-table :deep(.el-table__body .muted-cell) {
  color: var(--paper-muted) !important;
}

.market-table :deep(.el-table__body .level-chip),
.market-table :deep(.el-table__body .level-chip *) {
  color: inherit !important;
}

.market-table :deep(.el-table__body .el-button.is-link),
.market-table :deep(.el-table__body .el-button.is-link *) {
  color: var(--accent-primary) !important;
}

.market-table :deep(.cell) {
  padding: 0 8px;
  font-size: 13px;
  line-height: 1.35;
}

.market-table :deep(.el-table__row) {
  height: 50px;
}

.market-table :deep(.el-button.is-link) {
  height: 24px;
  padding: 0;
  font-size: 13px;
  font-weight: 800;
}

.compact-sparkline {
  width: 118px;
  height: 34px;
  display: flex;
  align-items: center;
  overflow: hidden;
  padding: 0 8px;
  border: var(--table-trend-border) !important;
  border-radius: 999px !important;
  background: var(--table-trend-bg) !important;
  box-shadow: var(--table-trend-shadow);
}

.level-chip {
  display: inline-flex;
  justify-content: center;
  min-width: 42px;
  padding: 2px 6px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 900;
}

.chip-low { color: var(--chip-low-text); background: var(--chip-low-bg); }
.chip-normal { color: var(--chip-normal-text); background: var(--chip-normal-bg); }
.chip-high { color: var(--chip-high-text); background: var(--chip-high-bg); }
.chip-none { color: var(--chip-none-text); background: var(--chip-none-bg); }

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(245px, 1fr));
  gap: 14px;
}

.deals-panel {
  display: grid;
  grid-template-columns: 1fr 1fr;
  height: 340px;
}

.deals-col {
  display: flex;
  flex-direction: column;
  padding: 18px 20px;
  border-right: 1px solid var(--paper-border);
  min-height: 0;
}

.donut-col {
  display: flex;
  flex-direction: column;
  padding: 18px 20px;
  min-height: 0;
}

.deals-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.deals-panel-head h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 900;
  margin: 0;
  color: var(--text-strong);
}

.deals-ranking {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.rank-item {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 8px;
  padding: 8px 6px;
  border-radius: var(--radius-control);
  color: inherit;
  text-decoration: none;
  transition: background 0.15s;
}

.rank-item:hover {
  background: var(--surface-soft-hover);
}

.rank-no {
  width: 22px;
  height: 22px;
  border-radius: 999px;
  background: var(--paper-border-strong);
  color: var(--paper-muted);
  font-size: 11px;
  font-weight: 900;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.rank-no.top-1 { background: #f59e0b; color: #fff; }
.rank-no.top-2 { background: #94a3b8; color: #fff; }
.rank-no.top-3 { background: #b45309; color: #fff; }

.rank-name {
  font-size: 12px;
  font-weight: 800;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--paper-text);
}

.rank-price {
  font-size: 13px;
  font-weight: 900;
  color: var(--text-strong);
  white-space: nowrap;
}

.rank-badge {
  min-width: 40px;
  height: 20px;
  border-radius: 999px;
  background: var(--badge-success-bg);
  color: var(--badge-success-text);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-style: normal;
  font-weight: 900;
}

.donut-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-height: 0;
}

.donut-chart {
  flex: 0 0 auto;
  width: 180px;
  height: 180px;
}

.donut-stats {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px 20px;
}

.donut-stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.donut-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  flex-shrink: 0;
}

.donut-stat-item span {
  font-size: 12px;
  font-weight: 800;
  color: var(--paper-muted);
  min-width: 32px;
}

.donut-stat-item strong {
  font-size: 14px;
  font-weight: 900;
  color: var(--text-strong);
}

.deals-panel-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.all-log-btn-sm {
  border: 0;
  background: transparent;
  color: var(--paper-muted);
  font-size: 12px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  padding: 0;
}

.all-log-btn-sm:hover {
  color: var(--accent-primary);
}

.deal-item {
  min-height: 42px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 8px;
  padding: 9px;
  color: inherit;
  text-decoration: none;
}

.deal-item:hover {
  background: var(--surface-soft-hover);
}

.deal-item span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  font-weight: 800;
}

.deal-item strong {
  color: var(--text-strong);
  font-size: 13px;
}

.deal-item em {
  min-width: 42px;
  height: 22px;
  border-radius: 999px;
  background: var(--badge-success-bg);
  color: var(--badge-success-text);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-style: normal;
  font-weight: 900;
}

.activity-item {
  display: grid;
  grid-template-columns: 8px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  border: 0;
  border-bottom: 1px solid var(--paper-border);
  background: transparent;
  padding: 15px 0;
  text-align: left;
  cursor: pointer;
}

.activity-item strong,
.activity-item span,
.activity-item small {
  display: block;
}

.activity-item strong {
  color: var(--text-strong);
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-item span,
.activity-item small {
  color: var(--paper-muted);
  font-size: 11px;
  line-height: 1.7;
}

.activity-item em {
  border: 1px solid var(--paper-border);
  border-radius: 999px;
  color: var(--text-strong);
  padding: 4px 8px;
  font-size: 10px;
  font-style: normal;
  font-weight: 900;
}

.all-log-btn {
  width: 100%;
  height: 42px;
  border: 0;
  background: transparent;
  color: var(--text-strong);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-weight: 900;
  cursor: pointer;
}

@media (max-width: 900px) {
  .dashboard-shell {
    grid-template-columns: 1fr;
  }

  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .search-box {
    width: 100%;
  }

  .main-area {
    padding: 20px 14px 28px;
  }

  .panel-head,
  .heatmap-head {
    flex-direction: column;
  }

  .metric-grid,
  .summary-cards {
    grid-template-columns: 1fr;
  }

  .heatmap-row {
    grid-template-columns: 1fr;
  }

  .row-cells {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
