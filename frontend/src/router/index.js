import { createRouter, createWebHistory } from 'vue-router'
import { isLoggedIn } from '../api/auth'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import VerifyView from '../views/VerifyView.vue'
import HomeView from '../views/HomeView.vue'
import QueryView from '../views/QueryView.vue'

const routes = [
  { path: '/', redirect: '/home' },
  { path: '/login', component: LoginView },
  { path: '/register', component: RegisterView },
  { path: '/verify', component: VerifyView },
  { path: '/home', component: HomeView, meta: { requiresAuth: true } },
  { path: '/query', component: QueryView, meta: { requiresAuth: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !isLoggedIn()) {
    return '/login'
  }
})

export default router
