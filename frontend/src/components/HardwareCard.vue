<template>
  <el-card class="hardware-card" shadow="hover" @click="emit('click')">
    <div class="card-header">
      <span class="name">{{ item.name }}</span>
      <el-tag :type="levelTagType" size="small" v-if="latestStats">
        {{ levelLabel }}
      </el-tag>
    </div>

    <template v-if="latestStats">
      <div class="price-row">
        <span class="price">¥{{ formatPrice(latestStats.median_price) }}</span>
        <span class="price-label">中位价</span>
      </div>
      <div class="meta">
        <span>¥{{ formatPrice(latestStats.min_price) }} ~ ¥{{ formatPrice(latestStats.max_price) }}</span>
        <span>{{ latestStats.sample_count }} 个样本</span>
      </div>
      <div class="date">{{ latestStats.stat_date }}</div>
    </template>

    <div v-else class="no-data">
      <el-text type="info" size="small">暂无行情数据</el-text>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { HardwareListItem, DailyStats } from '@/api/types'

const props = defineProps<{
  item: HardwareListItem & { latest_stats?: DailyStats | null }
}>()

const emit = defineEmits<{ click: [] }>()

const latestStats = computed(() => props.item.latest_stats ?? null)

const levelTagType = computed(() => {
  switch (latestStats.value?.price_level) {
    case 'low': return 'success'
    case 'high': return 'danger'
    default: return 'info'
  }
})

const levelLabel = computed(() => {
  switch (latestStats.value?.price_level) {
    case 'low': return '低位'
    case 'high': return '偏高'
    default: return '正常'
  }
})

function formatPrice(price: number): string {
  return price >= 10000
    ? (price / 10000).toFixed(1) + '万'
    : Math.round(price).toLocaleString()
}
</script>

<style scoped>
.hardware-card {
  cursor: pointer;
  transition: transform 0.15s;
}

.hardware-card:hover {
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.name {
  font-weight: 600;
  font-size: 15px;
  color: #303133;
}

.price-row {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 6px;
}

.price {
  font-size: 24px;
  font-weight: 700;
  color: #e6a23c;
}

.price-label {
  font-size: 12px;
  color: #909399;
}

.meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #606266;
  margin-bottom: 6px;
}

.date {
  font-size: 11px;
  color: #c0c4cc;
  text-align: right;
}

.no-data {
  padding: 16px 0;
  text-align: center;
}
</style>
