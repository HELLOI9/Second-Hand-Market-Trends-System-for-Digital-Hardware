<template>
  <div class="trend-chart-wrap">
    <div v-if="isSinglePoint" class="single-day-note">
      当前只有 1 天历史数据，先展示当日价格点；连续采集 2 天以上后会形成趋势线。
    </div>
    <v-chart :option="chartOption" style="height: 380px" autoresize />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import type { TrendPoint } from '@/api/types'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

const props = defineProps<{ trend: TrendPoint[] }>()
type TooltipParam = { dataIndex?: number }

const isSinglePoint = computed(() => props.trend.length === 1)
const themeVersion = ref(0)
let themeObserver: MutationObserver | null = null

function formatPriceTick(val: number): string {
  return val >= 10000 ? `${(val / 10000).toFixed(1)}万` : Math.round(val).toLocaleString()
}

function toTimestamp(dateStr: string): number {
  return new Date(`${dateStr}T00:00:00`).getTime()
}

function readThemeVar(name: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return value || fallback
}

const themePalette = computed(() => {
  themeVersion.value
  return {
    median: readThemeVar('--chart-series-median', '#1d4e89'),
    avg: readThemeVar('--chart-series-avg', '#2f7ed8'),
    min: readThemeVar('--chart-series-min', '#2f9e44'),
    max: readThemeVar('--chart-series-max', '#7b5fc9'),
    axis: readThemeVar('--chart-axis', '#536170'),
    grid: readThemeVar('--chart-grid', 'rgba(127, 138, 153, 0.22)'),
    crosshair: readThemeVar('--chart-crosshair', '#7f8a99'),
    tooltipBg: readThemeVar('--chart-tooltip-bg', 'rgba(255, 255, 255, 0.98)'),
    tooltipBorder: readThemeVar('--chart-tooltip-border', '#c1c8d1'),
    tooltipText: readThemeVar('--chart-tooltip-text', '#1f2937'),
  }
})

onMounted(() => {
  themeObserver = new MutationObserver(() => {
    themeVersion.value += 1
  })
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme', 'style', 'class'],
  })
})

onBeforeUnmount(() => {
  themeObserver?.disconnect()
  themeObserver = null
})

const chartOption = computed(() => {
  const palette = themePalette.value
  const timestamps = props.trend.map((p) => toTimestamp(p.date))

  const medians = props.trend.map((p, idx) => [timestamps[idx], p.median_price] as const)
  const avgs = props.trend.map((p, idx) => [timestamps[idx], p.avg_price] as const)
  const mins = props.trend.map((p, idx) => [timestamps[idx], p.min_price] as const)
  const maxs = props.trend.map((p, idx) => [timestamps[idx], p.max_price] as const)

  const allPrices = props.trend.flatMap((point) => [point.min_price, point.max_price, point.median_price, point.avg_price])

  const rawMin = allPrices.length ? Math.min(...allPrices) : 0
  const rawMax = allPrices.length ? Math.max(...allPrices) : 0
  const samePrice = rawMin === rawMax
  const padding = samePrice ? Math.max(rawMin * 0.05, 1) : (rawMax - rawMin) * 0.12

  const yMinBase = Math.max(0, rawMin - padding)
  const yMaxBase = rawMax + padding
  const yMin = yMinBase >= 1000 ? Math.floor(yMinBase / 50) * 50 : Math.floor(yMinBase)
  const yMax = yMaxBase >= 1000 ? Math.ceil(yMaxBase / 50) * 50 : Math.ceil(yMaxBase)

  const onePoint = timestamps.length === 1
  const xMin = onePoint ? timestamps[0] - 36 * 60 * 60 * 1000 : 'dataMin'
  const xMax = onePoint ? timestamps[0] + 36 * 60 * 60 * 1000 : 'dataMax'

  return {
    color: [palette.median, palette.avg, palette.min, palette.max],
    animationDuration: 380,
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        lineStyle: {
          type: 'dashed',
          color: palette.crosshair,
        },
      },
      backgroundColor: palette.tooltipBg,
      borderColor: palette.tooltipBorder,
      borderWidth: 1,
      textStyle: { color: palette.tooltipText },
      formatter: (params: TooltipParam[]) => {
        if (!params.length) return ''
        const dataIndex = params[0].dataIndex as number
        const point = props.trend[dataIndex]
        if (!point) return ''
        const levelMap: Record<string, string> = { low: '低位', normal: '正常', high: '偏高' }
        return [
          `<b>${point.date}</b>`,
          `中位价：¥${Math.round(point.median_price).toLocaleString()}`,
          `均价：¥${Math.round(point.avg_price).toLocaleString()}`,
          `区间：¥${Math.round(point.min_price).toLocaleString()} ~ ¥${Math.round(point.max_price).toLocaleString()}`,
          `样本：${point.sample_count} 件`,
          `行情：${levelMap[point.price_level] ?? point.price_level}`,
        ].join('<br/>')
      },
    },
    legend: {
      data: ['中位价', '均价', '最低价', '最高价'],
      bottom: 0,
      itemWidth: 14,
      itemHeight: 8,
      textStyle: {
        color: palette.axis,
        fontWeight: 600,
      },
    },
    grid: {
      top: 18,
      left: '7%',
      right: '3%',
      bottom: 42,
      containLabel: true,
    },
    xAxis: {
      type: 'time',
      min: xMin,
      max: xMax,
      axisLine: { lineStyle: { color: palette.grid } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: {
        color: palette.axis,
        fontSize: 11,
        hideOverlap: true,
        formatter: (value: number) => {
          const d = new Date(value)
          return `${d.getMonth() + 1}-${d.getDate()}`
        },
      },
    },
    yAxis: {
      type: 'value',
      min: yMin,
      max: yMax,
      splitNumber: 5,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: {
        lineStyle: {
          color: palette.grid,
          type: 'dashed',
        },
      },
      axisLabel: {
        formatter: formatPriceTick,
        color: palette.axis,
        fontSize: 11,
      },
    },
    series: [
      {
        name: '中位价',
        type: 'line',
        data: medians,
        smooth: false,
        lineStyle: { width: 3.2 },
        areaStyle: { color: `${palette.median}1a` },
        showSymbol: onePoint,
        symbol: 'circle',
        symbolSize: onePoint ? 12 : 7,
        emphasis: { focus: 'series' },
        z: 4,
      },
      {
        name: '均价',
        type: 'line',
        data: avgs,
        smooth: false,
        lineStyle: { width: 2.4, type: 'dashed' },
        showSymbol: onePoint,
        symbol: 'circle',
        symbolSize: onePoint ? 11 : 6,
        emphasis: { focus: 'series' },
        z: 3,
      },
      {
        name: '最低价',
        type: 'line',
        data: mins,
        smooth: false,
        lineStyle: { width: 1.5, type: 'dotted' },
        showSymbol: onePoint,
        symbol: 'circle',
        symbolSize: onePoint ? 10 : 5,
        emphasis: { focus: 'series' },
        z: 2,
      },
      {
        name: '最高价',
        type: 'line',
        data: maxs,
        smooth: false,
        lineStyle: { width: 1.7, type: 'dashdot' },
        showSymbol: onePoint,
        symbol: 'circle',
        symbolSize: onePoint ? 10 : 5,
        emphasis: { focus: 'series' },
        z: 1,
      },
    ],
  }
})
</script>

<style scoped>
.trend-chart-wrap {
  position: relative;
}

.single-day-note {
  position: absolute;
  top: 2px;
  left: 7%;
  z-index: 1;
  border-radius: 999px;
  background: var(--chart-note-bg);
  color: var(--paper-muted);
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 700;
}
</style>
