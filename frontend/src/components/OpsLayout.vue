<template>
  <div class="ops-page" :class="{ 'is-collapsed': isCollapsed }">
    <aside class="ops-sidebar">
      <div class="sidebar-head">
        <RouterLink class="brand" :to="{ name: 'landing' }" :title="isCollapsed ? brandName : undefined">
          <span class="brand-mark">
            <img class="brand-logo" :src="hardpulseLogo" alt="hardpulse logo" />
          </span>
          <div class="brand-copy">
            <strong>{{ brandName }}</strong>
          </div>
        </RouterLink>
        <button
          class="sidebar-toggle"
          type="button"
          :aria-label="isCollapsed ? '展开侧边栏' : '收起侧边栏'"
          :title="isCollapsed ? '展开侧边栏' : '收起侧边栏'"
          @click="toggleSidebar"
        >
          <el-icon><component :is="isCollapsed ? ArrowRightBold : ArrowLeftBold" /></el-icon>
        </button>
      </div>

      <nav class="ops-nav" aria-label="主导航">
        <RouterLink
          v-for="item in navItems"
          :key="item.name"
          :to="{ name: item.name }"
          :class="{ active: activeNav === item.name }"
          :title="isCollapsed ? item.label : undefined"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="system-card" :title="isCollapsed ? (backendOnline ? '后端已连接' : '后端未连接') : undefined">
        <strong>
          <i :class="backendOnline ? 'dot-online' : 'dot-offline'"></i>
          <span>{{ backendOnline ? '后端已连接' : '后端未连接' }}</span>
        </strong>
      </div>
    </aside>

    <section class="ops-workspace">
      <header class="topbar">
        <div class="topbar-inner">
          <div class="search-box">
            <el-icon><Search /></el-icon>
            <el-select
              v-model="selectedSearchHardwareId"
              class="hardware-jump-select"
              filterable
              clearable
              placeholder="搜索商品，快速进入详情"
              :loading="searchLoading"
              @change="jumpToSelectedHardware"
            >
              <el-option
                v-for="item in activeHardwareOptions"
                :key="item.id"
                :label="item.name"
                :value="String(item.id)"
              >
                <div class="hardware-option">
                  <span>{{ item.name }}</span>
                  <small v-if="item.latest_stats">{{ item.latest_stats.sample_count }} 个样本</small>
                  <small v-else>暂无数据</small>
                </div>
              </el-option>
            </el-select>
          </div>
          <slot name="topbar" />
        </div>
      </header>

      <main :class="['ops-main', mainClass]">
        <slot name="header" />
        <slot />
      </main>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { Aim, ArrowLeftBold, ArrowRightBold, Bell, Grid, Monitor, Search, Setting, Tools } from '@element-plus/icons-vue'
import { hardwareApi } from '@/api'
import type { HardwareDetail } from '@/api/types'
import hardpulseLogo from '@/assets/hardpulse-logo.png'

type NavName = 'home' | 'deals' | 'hardware-admin' | 'alerts' | 'crawler-health' | 'config'

const props = withDefaults(defineProps<{
  activeNav: NavName
  brandName?: string
  mainClass?: string
}>(), {
  brandName: 'HARDPULSE',
  mainClass: '',
})

const SIDEBAR_STORAGE_KEY = 'ops-sidebar-collapsed'
const THEME_STORAGE_KEY = 'ops-theme'
const router = useRouter()
const isCollapsed = ref(readStoredSidebarState())
const searchLoading = ref(false)
const selectedSearchHardwareId = ref('')
const groupedHardware = ref<Record<string, HardwareDetail[]>>({})
const backendOnline = ref(true)
let pingTimer: number | undefined

const navItems = computed(() => [
  { name: 'home' as const, label: '监控概览', icon: Grid },
  { name: 'deals' as const, label: '今日捡漏', icon: Aim },
  { name: 'hardware-admin' as const, label: '订阅管理', icon: Setting },
  { name: 'alerts' as const, label: '价格提醒', icon: Bell },
  { name: 'crawler-health' as const, label: '采集健康', icon: Monitor },
  { name: 'config' as const, label: '系统配置', icon: Tools },
])

const activeHardwareOptions = computed(() => {
  return Object.values(groupedHardware.value)
    .flat()
    .filter((item) => item.is_active)
    .sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'))
})

function toggleSidebar() {
  isCollapsed.value = !isCollapsed.value
}

function readStoredSidebarState() {
  if (typeof window === 'undefined') return false
  return window.localStorage.getItem(SIDEBAR_STORAGE_KEY) === '1'
}

async function loadHardwareOptions() {
  searchLoading.value = true
  try {
    groupedHardware.value = await hardwareApi.list()
  } catch {
    groupedHardware.value = {}
  } finally {
    searchLoading.value = false
  }
}

function jumpToSelectedHardware(value: string | number | boolean | undefined) {
  if (!value) return
  selectedSearchHardwareId.value = ''
  void router.push({ name: 'hardware-detail', params: { id: String(value) } })
}

async function pingBackend() {
  try {
    const res = await fetch('/api/../health', { signal: AbortSignal.timeout(4000) })
    backendOnline.value = res.ok
  } catch {
    backendOnline.value = false
  }
}

onMounted(() => {
  void loadHardwareOptions()
  void pingBackend()
  pingTimer = window.setInterval(pingBackend, 30_000)
})

onUnmounted(() => {
  if (pingTimer) window.clearInterval(pingTimer)
})

watch(isCollapsed, (value) => {
  localStorage.setItem(SIDEBAR_STORAGE_KEY, value ? '1' : '0')
})
</script>

<style>
@import '../styles/ops-shared.css';

.ops-workspace {
  min-width: 0;
  height: 100vh;
  overflow-y: auto;
  overscroll-behavior: none;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 15;
  padding: 14px var(--topbar-padding-x);
  border-bottom: var(--layout-topbar-border-bottom);
  background: var(--layout-topbar-bg);
  backdrop-filter: blur(14px);
}

.topbar-inner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.search-box {
  width: min(720px, 100%);
  height: 40px;
  border: 1px solid var(--paper-border);
  border-radius: var(--radius-card);
  background: var(--surface-floating);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 12px;
  color: var(--paper-subtle);
}

.hardware-jump-select {
  flex: 1;
  min-width: 0;
}

.hardware-jump-select :deep(.el-select__wrapper) {
  min-height: 36px;
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
}

.hardware-jump-select :deep(.el-select__placeholder),
.hardware-jump-select :deep(.el-select__input) {
  color: var(--paper-subtle);
  font-size: 13px;
  font-weight: 700;
}

.hardware-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  min-width: 0;
}

.hardware-option span {
  min-width: 0;
  overflow: hidden;
  color: var(--text-strong);
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hardware-option small {
  flex: 0 0 auto;
  color: var(--paper-subtle);
  font-size: 12px;
  font-weight: 800;
}

@media (max-width: 900px) {
  .topbar {
    position: static;
    padding: 16px;
  }

  .topbar-inner {
    flex-direction: column;
    align-items: stretch;
  }

  .search-box {
    width: 100%;
  }
}
</style>
