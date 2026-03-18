import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import HardwareDetailView from '@/views/HardwareDetailView.vue'

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
  ],
})

export default router
