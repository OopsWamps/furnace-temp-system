import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import Layout from '@/components/Layout/index.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard/index.vue'),
        meta: { title: '监控面板' }
      },
      {
        path: 'sensors',
        name: 'Sensors',
        component: () => import('@/views/Sensors/index.vue'),
        meta: { title: '传感器视图' }
      },
      {
        path: 'alarms',
        name: 'Alarms',
        component: () => import('@/views/Alarms/index.vue'),
        meta: { title: '异常记录' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
