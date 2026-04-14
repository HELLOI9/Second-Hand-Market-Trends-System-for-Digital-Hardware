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
            最近数据：{{ hardware.latest_stats.stat_date }} · {{ hardware.latest_stats.sample_count }} 个样本
          </p>
        </div>

        <el-tag v-if="hardware?.category" effect="dark" round>
          {{ CATEGORY_LABELS[hardware.category] ?? hardware.category }}
        </el-tag>
      </div>
    </header>

    <main class="content" v-if="hardware">
      <section class="stats-row" v-if="hardware.latest_stats">
        <el-card class="stat-card">
          <div class="stat-label">今日中位价</div>
          <div class="stat-value emphasize">¥{{ formatPrice(hardware.latest_stats.median_price) }}</div>
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
          <div class="stat-label">今日样本数</div>
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

      <section v-if="analysisMetrics" class="analysis-overview">
        <el-card class="analysis-hero">
          <div class="analysis-kicker">QUANT SNAPSHOT</div>
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
            <span class="analysis-chip" :class="`chip-${analysisMetrics.confidenceLevel}`">
              可信度：{{ analysisMetrics.confidenceLabel }}
            </span>
          </div>
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
    </main>

    <div v-else-if="!loading" class="not-found">
      <el-result icon="warning" title="硬件不存在" sub-title="请返回首页重新选择">
        <template #extra>
          <el-button @click="goBack">返回首页</el-button>
        </template>
      </el-result>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { hardwareApi } from '@/api'
import type { HardwareDetail, TrendResponse, PriceLevel, TrendPoint } from '@/api/types'
import PriceTrendChart from '@/components/PriceTrendChart.vue'

const props = defineProps<{ id: string }>()
const router = useRouter()
const route = useRoute()

const CATEGORY_LABELS: Record<string, string> = {
  cpu: 'CPU',
  gpu: '显卡',
  memory: '内存',
  ssd: '固态硬盘',
}
const VALID_CATEGORIES = new Set(Object.keys(CATEGORY_LABELS))
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
const selectedDays = ref<7 | 30 | 90>(30)

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
  const fromCategory = queryString(route.query.fromCategory)
  const fromView = queryString(route.query.fromView)

  const query: Record<string, string> = {}

  if (fromCategory && VALID_CATEGORIES.has(fromCategory)) {
    query.category = fromCategory
  }

  if (fromView && VALID_VIEWS.has(fromView)) {
    query.view = fromView
  }

  router.push({
    name: 'home',
    query,
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

onMounted(async () => {
  try {
    const [detail] = await Promise.all([
      hardwareApi.detail(Number(props.id)),
      loadTrend(),
      loadAnalysisTrend(),
    ])
    hardware.value = detail
  } catch {
    ElMessage.error('加载硬件信息失败')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.detail-page {
  min-height: 100vh;
  padding: 22px;
}

.detail-header {
  max-width: 1200px;
  margin: 0 auto;
}

.header-inner {
  background: linear-gradient(136deg, #2f4b7c 0%, #355f8d 52%, #2a788e 100%);
  border: 1px solid rgba(202, 218, 235, 0.62);
  box-shadow: var(--paper-shadow);
  border-radius: 20px;
  padding: 14px 18px;
  display: flex;
  align-items: center;
  gap: 14px;
  color: #eef4ff;
}

.back-btn {
  color: #f3f7fb;
  border-radius: 999px;
  border: 1px solid rgba(229, 237, 245, 0.5);
  padding: 6px 12px;
}

.back-btn:hover {
  background: rgba(255, 255, 255, 0.16);
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
  color: rgba(236, 242, 248, 0.92);
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

.analysis-overview {
  margin-top: 2px;
}

.analysis-hero {
  border-radius: 16px;
  border: 1px solid var(--paper-border);
  background:
    radial-gradient(circle at 8% -40%, rgba(65, 68, 135, 0.16) 0%, transparent 42%),
    radial-gradient(circle at 92% 140%, rgba(42, 120, 142, 0.13) 0%, transparent 46%),
    linear-gradient(160deg, #fbfcfe 0%, #f5f8fb 100%);
  box-shadow: 0 12px 24px rgba(31, 41, 55, 0.07);
}

.analysis-hero :deep(.el-card__body) {
  padding: 16px 18px 18px;
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
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid transparent;
}

.analysis-chip.chip-low {
  color: #1d5f3a;
  border-color: rgba(72, 160, 120, 0.36);
  background: rgba(72, 160, 120, 0.14);
}

.analysis-chip.chip-normal {
  color: #1c4c87;
  border-color: rgba(61, 112, 184, 0.36);
  background: rgba(61, 112, 184, 0.14);
}

.analysis-chip.chip-high {
  color: #5a3d95;
  border-color: rgba(108, 83, 170, 0.36);
  background: rgba(108, 83, 170, 0.14);
}

.analysis-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.analysis-card {
  border-radius: 14px;
  border: 1px solid var(--paper-border);
  box-shadow: 0 10px 20px rgba(31, 41, 55, 0.06);
}

.analysis-card :deep(.el-card__body) {
  padding: 14px 16px;
}

.analysis-card-title {
  font-size: 14px;
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
  padding: 7px 0;
  border-bottom: 1px dashed rgba(127, 138, 153, 0.26);
}

.metric-row:last-child {
  border-bottom: none;
}

.metric-key {
  font-size: 12px;
  color: var(--paper-muted);
}

.metric-val {
  font-size: 13px;
  line-height: 1.3;
  font-weight: 700;
  color: var(--paper-text);
}

.metric-val.tone-up {
  color: #1f6fb9;
}

.metric-val.tone-down {
  color: #8b4f5a;
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
  border-radius: 999px;
  background: rgba(193, 200, 209, 0.5);
  overflow: hidden;
}

.confidence-fill {
  position: absolute;
  inset: 0 auto 0 0;
  background: linear-gradient(90deg, #3c67a3 0%, #2a788e 60%, #22a884 100%);
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
  background: linear-gradient(180deg, rgba(61, 112, 184, 0.92) 0%, rgba(42, 120, 142, 0.78) 100%);
}

.sample-caption {
  margin-top: 6px;
  font-size: 11px;
  color: var(--paper-subtle);
}

.stat-card {
  border-radius: 14px;
  border: 1px solid var(--paper-border);
  box-shadow: 0 8px 18px rgba(31, 41, 55, 0.07);
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
  color: var(--v2);
}

.sep {
  color: var(--paper-subtle);
  margin: 0 4px;
}

.chart-card {
  border-radius: 16px;
  border: 1px solid var(--paper-border);
  box-shadow: 0 12px 26px rgba(31, 41, 55, 0.08);
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
}
</style>
