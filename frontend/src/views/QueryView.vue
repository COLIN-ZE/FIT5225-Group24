<template>
  <div class="page">
    <nav>
      <span class="nav-brand">AussieEcoLense</span>
      <span class="nav-user">Welcome, {{ userEmail }}</span>
      <button class="btn-logout" @click="handleLogout">Logout</button>
    </nav>

    <main>
      <!-- TODO: query content here -->
    </main>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { logout } from '../api/auth'

const userEmail = localStorage.getItem('user_name') || localStorage.getItem('user_email') || 'User'
const router = useRouter()

function handleLogout() {
  logout()
  router.push('/login')
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #f0f4f8;
}

nav {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 32px;
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  flex-wrap: wrap;
}

.nav-brand { font-weight: 700; font-size: 18px; color: #1a1a2e; flex: 1; }
.nav-user  { font-size: 14px; color: #555; }

.btn-logout {
  padding: 7px 16px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}
.btn-logout:hover { background: #c0392b; }

main {
  max-width: 700px;
  margin: 0 auto;
  padding: 48px 24px;
}
</style>
