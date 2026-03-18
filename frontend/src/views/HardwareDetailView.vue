<template>
  <div class="detail-page">
    <!-- 顶部导航 -->
    <div class="header">
      <div class="header-inner">
        <el-button text @click="router.back()">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <h2 class="title">{{ hardware?.name ?? '加载中…' }}</h2>
        <el-tag v-if="hardware?.category" type="info" size="small">
          {{ CATEGORY_LABELS[hardware.category] ?? hardware.category }}
        </el-tag>
      </div>
    </div>

    <div class="content" v-if="hardware">
      <!-- 今日行情卡片 -->
      <div class="stats-row">
        <el-card class="stat-card" v-if="hardware.latest_stats">
          <div class="stat-label">今日中位价</div>
          <div class="stat-value price">¥{{ formatPrice(hardware.latest_stats.median_price) }}</div>
        </el-card>
        <el-card class="stat-card" v-if="hardware.latest_stats">
          <div class="stat-label">价格区间</div>
          <div class="stat-value range">
            ¥{{ formatPrice(hardware.latest_stats.min_price) }}
            <span class="sep">~</span>
            ¥{{ formatPrice(hardware.latest_stats.max_price) }}
          </div>
        </el-card>
        <el-card class="stat-card" v-if="hardware.latest_stats">
          <div class="stat-label">今日样本数</div>
          <div class="stat-value">{{ hardware.latest_stats.sample_count }} 件</div>
        </el-card>
        <el-card class="stat-card" v-if="hardware.latest_stats">
          <div class="stat-label">行情判断</div>
          <div class="stat-value">
            <el-tag :type="levelTagType(hardware.latest_stats.price_level)" size="large">
              {{ LEVEL_LABELS[hardware.latest_stats.price_level] }}
            </el-tag>
          </div>
        </el-card>
      </div>

      <!-- 走势图 -->
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
    </div>

    <div v-else-if="!loading" class="not-found">
      <el-result icon="warning" title="硬件不存在" sub-title="请返回首页重新选择">
        <template #extra>
          <el-button @click="router.push('/')">返回首页</el-button>
        </template>
      </el-result>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { hardwareApi } from '@/api'
import type { HardwareDetail, TrendResponse, PriceLevel } from '@/api/types'
import PriceTrendChart from '@/components/PriceTrendChart.vue'

const props = defineProps<{ id: string }>()
const router = useRouter()

const CATEGORY_LABELS: Record<string, string> = {
  cpu: 'CPU', gpu: '显卡', memory: '内存', ssd: '固态硬盘',
}
const LEVEL_LABELS: Record<PriceLevel, string> = {
  low: '低位', normal: '正常', high: '偏高',
}

const loading = ref(true)
const trendLoading = ref(false)
const hardware = ref<HardwareDetail | null>(null)
const trendData = ref<TrendResponse | null>(null)
const selectedDays = ref<7 | 30 | 90>(30)

function levelTagType(level: PriceLevel) {
  if (level === 'low') return 'success'
  if (level === 'high') return 'danger'
  return 'info'
}

function formatPrice(price: number): string {
  return price >= 10000
    ? (price / 10000).toFixed(1) + '万'
    : Math.round(price).toLocaleString()
}

async function loadTrend() {
  trendLoading.value = true
  try {
    trendData.value = await hardwareApi.trend(Number(props.id), selectedDays.value)
  } catch {
    ElMessage.error('加载走势数据失败')
  } finally {
    trendLoading.value = false
  }
}

onMounted(async () => {
  try {
    const [detail] = await Promise.all([
      hardwareApi.detail(Number(props.id)),
      loadTrend(),
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
}

.header {
  background: #ffffff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-inner {
  max-width: 1200px;
  margin: 0 auto;
  height: 64px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.title {
  font-size: 18px;
  font-weight: 600;
  flex: 1;
}

.content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.stat-card {
  text-align: center;
  padding: 8px 0;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: #303133;
}

.stat-value.price {
  color: #e6a23c;
}

.stat-value.range {
  font-size: 16px;
}

.sep {
  color: #c0c4cc;
  margin: 0 4px;
}

.chart-card :deep(.el-card__header) {
  padding: 12px 16px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.chart-loading,
.chart-empty {
  padding: 24px;
}

.not-found {
  padding-top: 100px;
}
</style>
