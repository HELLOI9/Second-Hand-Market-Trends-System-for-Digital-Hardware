import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import HardwareDetailView from '@/views/HardwareDetailView.vue'
import AlertsView from '@/views/AlertsView.vue'
import CrawlerHealthView from '@/views/CrawlerHealthView.vue'
import HardwarePoolAdminView from '@/views/HardwarePoolAdminView.vue'
import DealsView from '@/views/DealsView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/hardware/:id',
      name: 'hardware-detail',
      component: HardwareDetailView,
      props: true,
    },
    {
      path: '/admin/hardware',
      name: 'hardware-admin',
      component: HardwarePoolAdminView,
    },
    {
      path: '/alerts',
      name: 'alerts',
      component: AlertsView,
    },
    {
      path: '/deals',
      name: 'deals',
      component: DealsView,
    },
    {
      path: '/health/crawler',
      name: 'crawler-health',
      component: CrawlerHealthView,
    },
  ],
})

export default router
