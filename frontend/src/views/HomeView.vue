<template>
  <div class="dashboard-shell ops-page">
    <aside class="sidebar ops-sidebar">
      <div class="brand">
        <span class="brand-mark"><el-icon><Lightning /></el-icon></span>
        <div>
          <strong>Market Pulse</strong>
          <span>Second-hand Market</span>
        </div>
      </div>

      <nav class="side-nav ops-nav" aria-label="主导航">
        <button class="nav-item active">
          <el-icon><Grid /></el-icon>
          <span>监控概览</span>
        </button>
        <RouterLink class="nav-link" :to="{ name: 'deals' }">
          <el-icon><Aim /></el-icon>
          <span>今日捡漏</span>
        </RouterLink>
        <RouterLink class="nav-link" :to="{ name: 'hardware-admin' }">
          <el-icon><Setting /></el-icon>
          <span>订阅管理</span>
        </RouterLink>
        <RouterLink class="nav-link" :to="{ name: 'alerts' }">
          <el-icon><Bell /></el-icon>
          <span>价格提醒</span>
        </RouterLink>
        <RouterLink class="nav-link" :to="{ name: 'crawler-health' }">
          <el-icon><Monitor /></el-icon>
          <span>爬虫健康</span>
        </RouterLink>
      </nav>

      <div class="system-card">
        <span class="system-label">系统状态</span>
        <strong><i></i>后端实时已连接</strong>
        <span>{{ crawlerStatus?.last_run_date ? `更新于 ${crawlerStatus.last_run_date}` : '等待首次更新' }}</span>
      </div>
    </aside>

    <section class="workspace ops-workspace">
      <header class="topbar">
        <div class="search-box">
          <el-icon><Search /></el-icon>
          <el-select
            v-model="selectedSearchHardwareId"
            class="hardware-jump-select"
            filterable
            clearable
            placeholder="选择商品"
            @change="jumpToSelectedHardware"
          >
            <el-option
              v-for="item in activeHardwareOptions"
              :key="item.id"
              :label="item.name"
              :value="String(item.id)"
            >
              <div class="hardware-option">
                <span>{{ item.name }}</span>
                <small v-if="item.latest_stats">{{ item.latest_stats.sample_count }} 个样本</small>
                <small v-else>暂无数据</small>
              </div>
            </el-option>
          </el-select>
        </div>
      </header>

      <main class="main-area ops-main">
        <section class="page-title-row">
          <div>
            <p class="eyebrow">MARKET MONITOR</p>
            <h1><el-icon><Grid /></el-icon>监控概览</h1>
            <p>这里展示订阅对象、聚合价格与最近采集结果的真实汇总。</p>
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
        </section>

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
              striped
              striped-flow
            />
            <div class="progress-meta">
              <span>{{ visibleCrawlProgress.processed }} / {{ visibleCrawlProgress.total }} 个对象</span>
              <span v-if="visibleCrawlProgress.phase === 'validating' && visibleCrawlProgress.validation_total">
                已校验 {{ visibleCrawlProgress.validation_processed ?? 0 }} / {{ visibleCrawlProgress.validation_total }} 条 · 待校验 {{ visibleCrawlProgress.validation_pending ?? 0 }} 条
              </span>
              <span v-else>成功 {{ crawlerHealth?.latest_run?.success ?? 0 }} · 失败 {{ crawlerHealth?.latest_run?.failed ?? 0 }} · 跳过 {{ crawlerHealth?.latest_run?.skipped ?? 0 }}</span>
            </div>
          </section>

          <section class="metric-grid">
            <article v-for="metric in overviewMetrics" :key="metric.label" class="metric-card">
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
              <section class="focus-panel">
                <div class="panel-head">
                  <div>
                    <h2>{{ focusItem?.name ?? '暂无关注对象' }}</h2>
                    <p>
                      当前订阅中样本最多的对象；搜索后会优先显示匹配结果里的最高样本项。
                    </p>
                  </div>
                  <span class="fresh-pill">最近更新 {{ crawlerStatus?.last_run_date ?? '暂无' }}</span>
                </div>

                <div class="summary-cards" v-if="focusItem?.latest_stats">
                  <article>
                    <span>当前均价</span>
                    <strong>¥{{ formatPrice(focusItem.latest_stats.avg_price) }}</strong>
                    <small>样本 {{ focusItem.latest_stats.sample_count }} 条</small>
                  </article>
                  <article>
                    <span>历史中位</span>
                    <strong>¥{{ formatPrice(focusItem.latest_stats.median_price) }}</strong>
                    <small>唯一商品 {{ focusItem.latest_stats.sample_count }} 个</small>
                  </article>
                  <article>
                    <span>价格区间</span>
                    <strong>¥{{ formatPrice(focusItem.latest_stats.min_price) }}</strong>
                    <small>最高 ¥{{ formatPrice(focusItem.latest_stats.max_price) }}</small>
                  </article>
                </div>

                <div class="curve-card">
                  <div class="curve-head">
                    <span>DAILY PRICE CURVE</span>
                    <div>
                      <i class="dot avg"></i>均价
                      <i class="dot mid"></i>中位数
                    </div>
                  </div>
                  <MiniTrendSparkline
                    v-if="focusItem"
                    :points="trendCache[focusItem.id]?.median ?? []"
                    :median-points="trendCache[focusItem.id]?.median ?? []"
                    :avg-points="trendCache[focusItem.id]?.avg ?? []"
                    :loading="Boolean(trendLoadingMap[focusItem.id])"
                    :level="heatLevel(focusItem)"
                    :height="112"
                  />
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
                    <el-table-column prop="name" label="对象" min-width="128" />
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
                    <el-table-column label="趋势" width="132">
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

            <aside class="activity-panel">
              <div class="activity-head">
                <h3><el-icon><Pulse /></el-icon>今日捡漏</h3>
              </div>

              <div v-if="isCrawlRunning" class="activity-empty">
                <el-empty :image-size="72" description="本轮采集中，完成后生成今日捡漏" />
              </div>

              <template v-else>
                <div class="deals-box">
                  <div class="deals-head">
                    <span>今日捡漏 TOP</span>
                    <strong>{{ dealItems.length }}</strong>
                  </div>
                  <div class="deals-list" v-if="dealItems.length">
                    <a
                      v-for="deal in dealItems.slice(0, 5)"
                      :key="`${deal.hardware_id}-${deal.item_url}-${deal.title}`"
                      class="deal-item"
                      :href="deal.item_url || undefined"
                      target="_blank"
                      rel="noreferrer"
                    >
                      <span>{{ deal.hardware_name }}</span>
                      <strong>¥{{ formatPrice(deal.price) }}</strong>
                      <em>-{{ Math.round(deal.discount_rate * 100) }}%</em>
                    </a>
                  </div>
                  <el-empty v-else :image-size="54" description="暂无捡漏候选" />
                </div>

                <div class="activity-list">
                  <button
                    v-for="item in activityItems"
                    :key="`activity-${item.id}`"
                    class="activity-item"
                    @click="goToDetail(item.id)"
                  >
                    <i></i>
                    <div>
                      <strong>{{ item.name }}</strong>
                      <span>{{ item.latest_stats?.stat_date ?? '暂无更新' }}</span>
                      <small v-if="item.latest_stats">当前 ¥{{ formatPrice(item.latest_stats.median_price) }}</small>
                      <small v-else>等待下一次调度执行</small>
                    </div>
                    <em>{{ item.latest_stats ? '已更新' : '待补充' }}</em>
                  </button>
                </div>
              </template>

              <button class="all-log-btn" @click="goToDeals">
                查看全部捡漏 <el-icon><ArrowRight /></el-icon>
              </button>
            </aside>
          </section>
        </template>
      </main>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { RouterLink } from 'vue-router'
import { ElMessage } from 'element-plus'
import { hardwareApi, crawlerApi, dealsApi, healthApi } from '@/api'
import type { HardwareDetail, CrawlerStatus, DealItem, CrawlerHealth } from '@/api/types'
import HardwareCard from '@/components/HardwareCard.vue'
import MiniTrendSparkline from '@/components/MiniTrendSparkline.vue'

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
const selectedSearchHardwareId = ref('')
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
    validation_total: 0,
    validation_processed: 0,
    validation_pending: 0,
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

const activeHardwareOptions = computed(() => {
  return allHardware.value
    .filter((item) => item.is_active)
    .sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'))
})

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

const activityItems = computed(() => {
  const missing = allHardware.value.filter((item) => !item.latest_stats).slice(0, 3)
  return [...sampleRanking.value.slice(0, 5), ...missing].slice(0, 8)
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

onMounted(async () => {
  await loadDashboardData()
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
    return {
      backgroundColor: '#f8fafc',
      borderColor: '#e6eaf0',
      color: '#748297',
    }
  }

  const ratio = Math.max(0, Math.min(1, item.latest_stats.sample_count / maxSampleCount.value))
  const alpha = 0.1 + ratio * 0.15

  const colorMap: Record<'low' | 'normal' | 'high', {
    rgb: [number, number, number]
    textColor: string
  }> = {
    low: {
      rgb: [16, 185, 129],
      textColor: '#102033',
    },
    normal: {
      rgb: [59, 130, 246],
      textColor: '#102033',
    },
    high: {
      rgb: [245, 158, 11],
      textColor: '#102033',
    },
  }

  const level = heatLevel(item)
  const { rgb, textColor } = colorMap[level as 'low' | 'normal' | 'high']
  const [r, g, b] = rgb

  return {
    backgroundColor: `rgba(${r}, ${g}, ${b}, ${alpha.toFixed(3)})`,
    borderColor: `rgba(${r}, ${g}, ${b}, 0.42)`,
    color: textColor,
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

function jumpToSelectedHardware(value: string | number | boolean | undefined) {
  if (!value) return
  const id = Number(value)
  if (!Number.isFinite(id)) return
  selectedSearchHardwareId.value = ''
  goToDetail(id)
}

function goToDeals() {
  router.push({ name: 'deals' })
}
</script>

<style scoped>
@import './ops-shared.css';

.dashboard-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 256px minmax(0, 1fr);
  background:
    linear-gradient(90deg, #fbfcff 0, #fbfcff 255px, transparent 255px),
    linear-gradient(180deg, #f8fafc 0%, #eef3f8 100%);
  color: var(--paper-text);
}

.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  padding: 18px 16px;
  border-right: 1px solid var(--paper-border);
  background: rgba(251, 252, 255, 0.96);
  display: flex;
  flex-direction: column;
}

.brand {
  display: flex;
  align-items: center;
  gap: 11px;
  margin-bottom: 30px;
}

.brand-mark {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  background: #101b31;
  box-shadow: 0 10px 20px rgba(16, 27, 49, 0.16);
}

.brand strong {
  display: block;
  font-size: 18px;
  line-height: 1.2;
  letter-spacing: -0.01em;
}

.brand span:not(.brand-mark) {
  display: block;
  color: #7b8798;
  font-size: 11px;
  font-weight: 800;
}

.side-nav {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.nav-item,
.nav-link {
  width: 100%;
  position: relative;
  height: 46px;
  min-height: 46px;
  border: 0;
  border-radius: 0 8px 8px 0;
  background: transparent;
  color: #718198;
  display: grid;
  grid-template-columns: 22px 1fr;
  align-items: center;
  gap: 10px;
  padding: 0 11px 0 16px;
  text-align: left;
  font-size: 13px;
  font-weight: 800;
  white-space: nowrap;
  overflow: hidden;
}

.nav-item {
  cursor: pointer;
}

.nav-link {
  text-decoration: none;
}

.nav-item span,
.nav-link span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.nav-item.active,
.nav-item.selected,
.nav-item:hover,
.nav-link:hover {
  background: linear-gradient(90deg, rgba(16, 27, 49, 0.08), rgba(16, 27, 49, 0.02));
  color: #101b31;
}

.nav-item.active::before,
.nav-link.router-link-active::before {
  content: '';
  position: absolute;
  left: -16px;
  top: 7px;
  width: 4px;
  height: 32px;
  border-radius: 0 999px 999px 0;
  background: #101b31;
}

.system-card {
  margin-top: 18px;
  padding: 16px;
  border: 1px dashed var(--paper-border);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.78);
}

.system-label,
.system-card span:last-child {
  display: block;
  color: #8290a3;
  font-size: 11px;
  font-weight: 700;
}

.system-card strong {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 8px 0 4px;
  color: #203049;
  font-size: 12px;
}

.system-card i,
.activity-item i {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #19c58a;
}

.workspace {
  min-width: 0;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 5;
  height: 64px;
  padding: 0 28px;
  border-bottom: 1px solid var(--paper-border);
  background: rgba(251, 252, 255, 0.92);
  display: flex;
  align-items: center;
  justify-content: center;
}

.search-box {
  width: min(720px, 56vw);
  height: 40px;
  border: 1px solid #e1e7f0;
  border-radius: 8px;
  background: #ffffff;
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
  color: #7f8da1;
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
  color: #17243a;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hardware-option small {
  flex: 0 0 auto;
  color: #8a97aa;
  font-size: 12px;
  font-weight: 800;
}

.main-area {
  padding: 34px 32px 46px;
}

.page-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 26px;
}

.eyebrow {
  margin-bottom: 5px;
  color: #8a9aaf;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.14em;
}

.page-title-row h1 {
  display: flex;
  align-items: center;
  gap: 9px;
  color: #101b31;
  font-size: 30px;
  line-height: 1.15;
  letter-spacing: -0.02em;
}

.page-title-row p:last-child {
  margin-top: 7px;
  color: #64748b;
  font-size: 14px;
}

.crawl-actions {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
}

.primary-action {
  height: 40px;
  border: 0;
  border-radius: 7px;
  background: #101b31;
  color: #ffffff;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 16px;
  font-size: 13px;
  font-weight: 800;
  box-shadow: 0 10px 20px rgba(16, 27, 49, 0.18);
  cursor: pointer;
}

.primary-action:disabled {
  opacity: 0.65;
  cursor: default;
}

.pause-action {
  height: 36px;
  border: 1px solid #d8e0eb;
  border-radius: 7px;
  background: #ffffff;
  color: #516174;
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
  background: #f8fafc;
  color: #243247;
}

.pause-action:disabled {
  opacity: 0.6;
  cursor: default;
}

.loading-panel,
.metric-card,
.crawl-progress-panel,
.focus-panel,
.market-panel,
.activity-panel {
  border: 1px solid var(--paper-border);
  border-radius: 8px;
  background: #ffffff;
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
  color: #142033;
  font-size: 26px;
}

.progress-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-top: 10px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.metric-card {
  min-height: 122px;
  padding: 22px 24px;
  display: flex;
  justify-content: space-between;
  gap: 14px;
}

.metric-card span,
.metric-card small {
  color: #7a8ba1;
  font-size: 12px;
  font-weight: 800;
}

.metric-card strong {
  display: block;
  margin: 8px 0 14px;
  color: #18243a;
  font-size: 29px;
}

.metric-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 23px;
}

.metric-icon.blue { color: #377cf6; background: #e9f1ff; }
.metric-icon.green { color: #08a979; background: #e8f8f1; }
.metric-icon.amber { color: #ff920b; background: #fff4e5; }
.metric-icon.purple { color: #9b5cff; background: #f2e9ff; }

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 330px;
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
  border-bottom: 1px solid #edf1f5;
}

.panel-head h2 {
  font-size: 20px;
  margin-bottom: 8px;
}

.panel-head p {
  color: #65758c;
  font-size: 13px;
}

.fresh-pill {
  align-self: flex-start;
  border-radius: 999px;
  background: #edf4ff;
  color: #3274df;
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
  border-radius: 8px;
  background: #fbfcfe;
  box-shadow: none;
}

.summary-cards span,
.summary-cards small {
  display: block;
  color: #95775e;
  font-size: 12px;
  font-weight: 800;
}

.summary-cards strong {
  display: block;
  margin: 12px 0 8px;
  color: #171717;
  font-size: 26px;
}

.curve-card {
  min-height: 202px;
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  background: #fbfcfe;
  padding: 18px 20px;
}

.curve-head {
  display: flex;
  justify-content: space-between;
  color: #718198;
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

.dot.avg { background: #2e7f8e; }
.dot.mid { background: #c86f3e; }

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
  color: #5d6c80;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 12px;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.view-tabs button.active {
  background: #101b31;
  color: #ffffff;
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
  color: #748297;
  font-size: 12px;
}

.heat-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  color: #64748b;
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

.legend-dot.low { background: #10b981; }
.legend-dot.normal { background: #3b82f6; }
.legend-dot.high { background: #f59e0b; }
.legend-dot.none { background: #cbd5e1; }

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
  color: #66758a;
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
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 10px;
  text-align: left;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.heat-cell:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 18px rgba(16, 27, 49, 0.08);
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
  background: rgba(255, 255, 255, 0.76);
  color: #64748b;
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
  color: #8795a8;
}

.market-table :deep(.el-table__header-wrapper th) {
  background: #f6f8fb;
  color: #1b2940;
  font-weight: 900;
}

.market-table :deep(.el-table__cell) {
  padding: 6px 0;
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

.chip-low { color: #047857; background: #dff8ee; }
.chip-normal { color: #1d4ed8; background: #e8f1ff; }
.chip-high { color: #b45309; background: #fff1d6; }
.chip-none { color: #77859a; background: #eef2f6; }

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(245px, 1fr));
  gap: 14px;
}

.activity-panel {
  padding: 22px;
}

.activity-head h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
}

.activity-list {
  margin-top: 22px;
  display: flex;
  flex-direction: column;
}

.deals-box {
  margin-top: 16px;
  padding: 12px;
  border: 1px solid #e6ebf2;
  border-radius: 8px;
  background: #f8fafc;
}

.activity-empty {
  min-height: 420px;
  margin-top: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #e6ebf2;
  border-radius: 8px;
  background: #f8fafc;
}

.deals-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.deals-head span {
  color: #64748b;
  font-size: 12px;
  font-weight: 900;
}

.deals-head strong {
  color: #16845f;
  font-size: 18px;
}

.deals-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.deal-item {
  min-height: 42px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 8px;
  padding: 9px;
  border-radius: 7px;
  background: #ffffff;
  color: inherit;
  text-decoration: none;
}

.deal-item:hover {
  background: #eef3fa;
}

.deal-item span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  font-weight: 800;
}

.deal-item strong {
  color: #101b31;
  font-size: 13px;
}

.deal-item em {
  min-width: 42px;
  height: 22px;
  border-radius: 999px;
  background: rgba(22, 132, 95, 0.12);
  color: #16845f;
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
  border-bottom: 1px solid #edf1f5;
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
  color: #1b2940;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-item span,
.activity-item small {
  color: #7b8798;
  font-size: 11px;
  line-height: 1.7;
}

.activity-item em {
  border: 1px solid #e0e7f0;
  border-radius: 999px;
  color: #203049;
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
  color: #132033;
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

  .sidebar {
    position: static;
    height: auto;
    align-self: start;
    border-right: 0;
    border-bottom: 1px solid #e4e8ef;
    display: block;
  }

  .side-nav {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(112px, 1fr));
  }

  .system-card {
    margin-top: 18px;
  }

  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .topbar {
    position: static;
    height: auto;
    padding: 16px;
    flex-direction: column;
    align-items: stretch;
  }

  .search-box {
    width: 100%;
  }

  .main-area {
    padding: 20px 14px 28px;
  }

  .page-title-row,
  .panel-head,
  .heatmap-head {
    flex-direction: column;
  }

  .metric-grid,
  .summary-cards {
    grid-template-columns: 1fr;
  }

  .side-nav {
    grid-template-columns: 1fr 1fr;
  }

  .heatmap-row {
    grid-template-columns: 1fr;
  }

  .row-cells {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
