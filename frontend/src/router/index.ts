import { createRouter, createWebHistory } from 'vue-router'

const LandingPage = () => import('@/views/LandingPage.vue')
const HomeView = () => import('@/views/HomeView.vue')
const HardwareDetailView = () => import('@/views/HardwareDetailView.vue')
const AlertsView = () => import('@/views/AlertsView.vue')
const CrawlerHealthView = () => import('@/views/CrawlerHealthView.vue')
const HardwarePoolAdminView = () => import('@/views/HardwarePoolAdminView.vue')
const DealsView = () => import('@/views/DealsView.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'landing',
      component: LandingPage,
    },
    {
      path: '/home',
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
