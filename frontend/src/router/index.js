import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('../views/Dashboard.vue')
    },
    {
      path: '/accounts',
      name: 'accounts',
      component: () => import('../views/Accounts.vue')
    },
    {
      path: '/tasks',
      name: 'tasks',
      component: () => import('../views/Tasks.vue')
    },
    {
      path: '/windows',
      name: 'windows',
      component: () => import('../views/Windows.vue')
    },
    {
      path: '/video-stats',
      name: 'video-stats',
      component: () => import('../views/VideoStats.vue')
    }
  ]
})

export default router
