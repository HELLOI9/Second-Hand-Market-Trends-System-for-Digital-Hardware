<template>
  <el-card class="hardware-card" :class="levelClass" shadow="never" @click="emit('click')">
    <div class="card-header">
      <span class="category-pill">{{ categoryLabel }}</span>
      <span class="level-pill" v-if="latestStats">{{ levelLabel }}</span>
    </div>

    <h3 class="name">{{ item.name }}</h3>

    <template v-if="latestStats">
      <div class="price-row">
        <span class="price">¥{{ formatPrice(latestStats.median_price) }}</span>
        <span class="price-label">中位价</span>
      </div>

      <div class="meta-line">
        <span>区间 ¥{{ formatPrice(latestStats.min_price) }} - ¥{{ formatPrice(latestStats.max_price) }}</span>
      </div>
      <div class="meta-line">
        <span>{{ latestStats.sample_count }} 个样本</span>
        <span>{{ latestStats.stat_date }}</span>
      </div>
    </template>

    <div v-else class="no-data">暂无行情数据</div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { HardwareListItem, DailyStats } from '@/api/types'

const props = defineProps<{
  item: HardwareListItem & { latest_stats?: DailyStats | null }
}>()

const emit = defineEmits<{ click: [] }>()

const CATEGORY_LABELS: Record<string, string> = {
  cpu: 'CPU',
  gpu: '显卡',
  memory: '内存',
  ssd: '固态',
}

const latestStats = computed(() => props.item.latest_stats ?? null)

const levelClass = computed(() => {
  switch (latestStats.value?.price_level) {
    case 'low':
      return 'level-low'
    case 'high':
      return 'level-high'
    default:
      return 'level-normal'
  }
})

const categoryLabel = computed(() => CATEGORY_LABELS[props.item.category] ?? props.item.category)

const levelLabel = computed(() => {
  switch (latestStats.value?.price_level) {
    case 'low':
      return '低位'
    case 'high':
      return '偏高'
    default:
      return '正常'
  }
})

function formatPrice(price: number): string {
  return price >= 10000 ? `${(price / 10000).toFixed(1)}万` : Math.round(price).toLocaleString()
}
</script>

<style scoped>
.hardware-card {
  cursor: pointer;
  border-radius: 18px;
  border: 1px solid var(--paper-border);
  background: linear-gradient(170deg, var(--paper-surface), var(--paper-surface-soft));
  box-shadow: 0 10px 22px rgba(31, 41, 55, 0.08);
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.hardware-card:hover {
  transform: translateY(-4px);
  border-color: var(--paper-border-strong);
  box-shadow: 0 14px 28px rgba(31, 41, 55, 0.12);
}

.hardware-card :deep(.el-card__body) {
  padding: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.category-pill,
.level-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.category-pill {
  color: var(--v2);
  background: var(--v-soft-1);
}

.level-pill {
  color: var(--paper-muted);
  background: rgba(83, 97, 112, 0.12);
}

.name {
  font-size: 17px;
  font-weight: 700;
  line-height: 1.35;
  color: var(--paper-text);
  margin-bottom: 12px;
}

.price-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 10px;
}

.price {
  font-size: 28px;
  line-height: 1;
  font-weight: 700;
  color: var(--v2);
}

.price-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--paper-subtle);
}

.meta-line {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--paper-muted);
  line-height: 1.45;
}

.meta-line + .meta-line {
  margin-top: 4px;
}

.no-data {
  color: var(--paper-subtle);
  font-size: 13px;
  font-weight: 600;
  padding: 14px 0 6px;
}

.level-low .level-pill {
  color: var(--v4);
  background: var(--v-soft-3);
}

.level-low .price {
  color: var(--v4);
}

.level-high .level-pill {
  color: var(--v1);
  background: var(--v-soft-1);
}

.level-high .price {
  color: var(--v1);
}

@media (max-width: 900px) {
  .hardware-card {
    border-radius: 14px;
  }

  .name {
    font-size: 16px;
  }

  .price {
    font-size: 25px;
  }
}
</style>
