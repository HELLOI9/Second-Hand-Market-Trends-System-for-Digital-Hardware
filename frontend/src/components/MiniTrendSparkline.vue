<template>
  <div class="sparkline-wrap" :style="sparklineStyle">
    <span v-if="loading" class="placeholder">加载中</span>
    <span v-else-if="!medianPoints.length && !avgPoints.length" class="placeholder">暂无趋势</span>
    <span v-else-if="pointCount < 2" class="placeholder">仅 1 天数据</span>
    <svg v-else :viewBox="`0 0 ${width} ${height}`" preserveAspectRatio="none" class="sparkline-svg">
      <line class="baseline" :x1="PADDING" :x2="width - PADDING" :y1="baselineY" :y2="baselineY" />
      <path
        v-if="avgPath"
        :d="avgPath"
        stroke="#2e7f8e"
        fill="none"
        stroke-width="1.35"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
      <path
        v-if="medianPath"
        :d="medianPath"
        stroke="#c86f3e"
        fill="none"
        stroke-width="1.35"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type HeatLevel = 'low' | 'normal' | 'high' | 'none'

const props = withDefaults(
  defineProps<{
    points: number[]
    avgPoints?: number[]
    medianPoints?: number[]
    loading?: boolean
    level?: HeatLevel
    width?: number
    height?: number
  }>(),
  {
    loading: false,
    level: 'normal',
    width: 180,
    height: 42,
  },
)

const PADDING = 4
const baselineY = props.height - PADDING

const medianPoints = computed(() => {
  return props.medianPoints?.length ? props.medianPoints : props.points
})

const avgPoints = computed(() => props.avgPoints ?? [])

const allValues = computed(() => [...medianPoints.value, ...avgPoints.value])

const pointCount = computed(() => Math.max(medianPoints.value.length, avgPoints.value.length))

function normalizeSeries(points: number[]) {
  if (!points.length) return []

  const min = Math.min(...allValues.value)
  const max = Math.max(...allValues.value)
  const span = max - min || 1
  const innerWidth = props.width - PADDING * 2
  const innerHeight = props.height - PADDING * 2
  const denominator = Math.max(points.length - 1, 1)

  if (points.length === 1) {
    return [{ x: props.width / 2, y: props.height / 2 }]
  }

  return points.map((value, idx) => {
    const x = PADDING + (innerWidth * idx) / denominator
    const y = PADDING + innerHeight - ((value - min) / span) * innerHeight
    return { x, y }
  })
}

function buildPath(points: Array<{ x: number; y: number }>) {
  if (!points.length) return ''

  if (points.length === 1) {
    const { x, y } = points[0]
    return `M ${(x - 10).toFixed(2)} ${y.toFixed(2)} L ${(x + 10).toFixed(2)} ${y.toFixed(2)}`
  }

  let d = `M ${points[0].x.toFixed(2)} ${points[0].y.toFixed(2)}`

  for (let i = 1; i < points.length; i += 1) {
    const prev = points[i - 1]
    const curr = points[i]
    const midX = ((prev.x + curr.x) / 2).toFixed(2)
    d += ` C ${midX} ${prev.y.toFixed(2)}, ${midX} ${curr.y.toFixed(2)}, ${curr.x.toFixed(2)} ${curr.y.toFixed(2)}`
  }

  return d
}

const medianPath = computed(() => buildPath(normalizeSeries(medianPoints.value)))
const avgPath = computed(() => buildPath(normalizeSeries(avgPoints.value)))
const sparklineStyle = computed(() => ({
  height: `${props.height}px`,
  minHeight: `${props.height}px`,
}))

</script>

<style scoped>
.sparkline-wrap {
  width: 100%;
  display: flex;
  align-items: center;
}

.sparkline-svg {
  width: 100%;
  height: 100%;
  display: block;
}

.baseline {
  stroke: rgba(127, 138, 153, 0.28);
  stroke-width: 0.8;
  stroke-dasharray: 2 2.5;
}

.placeholder {
  color: #7f8a99;
  font-size: 12px;
}
</style>
