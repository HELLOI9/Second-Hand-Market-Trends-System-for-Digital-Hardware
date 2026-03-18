<template>
  <div class="home">
    <!-- 顶部 Header -->
    <div class="header">
      <div class="header-inner">
        <h1 class="title">
          <el-icon><Monitor /></el-icon>
          数码硬件二手行情
        </h1>
        <div class="header-actions">
          <span class="last-update" v-if="crawlerStatus?.last_run_date">
            数据更新：{{ crawlerStatus.last_run_date }}
          </span>
          <el-button size="small" :loading="crawling" @click="triggerCrawl" type="primary" plain>
            立即采集
          </el-button>
        </div>
      </div>
    </div>

    <div class="content">
      <!-- 分类 Tab -->
      <el-tabs v-model="activeCategory" class="category-tabs">
        <el-tab-pane v-for="cat in CATEGORY_LABELS" :key="cat.value" :label="cat.label" :name="cat.value">
          <!-- 行情卡片网格 -->
          <div v-if="loading" class="loading-wrap">
            <el-skeleton :rows="4" animated />
          </div>
          <div v-else class="card-grid">
            <HardwareCard
              v-for="item in groupedHardware[cat.value] || []"
              :key="item.id"
              :item="item"
              @click="goToDetail(item.id)"
            />
          </div>
          <el-empty v-if="!loading && !(groupedHardware[cat.value]?.length)" description="暂无数据" />
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { hardwareApi, crawlerApi } from '@/api'
import type { HardwareDetail, CrawlerStatus } from '@/api/types'
import HardwareCard from '@/components/HardwareCard.vue'

const CATEGORY_LABELS = [
  { value: 'cpu',    label: 'CPU' },
  { value: 'gpu',    label: '显卡' },
  { value: 'memory', label: '内存' },
  { value: 'ssd',    label: '固态硬盘' },
]

const router = useRouter()
const loading = ref(true)
const crawling = ref(false)
const activeCategory = ref('cpu')
const groupedHardware = ref<Record<string, HardwareDetail[]>>({})
const crawlerStatus = ref<CrawlerStatus | null>(null)

onMounted(async () => {
  try {
    const [hardware, status] = await Promise.all([
      hardwareApi.list(),
      crawlerApi.status(),
    ])
    groupedHardware.value = hardware
    crawlerStatus.value = status
  } catch {
    ElMessage.error('加载数据失败，请检查后端服务')
  } finally {
    loading.value = false
  }
})

async function triggerCrawl() {
  crawling.value = true
  try {
    await crawlerApi.run()
    ElMessage.success('采集任务已启动，请稍后刷新页面查看数据')
  } catch {
    ElMessage.error('触发采集失败')
  } finally {
    crawling.value = false
  }
}

function goToDetail(id: number) {
  router.push({ name: 'hardware-detail', params: { id } })
}
</script>

<style scoped>
.home {
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
  max-width: 1400px;
  margin: 0 auto;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.title {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.last-update {
  font-size: 13px;
  color: #909399;
}

.content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}

.category-tabs :deep(.el-tabs__header) {
  margin-bottom: 20px;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.loading-wrap {
  padding: 20px;
}
</style>
