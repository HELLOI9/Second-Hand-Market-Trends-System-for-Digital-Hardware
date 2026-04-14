<template>
  <div class="sparkline-wrap">
    <span v-if="loading" class="placeholder">加载中</span>
    <span v-else-if="!points.length" class="placeholder">无趋势</span>
    <svg v-else :viewBox="`0 0 ${width} ${height}`" preserveAspectRatio="none" class="sparkline-svg">
      <line class="baseline" :x1="PADDING" :x2="width - PADDING" :y1="baselineY" :y2="baselineY" />
      <path
        class="line"
        :d="linePath"
        :stroke="palette.stroke"
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

const palette = computed(() => {
  switch (props.level) {
    case 'low':
      return {
        stroke: '#2d9b55',
      }
    case 'high':
      return {
        stroke: '#7255c7',
      }
    case 'none':
      return {
        stroke: '#94a3b8',
      }
    default:
      return {
        stroke: '#2f6fb2',
      }
  }
})

const normalized = computed(() => {
  if (!props.points.length) return []

  const min = Math.min(...props.points)
  const max = Math.max(...props.points)
  const span = max - min || 1
  const innerWidth = props.width - PADDING * 2
  const innerHeight = props.height - PADDING * 2
  const denominator = Math.max(props.points.length - 1, 1)

  if (props.points.length === 1) {
    return [{ x: props.width / 2, y: props.height / 2 }]
  }

  return props.points.map((value, idx) => {
    const x = PADDING + (innerWidth * idx) / denominator
    const y = PADDING + innerHeight - ((value - min) / span) * innerHeight
    return { x, y }
  })
})

const linePath = computed(() => {
  if (!normalized.value.length) return ''

  if (normalized.value.length === 1) {
    const { x, y } = normalized.value[0]
    return `M ${(x - 10).toFixed(2)} ${y.toFixed(2)} L ${(x + 10).toFixed(2)} ${y.toFixed(2)}`
  }

  const points = normalized.value
  let d = `M ${points[0].x.toFixed(2)} ${points[0].y.toFixed(2)}`

  for (let i = 1; i < points.length; i += 1) {
    const prev = points[i - 1]
    const curr = points[i]
    const midX = ((prev.x + curr.x) / 2).toFixed(2)
    d += ` C ${midX} ${prev.y.toFixed(2)}, ${midX} ${curr.y.toFixed(2)}, ${curr.x.toFixed(2)} ${curr.y.toFixed(2)}`
  }

  return d
})

</script>

<style scoped>
.sparkline-wrap {
  min-height: 42px;
  display: flex;
  align-items: center;
}

.sparkline-svg {
  width: 100%;
  height: 42px;
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
