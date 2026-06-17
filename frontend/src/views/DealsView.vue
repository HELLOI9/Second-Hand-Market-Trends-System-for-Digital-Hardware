<template>
  <OpsLayout
    active-nav="deals"
  >
    <template #header>
      <header class="ops-header">
        <div class="ops-header-copy">
          <h1 class="ops-header-title"><el-icon><Aim /></el-icon>今日捡漏</h1>
          <p class="ops-header-subtitle">当天最新一轮有效样本中，价格低于近 30 天历史中位价 15% 以上，每款硬件取最低一条。</p>
        </div>
        <el-button type="primary" :icon="Refresh" :loading="loading" @click="loadDeals">刷新</el-button>
      </header>
    </template>

      <section class="deals-panel">
        <div class="panel-head">
          <span>{{ deals.length }} 个候选 · 按折扣率从高到低排序</span>
        </div>

        <div v-if="deals.length" class="deal-grid">
          <article
            v-for="deal in deals"
            :key="`${deal.hardware_id}-${deal.item_url}-${deal.price}`"
            class="deal-card"
            :class="{ clickable: Boolean(deal.item_url) }"
            @click="deal.item_url && openDeal(deal.item_url)"
          >
            <div class="item-image">
            <img v-if="deal.image_url" :src="deal.image_url" :alt="deal.title" loading="lazy" />
            <div v-else class="image-placeholder">{{ deal.hardware_name.slice(0, 2) }}</div>
            </div>

            <div class="deal-body">
              <span class="hardware-name">{{ deal.hardware_name }}</span>
              <h3>{{ deal.title }}</h3>
              <div class="price-line">
                <strong>¥{{ formatPrice(deal.price) }}</strong>
                <span>{{ deal.area || '暂无地区' }}</span>
                <em>-{{ discountPercent(deal) }}%</em>
              </div>

              <div class="price-meta">
                <div>
                  <span>市场基准</span>
                  <strong>¥{{ formatPrice(deal.baseline_median) }}</strong>
                </div>
                <div>
                  <span>样本日期</span>
                  <strong>{{ deal.snapshot_date }}</strong>
                </div>
              </div>
            </div>

            <footer class="deal-footer">
              <span>{{ deal.seller || '未知卖家' }}</span>
              <el-button v-if="deal.item_url" text @click.stop="openDeal(deal.item_url)">详情</el-button>
              <span v-else>无链接</span>
            </footer>
          </article>
        </div>
        <el-empty v-if="!loading && !deals.length" description="今天暂无捡漏候选" />
      </section>
  </OpsLayout>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Aim, Refresh } from '@element-plus/icons-vue'
import { crawlerApi, dealsApi } from '@/api'
import type { CrawlerStatus, DealItem } from '@/api/types'
import OpsLayout from '@/components/OpsLayout.vue'

const deals = ref<DealItem[]>([])
const crawlerStatus = ref<CrawlerStatus | null>(null)
const loading = ref(false)

onMounted(() => {
  void loadDeals()
  void loadCrawlerStatus()
})

async function loadDeals() {
  loading.value = true
  try {
    deals.value = await dealsApi.today(100)
  } catch {
    ElMessage.error('加载捡漏候选失败')
  } finally {
    loading.value = false
  }
}

async function loadCrawlerStatus() {
  try {
    crawlerStatus.value = await crawlerApi.status()
  } catch {
    crawlerStatus.value = null
  }
}

function formatPrice(price: number): string {
  return price >= 10000 ? `${(price / 10000).toFixed(1)}万` : Math.round(price).toLocaleString()
}

function discountPercent(deal: DealItem): string {
  return Math.round(deal.discount_rate * 100).toString()
}

function openDeal(url: string) {
  window.open(url, '_blank', 'noopener,noreferrer')
}
</script>

<style scoped>
.deals-panel {
  padding: 20px;
}

.panel-head {
  margin-bottom: 14px;
}

.panel-head span {
  display: block;
  color: var(--paper-muted);
  font-size: 12px;
}

.deal-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.deal-card {
  position: relative;
  display: flex;
  min-height: 100%;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--paper-border);
  border-radius: var(--radius-card);
  background: var(--surface-floating);
  box-shadow: var(--paper-shadow);
}

.deal-card::after {
  content: '';
  position: absolute;
  inset: 0;
  background: var(--surface-soft-hover);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.18s ease;
}

.deal-card > * {
  position: relative;
  z-index: 1;
}

.deal-card.clickable {
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}

.deal-card.clickable:hover {
  border-color: var(--paper-border-strong);
  transform: translateY(-2px);
  box-shadow: var(--shadow-card-hover);
}

.deal-card.clickable:hover::after {
  opacity: 1;
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

.deal-body {
  flex: 1;
  padding: 14px 14px 12px;
}

.hardware-name {
  display: block;
  margin-bottom: 6px;
  color: var(--paper-subtle);
  font-size: 12px;
  font-weight: 900;
}

.deal-body h3 {
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

.price-line em {
  margin-left: auto;
  border-radius: var(--radius-pill);
  padding: 4px 9px;
  background: var(--badge-success-bg);
  color: var(--badge-success-text);
  font-size: 12px;
  font-style: normal;
  font-weight: 950;
}

.price-meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 12px;
}

.price-meta div {
  padding: 10px;
}

.price-meta span,
.price-meta strong {
  display: block;
}

.price-meta span {
  color: var(--paper-subtle);
  font-size: 11px;
  font-weight: 900;
}

.price-meta strong {
  margin-top: 4px;
  color: var(--text-strong);
  font-size: 13px;
  font-weight: 950;
}

.deal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 48px;
  border-top: 1px solid var(--paper-border);
  padding: 0 14px;
}

.deal-footer span {
  min-width: 0;
  overflow: hidden;
  color: var(--paper-subtle);
  font-size: 12px;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.deal-footer :deep(.el-button) {
  color: var(--text-strong);
  font-weight: 950;
}

@media (max-width: 1280px) {
  .deal-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 980px) {
  .deal-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .deal-grid {
    grid-template-columns: 1fr;
  }
}
</style>
