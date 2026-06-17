<template>
  <div class="detail-page">
    <header class="detail-header">
      <div class="header-inner">
        <el-button class="back-btn" text @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回列表
        </el-button>

        <div class="title-wrap">
          <h2 class="title">{{ hardware?.name ?? '加载中…' }}</h2>
          <p class="subtitle" v-if="hardware?.latest_stats">
            <template v-if="hardware.stats_is_stale">
              <span class="stale-warning">
                ⚠ 旧数据：{{ hardware.latest_stats.stat_date }}（本轮采集无样本，非当天数据）
              </span>
            </template>
            <template v-else>
              最近数据：{{ hardware.latest_stats.stat_date }} · {{ hardware.latest_stats.sample_count }} 个样本
            </template>
          </p>
        </div>

        <el-button v-if="hardware" class="alert-btn" :icon="Bell" @click="subscribeHardware">
          订阅提醒
        </el-button>
        <el-button v-if="hardware" type="primary" :loading="hwCrawling" @click="startCrawl">
          立即采集
        </el-button>
      </div>
    </header>

    <main class="content" v-if="hardware">
      <section class="stats-row" v-if="hardware.latest_stats">
        <el-card class="stat-card">
          <div class="stat-label">最新中位价</div>
          <div class="stat-value emphasize">¥{{ formatPrice(hardware.latest_stats.median_price) }}</div>
          <div class="stat-date" :class="{ stale: hardware.stats_is_stale }">
            <template v-if="hardware.stats_is_stale">⚠ 旧数据 · 截至 {{ hardware.latest_stats.stat_date }}</template>
            <template v-else>截至 {{ hardware.latest_stats.stat_date }}</template>
          </div>
        </el-card>

        <el-card class="stat-card">
          <div class="stat-label">价格区间</div>
          <div class="stat-value">
            ¥{{ formatPrice(hardware.latest_stats.min_price) }}
            <span class="sep">~</span>
            ¥{{ formatPrice(hardware.latest_stats.max_price) }}
          </div>
        </el-card>

        <el-card class="stat-card">
          <div class="stat-label">样本数</div>
          <div class="stat-value">{{ hardware.latest_stats.sample_count }} 件</div>
        </el-card>

        <el-card class="stat-card">
          <div class="stat-label">行情判断</div>
          <div class="stat-value">
            <el-tag :type="levelTagType(hardware.latest_stats.price_level)" round>
              {{ LEVEL_LABELS[hardware.latest_stats.price_level] }}
            </el-tag>
          </div>
        </el-card>
      </section>

      <!-- 采集进度 -->
      <section v-if="hwCrawling || hwProgress" class="crawl-progress-section">
        <el-card class="crawl-progress-card">
          <div class="progress-row">
            <span class="progress-label">爬取进度</span>
            <el-progress
              :percentage="hwProgress?.crawl_percent ?? 0"
              :stroke-width="14"
              color="#6366f1"
            />
            <span class="progress-pct">
              <template v-if="hwProgress && hwProgress.crawl_total > 0">
                {{ hwProgress.crawl_done }} / {{ hwProgress.crawl_total }}
              </template>
              <template v-else>等待中</template>
            </span>
          </div>
          <div class="progress-row">
            <span class="progress-label">LLM 校验</span>
            <el-progress
              :percentage="hwProgress?.llm_current_total ? Math.round((hwProgress.llm_current_done ?? 0) / hwProgress.llm_current_total * 100) : 0"
              :stroke-width="14"
              color="#10b981"
            />
            <span class="progress-pct">
              <template v-if="hwProgress?.llm_current_total">
                {{ hwProgress.llm_current_done ?? 0 }} / {{ hwProgress.llm_current_total }}
              </template>
              <template v-else>等待中</template>
            </span>
          </div>
        </el-card>
      </section>

      <section v-if="analysisMetrics" class="analysis-overview">
        <el-card class="analysis-hero">
          <div class="analysis-kicker">量化快照</div>
          <h3 class="analysis-title">行情分析结论</h3>
          <p class="analysis-summary">{{ analysisSummary }}</p>
          <div class="analysis-chip-row">
            <span class="analysis-chip" :class="`chip-${analysisMetrics.valuationLevel}`">
              估值：{{ analysisMetrics.valuationLabel }}
            </span>
            <span class="analysis-chip" :class="`chip-${analysisMetrics.trendLevel}`">
              趋势：{{ analysisMetrics.trendLabel }}
            </span>
            <span class="analysis-chip" :class="`chip-${analysisMetrics.riskLevel}`">
              风险：{{ analysisMetrics.riskLabel }}
            </span>
            <span class="analysis-chip confidence-chip" :class="`confidence-${analysisMetrics.confidenceLevel}`">
              可信度：{{ analysisMetrics.confidenceLabel }}
            </span>
          </div>
        </el-card>
      </section>

      <section v-else-if="hasTrendData" class="analysis-overview">
        <el-card class="analysis-hero muted-analysis">
          <div class="analysis-kicker">量化快照</div>
          <h3 class="analysis-title">行情分析等待更多数据</h3>
          <p class="analysis-summary">
            当前只有 {{ analysisPoints.length }} 天历史数据，估值、趋势、波动和样本可信度需要连续采集至少 2 天后生成。
          </p>
        </el-card>
      </section>

      <section v-if="analysisMetrics" class="analysis-grid">
        <el-card class="analysis-card">
          <div class="analysis-card-title">估值定位</div>
          <div class="metric-list">
            <div class="metric-row">
              <span class="metric-key">90天分位</span>
              <strong class="metric-val">{{ formatPercent(analysisMetrics.percentile90) }}</strong>
            </div>
            <div class="metric-row">
              <span class="metric-key">距90天低点</span>
              <strong class="metric-val">{{ formatPercent(analysisMetrics.distanceToLowPct) }}</strong>
            </div>
            <div class="metric-row">
              <span class="metric-key">距90天高点</span>
              <strong class="metric-val">{{ formatPercent(analysisMetrics.distanceToHighPct) }}</strong>
            </div>
            <div class="metric-row">
              <span class="metric-key">观察区间</span>
              <strong class="metric-val">{{ analysisMetrics.coverageDays }} 天</strong>
            </div>
          </div>
        </el-card>

        <el-card class="analysis-card">
          <div class="analysis-card-title">趋势动量</div>
          <div class="metric-list">
            <div class="metric-row">
              <span class="metric-key">7天涨跌</span>
              <strong class="metric-val" :class="trendToneClass(analysisMetrics.change7)">{{ formatSignedPercent(analysisMetrics.change7) }}</strong>
            </div>
            <div class="metric-row">
              <span class="metric-key">30天涨跌</span>
              <strong class="metric-val" :class="trendToneClass(analysisMetrics.change30)">{{ formatSignedPercent(analysisMetrics.change30) }}</strong>
            </div>
            <div class="metric-row">
              <span class="metric-key">90天涨跌</span>
              <strong class="metric-val" :class="trendToneClass(analysisMetrics.change90)">{{ formatSignedPercent(analysisMetrics.change90) }}</strong>
            </div>
            <div class="metric-row">
              <span class="metric-key">斜率(日化)</span>
              <strong class="metric-val" :class="trendToneClass(analysisMetrics.slopePctPerDay)">{{ formatSignedPercent(analysisMetrics.slopePctPerDay, 2) }}</strong>
            </div>
          </div>
        </el-card>

        <el-card class="analysis-card">
          <div class="analysis-card-title">波动风险</div>
          <div class="metric-list">
            <div class="metric-row">
              <span class="metric-key">日波动率</span>
              <strong class="metric-val">{{ formatPercent(analysisMetrics.volatilityPct, 2) }}</strong>
            </div>
            <div class="metric-row">
              <span class="metric-key">最大回撤</span>
              <strong class="metric-val">{{ formatPercent(analysisMetrics.maxDrawdownPct, 2) }}</strong>
            </div>
            <div class="metric-row">
              <span class="metric-key">区间振幅</span>
              <strong class="metric-val">{{ formatPercent(analysisMetrics.rangeAmplitudePct, 1) }}</strong>
            </div>
            <div class="metric-row">
              <span class="metric-key">风险等级</span>
              <strong class="metric-val">{{ analysisMetrics.riskLabel }}</strong>
            </div>
          </div>
        </el-card>

        <el-card class="analysis-card">
          <div class="analysis-card-title">样本可信度</div>
          <div class="metric-list">
            <div class="metric-row">
              <span class="metric-key">近7天平均样本</span>
              <strong class="metric-val">{{ formatCount(analysisMetrics.sampleAvg7) }}</strong>
            </div>
            <div class="metric-row">
              <span class="metric-key">近7天最小样本</span>
              <strong class="metric-val">{{ formatCount(analysisMetrics.sampleMin7) }}</strong>
            </div>
            <div class="metric-row">
              <span class="metric-key">样本波动系数</span>
              <strong class="metric-val">{{ formatPercent(analysisMetrics.sampleCv7Pct, 1) }}</strong>
            </div>
            <div class="metric-row">
              <span class="metric-key">近7天样本变化</span>
              <strong class="metric-val" :class="trendToneClass(analysisMetrics.sampleTrend7)">{{ formatSignedPercent(analysisMetrics.sampleTrend7) }}</strong>
            </div>
          </div>
          <div class="confidence-meter">
            <div class="confidence-track">
              <span class="confidence-fill" :style="{ width: `${analysisMetrics.confidenceScore}%` }"></span>
            </div>
            <span class="confidence-text">{{ analysisMetrics.confidenceScore }}/100</span>
          </div>
          <div
            class="sample-bars"
            v-if="sampleBarData.length"
            :style="{ gridTemplateColumns: `repeat(${sampleBarData.length}, minmax(0, 1fr))` }"
          >
            <div
              v-for="(bar, idx) in sampleBarData"
              :key="`sample-bar-${bar.date}-${idx}`"
              class="sample-bar-item"
              :title="`${bar.date}：${bar.count} 件`"
            >
              <span class="sample-bar" :style="{ height: `${bar.height}%` }"></span>
            </div>
          </div>
          <div class="sample-caption">近14天样本活跃度</div>
        </el-card>
      </section>

      <el-card class="chart-card">
        <template #header>
          <div class="chart-header">
            <span>价格走势</span>
            <el-radio-group v-model="selectedDays" size="small" @change="loadTrend">
              <el-radio-button :value="7">近 7 天</el-radio-button>
              <el-radio-button :value="30">近 30 天</el-radio-button>
              <el-radio-button :value="90">近 90 天</el-radio-button>
            </el-radio-group>
          </div>
        </template>

        <div v-if="trendLoading" class="chart-loading">
          <el-skeleton :rows="6" animated />
        </div>

        <div v-else-if="!trendData?.trend.length" class="chart-empty">
          <el-empty description="暂无历史走势数据" />
        </div>

        <PriceTrendChart v-else :trend="trendData.trend" />
      </el-card>

      <section class="recommend-section">
        <div class="recommend-head">
          <div>
            <p>参考样本</p>
            <h3>精选相关商品</h3>
          </div>
          <span v-if="recommendedSamples.length">{{ recommendedSamples.length }} 个最新有效样本</span>
        </div>

        <div v-if="sampleLoading" class="recommend-loading">
          <el-skeleton :rows="5" animated />
        </div>

        <div v-else-if="recommendedSamples.length" class="recommend-grid">
          <article
            v-for="item in recommendedSamples"
            :key="item.id"
            class="recommend-card clickable"
            @click="openDrawer(item)"
          >
            <div class="item-image">
              <img v-if="item.image_url" :src="item.image_url" :alt="item.title" loading="lazy" />
              <div v-else class="image-placeholder">{{ hardware.name.slice(0, 2) }}</div>
              <span v-if="recommendInfo(item).featured" class="featured-badge">精选</span>
            </div>

            <div class="recommend-body">
              <h4>{{ item.title }}</h4>
              <div class="price-line">
                <strong>¥{{ formatPrice(item.price) }}</strong>
                <span>{{ item.area || '暂无地区' }}</span>
              </div>

              <div class="match-box" :class="{ caution: !recommendInfo(item).recommended }">
                <div class="match-title">
                  <span>{{ recommendInfo(item).recommended ? '推荐关注' : '谨慎观察' }}</span>
                  <strong>匹配度 {{ recommendInfo(item).score }}%</strong>
                </div>
                <div class="match-track">
                  <i :style="{ width: `${recommendInfo(item).score}%` }"></i>
                </div>
              </div>
            </div>

            <footer class="recommend-footer">
              <span>{{ item.seller || '未知卖家' }}</span>
            </footer>
          </article>
        </div>

        <el-empty v-else description="暂无精选相关商品" />
      </section>

      <!-- Sample detail drawer -->
      <el-drawer
        v-model="drawerVisible"
        direction="rtl"
        size="400px"
        :with-header="false"
        class="sample-drawer"
      >
        <template v-if="drawerItem">
          <div class="drawer-topbar">
            <div class="drawer-topbar-left">
              <span v-if="drawerInfo.featured" class="featured-badge">精选</span>
              <span v-else class="drawer-kicker">参考样本</span>
            </div>
            <button class="drawer-close-btn" aria-label="关闭" @click="drawerVisible = false">
              <el-icon><Close /></el-icon>
            </button>
          </div>

          <div class="drawer-hero">
            <img v-if="drawerItem.image_url" :src="drawerItem.image_url" :alt="drawerItem.title" />
            <div v-else class="drawer-hero-placeholder">{{ hardware?.name.slice(0, 2) }}</div>
          </div>

          <div class="drawer-body">
            <h3 class="drawer-title">{{ drawerItem.title }}</h3>

            <div class="drawer-meta-row">
              <strong class="drawer-price">¥{{ formatPrice(drawerItem.price) }}</strong>
              <span class="drawer-area-tag">{{ drawerItem.area || '暂无地区' }}</span>
            </div>

            <div v-if="drawerItem.seller" class="drawer-seller-row">
              <el-icon><User /></el-icon>
              <span>{{ drawerItem.seller }}</span>
            </div>

            <div class="drawer-divider"></div>

            <div class="drawer-analysis" :class="{ caution: !drawerInfo.recommended }">
              <div class="drawer-analysis-header">
                <span class="drawer-analysis-label">{{ drawerInfo.recommended ? '推荐关注' : '谨慎观察' }}</span>
                <strong class="drawer-score-text">匹配度 {{ drawerInfo.score }}%</strong>
              </div>
              <div class="drawer-track">
                <i :style="{ width: `${drawerInfo.score}%` }"></i>
              </div>
              <p class="drawer-reason">{{ drawerInfo.reason }}</p>
            </div>
          </div>

          <div class="drawer-footer">
            <el-button
              v-if="drawerItem.item_url"
              type="primary"
              size="large"
              class="drawer-cta"
              @click="openItem(drawerItem.item_url!)"
            >
              去闲鱼查看
            </el-button>
          </div>
        </template>
      </el-drawer>
    </main>

    <div v-else-if="!loading" class="not-found">
      <el-result icon="warning" title="对象不存在" sub-title="请返回首页重新选择">
        <template #extra>
          <el-button @click="goBack">返回首页</el-button>
        </template>
      </el-result>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Bell, Close, User } from '@element-plus/icons-vue'
import { hardwareApi } from '@/api'
import type { HardwareDetail, TrendResponse, PriceLevel, TrendPoint, HardwareSample, HwCrawlProgressResponse } from '@/api/types'
import PriceTrendChart from '@/components/PriceTrendChart.vue'

const props = defineProps<{ id: string }>()
const router = useRouter()
const route = useRoute()

const VALID_VIEWS = new Set(['heatmap', 'table', 'cards'])

const LEVEL_LABELS: Record<PriceLevel, string> = {
  low: '低位',
  normal: '正常',
  high: '偏高',
}

const loading = ref(true)
const trendLoading = ref(false)
const hardware = ref<HardwareDetail | null>(null)
const trendData = ref<TrendResponse | null>(null)
const analysisTrend = ref<TrendResponse | null>(null)
const samples = ref<HardwareSample[]>([])
const selectedDays = ref<7 | 30 | 90>(30)
const sampleLoading = ref(false)
const drawerVisible = ref(false)
const drawerItem = ref<HardwareSample | null>(null)

// ── 单硬件立即采集 ──────────────────────────────
const hwCrawling = ref(false)
const hwProgress = ref<HwCrawlProgressResponse['progress']>(null)
let crawlPollTimer: ReturnType<typeof setInterval> | null = null

async function startCrawl() {
  if (hwCrawling.value) return
  hwCrawling.value = true
  hwProgress.value = null
  try {
    const res = await hardwareApi.crawlNow(Number(props.id))
    if (res.status === 'already_running' || res.status === 'started') {
      startPolling()
    } else if (res.status === 'rejected') {
      ElMessage.warning(res.message || '请等待当前采集完毕后再进行下一次采集')
      hwCrawling.value = false
    } else {
      hwCrawling.value = false
    }
  } catch {
    ElMessage.error('触发采集失败')
    hwCrawling.value = false
  }
}

function startPolling() {
  stopPolling()
  crawlPollTimer = setInterval(async () => {
    try {
      const res = await hardwareApi.crawlProgress(Number(props.id))
      hwProgress.value = res.progress
      if (!res.running) {
        stopPolling()
        hwCrawling.value = false
        hwProgress.value = null
        // 根据实际状态提示
        if (res.progress?.phase === 'success') {
          ElMessage.success('采集完成')
        } else if (res.progress?.phase === 'failed') {
          ElMessage.error('采集失败，请检查日志')
        } else {
          ElMessage.warning('采集已结束')
        }
        // 刷新数据
        const [detail] = await Promise.all([
          hardwareApi.detail(Number(props.id)),
          loadTrend(),
          loadAnalysisTrend(),
          loadSamples(),
        ])
        hardware.value = detail
      }
    } catch {
      // 忽略单次轮询失败
    }
  }, 2000)
}

function stopPolling() {
  if (crawlPollTimer) {
    clearInterval(crawlPollTimer)
    crawlPollTimer = null
  }
}

onUnmounted(() => {
  stopPolling()
})

const drawerInfo = computed(() =>
  drawerItem.value ? recommendInfo(drawerItem.value) : { score: 0, reason: '', recommended: false, featured: false },
)

function openDrawer(item: HardwareSample) {
  drawerItem.value = item
  drawerVisible.value = true
}

type SignalLevel = 'low' | 'normal' | 'high'

interface AnalysisMetrics {
  coverageDays: number
  percentile90: number
  distanceToLowPct: number
  distanceToHighPct: number
  change7: number | null
  change30: number | null
  change90: number | null
  slopePctPerDay: number
  volatilityPct: number
  maxDrawdownPct: number
  rangeAmplitudePct: number
  sampleAvg7: number
  sampleMin7: number
  sampleCv7Pct: number
  sampleTrend7: number | null
  confidenceScore: number
  valuationLabel: string
  valuationLevel: SignalLevel
  trendLabel: string
  trendLevel: SignalLevel
  riskLabel: string
  riskLevel: SignalLevel
  confidenceLabel: string
  confidenceLevel: SignalLevel
}

function queryString(value: unknown): string | null {
  if (Array.isArray(value)) {
    return typeof value[0] === 'string' ? value[0] : null
  }
  return typeof value === 'string' ? value : null
}

function goBack() {
  const fromView = queryString(route.query.fromView)

  const query: Record<string, string> = {}

  if (fromView && VALID_VIEWS.has(fromView)) {
    query.view = fromView
  }

  router.push({
    name: 'home',
    query,
  })
}

function subscribeHardware() {
  router.push({
    name: 'alerts',
    query: {
      hardwareId: props.id,
    },
  })
}

function levelTagType(level: PriceLevel) {
  if (level === 'low') return 'success'
  if (level === 'high') return 'warning'
  return 'info'
}

function formatPrice(price: number): string {
  return price >= 10000 ? `${(price / 10000).toFixed(1)}万` : Math.round(price).toLocaleString()
}

function formatCount(value: number): string {
  return `${Math.round(value).toLocaleString()} 件`
}

function formatPercent(value: number, digits = 1): string {
  return `${value.toFixed(digits)}%`
}

function formatSignedPercent(value: number | null, digits = 1): string {
  if (value === null || Number.isNaN(value)) return '--'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(digits)}%`
}

function trendToneClass(value: number | null): 'tone-up' | 'tone-down' | 'tone-neutral' {
  if (value === null || Number.isNaN(value)) return 'tone-neutral'
  if (value >= 0.3) return 'tone-up'
  if (value <= -0.3) return 'tone-down'
  return 'tone-neutral'
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
}

function mean(values: number[]): number {
  if (!values.length) return 0
  return values.reduce((sum, v) => sum + v, 0) / values.length
}

function stdDev(values: number[]): number {
  if (values.length < 2) return 0
  const avg = mean(values)
  const variance = values.reduce((sum, v) => sum + (v - avg) ** 2, 0) / values.length
  return Math.sqrt(variance)
}

function calcChange(points: TrendPoint[], lookbackDays: number): number | null {
  if (points.length < 2) return null
  const steps = Math.min(Math.max(lookbackDays - 1, 1), points.length - 1)
  const base = points[points.length - 1 - steps].median_price
  const latest = points[points.length - 1].median_price
  if (base <= 0) return null
  return ((latest - base) / base) * 100
}

function calcSlopePctPerDay(series: number[]): number {
  if (series.length < 2) return 0
  const n = series.length
  let sumX = 0
  let sumY = 0
  let sumXY = 0
  let sumXX = 0
  for (let i = 0; i < n; i += 1) {
    sumX += i
    sumY += series[i]
    sumXY += i * series[i]
    sumXX += i * i
  }
  const denominator = n * sumXX - sumX * sumX
  if (denominator === 0) return 0
  const slope = (n * sumXY - sumX * sumY) / denominator
  const latest = series[series.length - 1]
  if (latest <= 0) return 0
  return (slope / latest) * 100
}

function calcMaxDrawdown(series: number[]): number {
  if (!series.length) return 0
  let peak = series[0]
  let maxDrawdown = 0
  for (const price of series) {
    if (price > peak) peak = price
    if (peak <= 0) continue
    const drawdown = ((peak - price) / peak) * 100
    if (drawdown > maxDrawdown) maxDrawdown = drawdown
  }
  return maxDrawdown
}

function classifyValuation(percentile: number): { label: string; level: SignalLevel } {
  if (percentile <= 20) return { label: '低位区', level: 'low' }
  if (percentile >= 80) return { label: '高位区', level: 'high' }
  return { label: '中位区', level: 'normal' }
}

function classifyTrend(change30: number | null, slopePctPerDay: number): { label: string; level: SignalLevel } {
  const momentum = change30 ?? slopePctPerDay * 30
  if (momentum >= 6 || slopePctPerDay >= 0.08) return { label: '上行', level: 'high' }
  if (momentum <= -6 || slopePctPerDay <= -0.08) return { label: '走弱', level: 'low' }
  return { label: '震荡', level: 'normal' }
}

function classifyRisk(volatilityPct: number, maxDrawdownPct: number): { label: string; level: SignalLevel } {
  if (volatilityPct >= 4 || maxDrawdownPct >= 24) return { label: '高', level: 'high' }
  if (volatilityPct >= 2.2 || maxDrawdownPct >= 12) return { label: '中', level: 'normal' }
  return { label: '低', level: 'low' }
}

function classifyConfidence(score: number): { label: string; level: SignalLevel } {
  if (score >= 75) return { label: '高', level: 'high' }
  if (score >= 45) return { label: '中', level: 'normal' }
  return { label: '低', level: 'low' }
}

const analysisPoints = computed(() => {
  if (analysisTrend.value?.trend?.length) return analysisTrend.value.trend
  return trendData.value?.trend ?? []
})

const hasTrendData = computed(() => analysisPoints.value.length > 0)

const analysisMetrics = computed<AnalysisMetrics | null>(() => {
  const points = analysisPoints.value
  if (points.length < 2) return null

  const medianSeries = points.map((point) => point.median_price).filter((v) => Number.isFinite(v))
  if (medianSeries.length < 2) return null

  const latest = medianSeries[medianSeries.length - 1]
  const low = Math.min(...medianSeries)
  const high = Math.max(...medianSeries)
  const span = high - low
  const percentile90 = span > 0 ? clamp(((latest - low) / span) * 100, 0, 100) : 50
  const distanceToLowPct = low > 0 ? ((latest - low) / low) * 100 : 0
  const distanceToHighPct = high > 0 ? ((high - latest) / high) * 100 : 0
  const rangeAmplitudePct = low > 0 ? (span / low) * 100 : 0

  const change7 = calcChange(points, 7)
  const change30 = calcChange(points, 30)
  const change90 = calcChange(points, 90)
  const slopePctPerDay = calcSlopePctPerDay(medianSeries)

  const returns: number[] = []
  for (let i = 1; i < medianSeries.length; i += 1) {
    const base = medianSeries[i - 1]
    if (base <= 0) continue
    returns.push((medianSeries[i] - base) / base)
  }
  const volatilityPct = stdDev(returns) * 100
  const maxDrawdownPct = calcMaxDrawdown(medianSeries)

  const sampleSeries = points.map((point) => point.sample_count)
  const sampleWindow = sampleSeries.slice(-Math.min(7, sampleSeries.length))
  const sampleAvg7 = mean(sampleWindow)
  const sampleMin7 = sampleWindow.length ? Math.min(...sampleWindow) : 0
  const sampleCv = sampleAvg7 > 0 ? stdDev(sampleWindow) / sampleAvg7 : 0
  const sampleCv7Pct = sampleCv * 100
  const sampleTrend7 = sampleWindow.length >= 2 && sampleWindow[0] > 0
    ? ((sampleWindow[sampleWindow.length - 1] - sampleWindow[0]) / sampleWindow[0]) * 100
    : null

  const confidenceScore = Math.round(
    clamp(sampleAvg7 / 120, 0, 1) * 60
    + clamp(sampleMin7 / 40, 0, 1) * 25
    + clamp(1 - sampleCv, 0, 1) * 15,
  )

  const valuation = classifyValuation(percentile90)
  const trend = classifyTrend(change30, slopePctPerDay)
  const risk = classifyRisk(volatilityPct, maxDrawdownPct)
  const confidence = classifyConfidence(confidenceScore)

  return {
    coverageDays: points.length,
    percentile90,
    distanceToLowPct,
    distanceToHighPct,
    change7,
    change30,
    change90,
    slopePctPerDay,
    volatilityPct,
    maxDrawdownPct,
    rangeAmplitudePct,
    sampleAvg7,
    sampleMin7,
    sampleCv7Pct,
    sampleTrend7,
    confidenceScore,
    valuationLabel: valuation.label,
    valuationLevel: valuation.level,
    trendLabel: trend.label,
    trendLevel: trend.level,
    riskLabel: risk.label,
    riskLevel: risk.level,
    confidenceLabel: confidence.label,
    confidenceLevel: confidence.level,
  }
})

const analysisSummary = computed(() => {
  const metrics = analysisMetrics.value
  if (!metrics) return '暂无足够数据形成稳定结论。'

  const direction = metrics.change30 === null
    ? `趋势呈${metrics.trendLabel}`
    : `近30天${metrics.change30 >= 0 ? '上涨' : '回落'}${Math.abs(metrics.change30).toFixed(1)}%`

  return `当前处于${metrics.valuationLabel}（90天分位 ${metrics.percentile90.toFixed(1)}%），${direction}。`
    + `波动风险${metrics.riskLabel}（日波动 ${metrics.volatilityPct.toFixed(2)}%，最大回撤 ${metrics.maxDrawdownPct.toFixed(2)}%）。`
    + `样本可信度${metrics.confidenceLabel}（近7天均值 ${Math.round(metrics.sampleAvg7)} 件）。`
})

const sampleBarData = computed(() => {
  const points = analysisPoints.value.slice(-14)
  if (!points.length) return []
  const maxSample = Math.max(...points.map((point) => point.sample_count), 1)

  return points.map((point) => ({
    date: point.date,
    count: point.sample_count,
    height: Math.max(12, Math.round((point.sample_count / maxSample) * 100)),
  }))
})

const recommendedSamples = computed(() => {
  const sorted = [...samples.value].sort((a, b) => {
    const infoA = recommendInfo(a)
    const infoB = recommendInfo(b)
    // featured first, then by score descending
    if (infoA.featured !== infoB.featured) return infoA.featured ? -1 : 1
    return infoB.score - infoA.score
  })
  return sorted
})

function recommendInfo(item: HardwareSample): { score: number; reason: string; recommended: boolean; featured: boolean } {
  const median = hardware.value?.latest_stats?.median_price ?? item.price
  const ratio = median > 0 ? item.price / median : 1
  const diff = median > 0 ? ((item.price - median) / median) * 100 : 0
  const title = item.title.toLowerCase()
  const target = hardware.value?.name.toLowerCase() ?? ''
  const targetTokens = target.split(/[\s\-_/]+/).filter((token) => token.length >= 2)
  const matchedTokens = targetTokens.filter((token) => title.includes(token)).length

  const riskyTerms = ['有偿', '教你', '方法', '带你', '定金', '订金', '维修', '负压', '优化', '教程', '链接', '咨询', '配件', '散热', '空盒', '盒子', '外壳']
  const positiveTerms = ['全新', '自用', '原装', '国行', '在保', '保修', '箱说', '包邮', '成色', '正常', '无修', '无拆']
  const riskHits = riskyTerms.filter((term) => title.includes(term))
  const positiveHits = positiveTerms.filter((term) => title.includes(term))

  const identityScore = clamp(
    20
    + (target && title.includes(target) ? 24 : 0)
    + (targetTokens.length ? (matchedTokens / targetTokens.length) * 18 : 8),
    8,
    42,
  )

  let valueScore = 12
  if (ratio <= 0.72) valueScore = 14
  else if (ratio <= 0.86) valueScore = 28
  else if (ratio <= 0.98) valueScore = 24
  else if (ratio <= 1.08) valueScore = 18
  else if (ratio <= 1.18) valueScore = 10
  else valueScore = 4

  const infoScore = (item.image_url ? 8 : 0) + (item.seller ? 6 : 0) + (item.area ? 4 : 0) + (item.item_url ? 3 : 0)
  const qualityScore = clamp(positiveHits.length * 3, 0, 12)
  const riskPenalty = clamp(riskHits.length * 10 + (ratio < 0.55 ? 16 : 0), 0, 40)
  const score = Math.round(clamp(identityScore + valueScore + infoScore + qualityScore - riskPenalty, 18, 96))
  const recommended = score >= 70 && riskHits.length <= 1

  const priceText = diff <= -14
    ? `价格明显低于中位价 ${Math.abs(diff).toFixed(1)}%，但需要重点核对标题和卖家信息。`
    : diff <= -3
      ? `价格低于市场中位约 ${Math.abs(diff).toFixed(1)}%，匹配度和信息完整度较好。`
      : diff <= 8
        ? `价格接近市场中位，建议结合成色、卖家和图片继续判断。`
        : `价格高于市场中位约 ${diff.toFixed(1)}%，性价比一般。`
  const riskText = riskHits.length ? ` 标题命中风险词：${riskHits.slice(0, 2).join('、')}。` : ''
  const positiveText = positiveHits.length ? ` 可参考信息：${positiveHits.slice(0, 2).join('、')}。` : ''

  return {
    score,
    reason: `${priceText}${riskText}${positiveText}`,
    recommended,
    featured: recommended && score >= 76,
  }
}

async function loadTrend() {
  trendLoading.value = true
  try {
    if (selectedDays.value === 90 && analysisTrend.value?.trend?.length) {
      trendData.value = analysisTrend.value
      return
    }
    const response = await hardwareApi.trend(Number(props.id), selectedDays.value)
    trendData.value = response
    if (selectedDays.value === 90) {
      analysisTrend.value = response
    }
  } catch {
    ElMessage.error('加载走势数据失败')
  } finally {
    trendLoading.value = false
  }
}

async function loadAnalysisTrend() {
  try {
    analysisTrend.value = await hardwareApi.trend(Number(props.id), 90)
  } catch {
    analysisTrend.value = null
  }
}

async function loadSamples() {
  sampleLoading.value = true
  try {
    samples.value = await hardwareApi.samples(Number(props.id), 24)
  } catch {
    samples.value = []
  } finally {
    sampleLoading.value = false
  }
}

function openItem(url: string) {
  window.open(url, '_blank', 'noopener,noreferrer')
}

onMounted(async () => {
  try {
    const [detail] = await Promise.all([
      hardwareApi.detail(Number(props.id)),
      loadTrend(),
      loadAnalysisTrend(),
      loadSamples(),
    ])
    hardware.value = detail
  } catch {
    ElMessage.error('加载对象信息失败')
  } finally {
    loading.value = false
  }

  // 恢复进度条：检查该硬件是否有正在进行的采集
  try {
    const progressRes = await hardwareApi.crawlProgress(Number(props.id))
    if (progressRes.running) {
      hwCrawling.value = true
      hwProgress.value = progressRes.progress
      startPolling()
    }
  } catch {
    // 忽略
  }
})
</script>

<style scoped>
.detail-page {
  min-height: 100vh;
  padding: 22px;
  background: var(--layout-page-gradient);
}

.detail-header {
  max-width: 1200px;
  margin: 0 auto;
}

.header-inner {
  background: var(--detail-hero-panel-bg);
  border: 1px solid var(--detail-card-border);
  box-shadow: var(--detail-panel-shadow);
  border-radius: 18px;
  padding: 14px 18px;
  display: flex;
  align-items: center;
  gap: 14px;
  color: var(--detail-hero-text);
}

.back-btn {
  color: var(--detail-hero-text) !important;
  background: var(--detail-hero-button-bg) !important;
  border-radius: 999px;
  border: 1px solid var(--detail-hero-button-border);
  padding: 6px 12px;
}

.back-btn:hover {
  background: var(--detail-hero-button-bg-hover) !important;
}

.alert-btn {
  border-color: var(--detail-hero-button-border);
  background: var(--detail-hero-button-bg);
  color: var(--detail-hero-text);
}

.alert-btn:hover {
  background: var(--detail-hero-button-bg-hover);
  color: var(--detail-hero-text);
}

.title-wrap {
  flex: 1;
}

.title {
  font-size: clamp(18px, 2vw, 28px);
  line-height: 1.2;
  font-weight: 700;
}

.subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: var(--detail-hero-muted);
}

.stale-warning {
  color: #e11d48;
  font-weight: 700;
}

.content {
  max-width: 1200px;
  margin: 18px auto 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
}

.crawl-progress-section {
  margin-top: 2px;
}

.crawl-progress-card {
  border: 1px solid var(--detail-card-border);
  background: var(--detail-panel-bg);
  box-shadow: var(--detail-panel-shadow);
}

.crawl-progress-card :deep(.el-card__body) {
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.progress-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-label {
  flex-shrink: 0;
  width: 68px;
  font-size: 13px;
  font-weight: 700;
  color: var(--paper-text);
}

.progress-row :deep(.el-progress) {
  flex: 1;
}

.progress-pct {
  flex-shrink: 0;
  min-width: 72px;
  text-align: right;
  font-size: 12px;
  font-weight: 700;
  color: var(--paper-muted);
}

.progress-row :deep(.el-progress__text) {
  font-size: 11px !important;
  font-weight: 800;
  color: var(--el-color-primary) !important;
}

.crawl-btn {
  border-color: var(--detail-hero-button-border);
  background: var(--detail-hero-button-bg);
  color: var(--detail-hero-text);
}

.crawl-btn:hover {
  background: var(--detail-hero-button-bg-hover);
  color: var(--detail-hero-text);
}

.analysis-overview {
  margin-top: 2px;
}

.analysis-hero {
  border: 1px solid var(--detail-card-border);
  background: var(--detail-hero-panel-bg);
  box-shadow: var(--detail-panel-shadow);
}

.analysis-hero :deep(.el-card__body) {
  padding: 16px 18px 18px;
}

.muted-analysis {
  background: var(--detail-panel-bg);
}

.analysis-kicker {
  font-size: 11px;
  letter-spacing: 0.14em;
  color: var(--paper-subtle);
  font-weight: 700;
}

.analysis-title {
  margin-top: 6px;
  font-size: 20px;
  color: var(--paper-text);
}

.analysis-summary {
  margin-top: 8px;
  color: var(--paper-muted);
  line-height: 1.65;
  font-size: 14px;
}

.analysis-chip-row {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.analysis-chip {
  display: inline-flex;
  align-items: center;
  height: 28px;
  padding: 0 10px;
  border-radius: var(--radius-pill);
  font-size: 12px;
  font-weight: 700;
  border: 1px solid transparent;
}

.analysis-chip.chip-low {
  color: var(--chip-low-text);
  border-color: rgba(72, 160, 120, 0.36);
  background: var(--chip-low-bg);
}

.analysis-chip.chip-normal {
  color: var(--chip-normal-text);
  border-color: rgba(16, 27, 49, 0.34);
  background: var(--chip-normal-bg);
}

.analysis-chip.chip-high {
  color: var(--chip-high-text);
  border-color: rgba(108, 83, 170, 0.36);
  background: var(--chip-high-bg);
}

.analysis-chip.confidence-chip.confidence-high {
  color: var(--chip-low-text);
  border-color: rgba(72, 160, 120, 0.36);
  background: var(--chip-low-bg);
}

.analysis-chip.confidence-chip.confidence-normal {
  color: var(--chip-high-text);
  border-color: rgba(214, 170, 38, 0.32);
  background: var(--chip-high-bg);
}

.analysis-chip.confidence-chip.confidence-low {
  color: var(--text-danger);
  border-color: rgba(217, 68, 93, 0.26);
  background: rgba(217, 68, 93, 0.1);
}

.analysis-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.analysis-card {
  border: 1px solid var(--detail-card-border);
  background: var(--detail-panel-bg);
  box-shadow: var(--detail-panel-shadow);
}

.analysis-card :deep(.el-card__body) {
  padding: 13px 14px;
}

.analysis-card-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--paper-text);
  margin-bottom: 6px;
}

.metric-list {
  display: flex;
  flex-direction: column;
}

.metric-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  padding: 6px 0;
  border-bottom: 1px dashed var(--detail-row-border);
}

.metric-row:last-child {
  border-bottom: none;
}

.metric-key {
  font-size: 11px;
  color: var(--paper-muted);
}

.metric-val {
  font-size: 12px;
  line-height: 1.3;
  font-weight: 700;
  color: var(--paper-text);
}

.metric-val.tone-up {
  color: var(--text-strong);
}

.metric-val.tone-down {
  color: var(--text-danger);
}

.metric-val.tone-neutral {
  color: var(--paper-muted);
}

.confidence-meter {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.confidence-track {
  position: relative;
  flex: 1;
  height: 6px;
  border-radius: var(--radius-pill);
  background: var(--line-soft);
  overflow: hidden;
}

.confidence-fill {
  position: absolute;
  inset: 0 auto 0 0;
  background: linear-gradient(90deg, var(--accent-primary) 0%, var(--chart-series-avg) 100%);
}

.confidence-text {
  font-size: 12px;
  color: var(--paper-muted);
  font-weight: 700;
}

.sample-bars {
  margin-top: 10px;
  height: 58px;
  display: grid;
  gap: 4px;
  align-items: end;
}

.sample-bar-item {
  height: 100%;
  display: flex;
  align-items: flex-end;
}

.sample-bar {
  width: 100%;
  border-radius: 4px 4px 2px 2px;
  background: linear-gradient(180deg, var(--chart-series-avg) 0%, var(--accent-primary) 100%);
}

.sample-caption {
  margin-top: 6px;
  font-size: 11px;
  color: var(--paper-subtle);
}

.stat-card {
  border: 1px solid var(--detail-card-border);
  background: var(--detail-panel-bg);
  box-shadow: var(--detail-panel-shadow);
}

.stat-card :deep(.el-card__body) {
  padding: 14px;
}

.stat-label {
  font-size: 12px;
  color: var(--paper-muted);
}

.stat-value {
  margin-top: 8px;
  font-size: 22px;
  line-height: 1.2;
  font-weight: 700;
  color: var(--paper-text);
}

.stat-value.emphasize {
  color: var(--text-strong);
}

.stat-date {
  margin-top: 6px;
  font-size: 11px;
  color: var(--paper-subtle);
}

.stat-date.stale {
  color: #e11d48;
  font-weight: 700;
}

.sep {
  color: var(--paper-subtle);
  margin: 0 4px;
}

.chart-card {
  border: 1px solid var(--detail-card-border);
  background: var(--detail-chart-panel-bg);
  box-shadow: var(--detail-panel-shadow);
}

.chart-card :deep(.el-card__header) {
  padding: 12px 16px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 700;
  color: var(--paper-text);
}

.chart-loading,
.chart-empty {
  padding: 24px;
}

.recommend-section {
  border: 1px solid var(--detail-card-border);
  border-radius: var(--radius-card);
  background: var(--detail-panel-bg);
  box-shadow: var(--detail-panel-shadow);
  overflow: hidden;
}

.recommend-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 14px;
  padding: 18px 18px 12px;
}

.recommend-head p {
  color: var(--paper-subtle);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.14em;
}

.recommend-head h3 {
  margin-top: 5px;
  color: var(--paper-text);
  font-size: 20px;
  font-weight: 900;
}

.recommend-head > span {
  color: var(--paper-muted);
  font-size: 12px;
  font-weight: 800;
}

.recommend-loading {
  padding: 18px;
}

.recommend-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  padding: 0 18px 18px;
}

.recommend-card {
  display: flex;
  min-height: 100%;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--detail-card-border);
  border-radius: var(--radius-card);
  background: var(--detail-panel-bg);
  box-shadow: none;
}

.recommend-card.clickable {
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.recommend-card.clickable:hover {
  border-color: var(--accent-primary-soft);
  transform: translateY(-2px);
  box-shadow: var(--shadow-card-hover);
}

.item-image {
  position: relative;
  aspect-ratio: 1.24 / 1;
  overflow: hidden;
  background: var(--paper-bg-soft);
}

.item-image img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--paper-muted);
  font-size: 32px;
  font-weight: 950;
  background:
    linear-gradient(135deg, rgba(16, 27, 49, 0.08), rgba(22, 132, 95, 0.12)),
    var(--surface-sunken);
}

.featured-badge {
  position: absolute;
  left: 12px;
  top: 12px;
  height: 26px;
  padding: 0 12px;
  border-radius: var(--radius-pill);
  background: var(--text-success);
  color: var(--surface-floating);
  font-size: 12px;
  font-weight: 950;
  line-height: 26px;
}

.recommend-body {
  padding: 14px 14px 12px;
  flex: 1;
}

.recommend-body h4 {
  min-height: 48px;
  display: -webkit-box;
  overflow: hidden;
  color: var(--text-strong);
  font-size: 15px;
  font-weight: 900;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.price-line {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-top: 10px;
}

.price-line strong {
  color: var(--text-danger);
  font-size: 24px;
  font-weight: 950;
}

.price-line span {
  color: var(--paper-subtle);
  font-size: 12px;
  font-weight: 800;
}

.match-box {
  margin-top: 12px;
  padding: 12px;
}

.match-box.caution {
  border-color: rgba(217, 68, 93, 0.16);
  background: rgba(217, 68, 93, 0.08);
}

.match-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: var(--badge-success-text);
  font-size: 12px;
  font-weight: 950;
}

.match-box.caution .match-title {
  color: var(--badge-danger-text);
}

.match-title strong {
  color: inherit;
}

.match-track {
  height: 6px;
  margin-top: 8px;
  overflow: hidden;
  border-radius: var(--radius-pill);
  background: var(--line-soft);
}

.match-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--text-success);
}

.match-box.caution .match-track i {
  background: var(--text-danger);
}

.match-box p {
  min-height: 40px;
  margin-top: 9px;
  display: -webkit-box;
  overflow: hidden;
  color: var(--paper-muted);
  font-size: 12px;
  font-weight: 750;
  line-height: 1.65;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.recommend-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 14px;
  border-top: 1px solid var(--paper-border);
  color: var(--paper-subtle);
  font-size: 12px;
  font-weight: 850;
}

.recommend-footer span:first-child {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recommend-footer :deep(.el-button) {
  color: var(--text-strong);
  font-weight: 950;
}

.sample-drawer :deep(.el-drawer) {
  background: var(--detail-panel-bg);
  display: flex;
  flex-direction: column;
}

.sample-drawer :deep(.el-drawer__body) {
  padding: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  flex: 1;
}

.drawer-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--paper-border);
  flex-shrink: 0;
}

.drawer-kicker {
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.12em;
  color: var(--paper-subtle);
}

.drawer-close-btn {
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--control-ghost-border);
  border-radius: 50%;
  background: transparent;
  color: var(--paper-muted);
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
  padding: 0;
}

.drawer-close-btn:hover {
  background: var(--control-ghost-bg-hover);
  color: var(--paper-text);
  border-color: var(--control-ghost-border-hover);
}

.drawer-hero {
  width: 100%;
  aspect-ratio: 16 / 10;
  overflow: hidden;
  background: var(--surface-sunken);
  flex-shrink: 0;
  position: relative;
}

.drawer-hero img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.drawer-hero-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 56px;
  font-weight: 950;
  color: var(--paper-muted);
  background: linear-gradient(135deg, rgba(16, 27, 49, 0.06), rgba(22, 132, 95, 0.10)), var(--surface-sunken);
}

.drawer-hero .featured-badge {
  position: absolute;
  left: 14px;
  top: 14px;
}

.drawer-body {
  flex: 1;
  padding: 20px 20px 0;
  display: flex;
  flex-direction: column;
}

.drawer-title {
  font-size: 16px;
  font-weight: 900;
  color: var(--text-strong);
  line-height: 1.55;
  margin-bottom: 14px;
}

.drawer-meta-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.drawer-price {
  color: var(--text-danger);
  font-size: 30px;
  font-weight: 950;
  line-height: 1;
}

.drawer-area-tag {
  height: 22px;
  padding: 0 10px;
  border-radius: var(--radius-pill);
  background: var(--surface-glass);
  border: 1px solid var(--paper-border);
  color: var(--paper-subtle);
  font-size: 12px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
}

.drawer-seller-row {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--paper-muted);
  font-size: 13px;
  font-weight: 800;
  margin-bottom: 18px;
}

.drawer-divider {
  height: 1px;
  background: var(--paper-border);
  margin-bottom: 18px;
}

.drawer-analysis {
  padding: 16px;
  border-radius: var(--radius-card);
  background: rgba(72, 160, 120, 0.07);
  border: 1px solid rgba(72, 160, 120, 0.18);
}

.drawer-analysis.caution {
  background: rgba(217, 68, 93, 0.07);
  border-color: rgba(217, 68, 93, 0.18);
}

.drawer-analysis-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}

.drawer-analysis-label {
  font-size: 13px;
  font-weight: 950;
  color: var(--badge-success-text);
}

.drawer-analysis.caution .drawer-analysis-label {
  color: var(--badge-danger-text);
}

.drawer-score-text {
  font-size: 13px;
  font-weight: 950;
  color: var(--paper-text);
}

.drawer-track {
  height: 8px;
  border-radius: var(--radius-pill);
  background: var(--line-soft);
  overflow: hidden;
}

.drawer-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--text-success);
  transition: width 0.4s ease;
}

.drawer-analysis.caution .drawer-track i {
  background: var(--text-danger);
}

.drawer-reason {
  margin-top: 12px;
  color: var(--paper-muted);
  font-size: 13px;
  font-weight: 750;
  line-height: 1.75;
}

.drawer-footer {
  position: sticky;
  bottom: 0;
  padding: 16px 20px;
  background: var(--detail-panel-bg);
  border-top: 1px solid var(--paper-border);
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 20px;
}

.drawer-cta {
  width: 100%;
}

.not-found {
  max-width: 1200px;
  margin: 80px auto 0;
}

@media (max-width: 900px) {
  .detail-page {
    padding: 14px;
  }

  .header-inner {
    border-radius: 16px;
    padding: 12px;
    flex-wrap: wrap;
  }

  .chart-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .analysis-grid {
    grid-template-columns: 1fr;
  }

  .recommend-grid {
    grid-template-columns: 1fr;
  }
}

@media (min-width: 901px) and (max-width: 1180px) {
  .analysis-grid,
  .recommend-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
