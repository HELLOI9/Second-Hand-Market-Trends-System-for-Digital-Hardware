<template>
  <div class="ops-page">
    <aside class="ops-sidebar">
      <RouterLink class="brand" :to="{ name: 'home' }">
        <span class="brand-mark"><el-icon><Lightning /></el-icon></span>
        <div>
          <strong>Market Pulse</strong>
          <span>Second-hand Market</span>
        </div>
      </RouterLink>
      <nav class="ops-nav">
        <RouterLink :to="{ name: 'home' }"><el-icon><Grid /></el-icon><span>监控概览</span></RouterLink>
        <RouterLink class="active" :to="{ name: 'deals' }"><el-icon><Aim /></el-icon><span>今日捡漏</span></RouterLink>
        <RouterLink :to="{ name: 'hardware-admin' }"><el-icon><Setting /></el-icon><span>订阅管理</span></RouterLink>
        <RouterLink :to="{ name: 'alerts' }"><el-icon><Bell /></el-icon><span>价格提醒</span></RouterLink>
        <RouterLink :to="{ name: 'crawler-health' }"><el-icon><Monitor /></el-icon><span>爬虫健康</span></RouterLink>
      </nav>

      <div class="system-card">
        <span class="system-label">系统状态</span>
        <strong><i></i>后端实时已连接</strong>
        <span>{{ crawlerStatus?.last_run_date ? `更新于 ${crawlerStatus.last_run_date}` : '等待首次更新' }}</span>
      </div>
    </aside>

    <main class="ops-main">
      <header class="ops-header">
        <div>
          <p>TODAY DEALS</p>
          <h1>今日捡漏</h1>
          <span class="rule-text">样本价低于近 30 天基准中位价 15% 以上时进入候选。</span>
        </div>
        <el-button type="primary" :icon="Refresh" :loading="loading" @click="loadDeals">刷新</el-button>
      </header>

      <section class="deals-panel">
        <div class="panel-head">
          <div>
            <h2>今日可捡漏商品</h2>
            <span>{{ deals.length }} 个候选 · 按折扣率从高到低排序</span>
          </div>
        </div>

        <div v-if="deals.length" class="deal-grid">
          <article v-for="deal in deals" :key="`${deal.hardware_id}-${deal.item_url}-${deal.price}`" class="deal-card">
            <div class="item-image">
              <img v-if="deal.image_url" :src="deal.image_url" :alt="deal.title" loading="lazy" />
              <div v-else class="image-placeholder">{{ deal.hardware_name.slice(0, 2) }}</div>
              <span class="featured-badge">捡漏</span>
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
              <el-button v-if="deal.item_url" text @click="openDeal(deal.item_url)">详情</el-button>
              <span v-else>无链接</span>
            </footer>
          </article>
        </div>
        <el-empty v-if="!loading && !deals.length" description="今天暂无捡漏候选" />
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { crawlerApi, dealsApi } from '@/api'
import type { CrawlerStatus, DealItem } from '@/api/types'

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
@import './ops-shared.css';

.rule-text {
  display: block;
  margin-top: 6px;
  color: #718198;
  font-size: 13px;
  font-weight: 700;
}

.deals-panel {
  padding: 20px;
  border: 1px solid var(--paper-border);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: var(--paper-shadow);
}

.panel-head {
  margin-bottom: 14px;
}

.panel-head h2 {
  font-size: 18px;
}

.panel-head span {
  display: block;
  margin-top: 3px;
  color: #7b8798;
  font-size: 12px;
}

.deal-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.deal-card {
  display: flex;
  min-height: 100%;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #e8edf4;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 12px 24px rgba(16, 27, 49, 0.06);
}

.item-image {
  position: relative;
  aspect-ratio: 1.24 / 1;
  overflow: hidden;
  background: #eef3f8;
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
  color: #7b8798;
  font-size: 32px;
  font-weight: 950;
  background:
    linear-gradient(135deg, rgba(16, 27, 49, 0.08), rgba(22, 132, 95, 0.12)),
    #f6f9fc;
}

.featured-badge {
  position: absolute;
  left: 12px;
  top: 12px;
  height: 26px;
  padding: 0 12px;
  border-radius: 999px;
  background: #55c18c;
  color: #ffffff;
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
  color: #94a1b4;
  font-size: 12px;
  font-weight: 900;
}

.deal-body h3 {
  min-height: 48px;
  display: -webkit-box;
  overflow: hidden;
  color: #1d2738;
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
  color: #d9445d;
  font-size: 24px;
  font-weight: 950;
}

.price-line span {
  color: #9aa7b8;
  font-size: 12px;
  font-weight: 800;
}

.price-line em {
  margin-left: auto;
  border-radius: 999px;
  padding: 4px 9px;
  background: rgba(22, 132, 95, 0.12);
  color: #16845f;
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
  border: 1px solid #edf1f6;
  border-radius: 8px;
  padding: 10px;
  background: #fbfcff;
}

.price-meta span,
.price-meta strong {
  display: block;
}

.price-meta span {
  color: #9aa7b8;
  font-size: 11px;
  font-weight: 900;
}

.price-meta strong {
  margin-top: 4px;
  color: #1d2738;
  font-size: 13px;
  font-weight: 950;
}

.deal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 48px;
  border-top: 1px solid #edf1f6;
  padding: 0 14px;
}

.deal-footer span {
  min-width: 0;
  overflow: hidden;
  color: #94a1b4;
  font-size: 12px;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.deal-footer :deep(.el-button) {
  color: #101b31;
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
