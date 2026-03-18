<template>
  <v-chart :option="chartOption" style="height: 360px;" autoresize />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  MarkLineComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import type { TrendPoint } from '@/api/types'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent, MarkLineComponent])

const props = defineProps<{ trend: TrendPoint[] }>()

const chartOption = computed(() => {
  const dates = props.trend.map(p => p.date)
  const medians = props.trend.map(p => p.median_price)
  const avgs = props.trend.map(p => p.avg_price)
  const mins = props.trend.map(p => p.min_price)
  const maxs = props.trend.map(p => p.max_price)

  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any[]) => {
        const date = params[0].axisValue
        const point = props.trend.find(p => p.date === date)
        if (!point) return ''
        const levelMap: Record<string, string> = { low: '低位', normal: '正常', high: '偏高' }
        return [
          `<b>${date}</b>`,
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
    },
    grid: {
      top: 20,
      left: '8%',
      right: '4%',
      bottom: 40,
    },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLabel: { fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: (val: number) =>
          val >= 10000 ? (val / 10000).toFixed(1) + '万' : val.toLocaleString(),
        fontSize: 11,
      },
    },
    series: [
      {
        name: '中位价',
        type: 'line',
        data: medians,
        smooth: true,
        lineStyle: { width: 3 },
        itemStyle: { color: '#e6a23c' },
        symbol: 'circle',
        symbolSize: 4,
      },
      {
        name: '均价',
        type: 'line',
        data: avgs,
        smooth: true,
        lineStyle: { width: 2, type: 'dashed' },
        itemStyle: { color: '#409eff' },
        symbol: 'none',
      },
      {
        name: '最低价',
        type: 'line',
        data: mins,
        smooth: true,
        lineStyle: { width: 1, type: 'dotted' },
        itemStyle: { color: '#67c23a' },
        symbol: 'none',
      },
      {
        name: '最高价',
        type: 'line',
        data: maxs,
        smooth: true,
        lineStyle: { width: 1, type: 'dotted' },
        itemStyle: { color: '#f56c6c' },
        symbol: 'none',
      },
    ],
  }
})
</script>
