<template>
  <div class="home">
    <nav>
      <span>Welcome, {{ userEmail }}</span>
      <button @click="handleLogout">Logout</button>
    </nav>
    <main>
      <h1>AussieEcoLense</h1>
      <p>You are logged in. Upload functionality coming soon.</p>
    </main>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { logout } from '../utils/auth'

const userEmail = localStorage.getItem('user_name') || localStorage.getItem('user_email') || 'User'
const router = useRouter()

function handleLogout() {
  logout()
  router.push('/login')
}
</script>

<style scoped>
.home {
  min-height: 100vh;
  background: #f0f4f8;
}

nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 32px;
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  flex-wrap: wrap;
  gap: 12px;
}

nav span {
  font-weight: 500;
  color: #333;
  word-break: break-all;
}

nav button {
  padding: 8px 16px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  white-space: nowrap;
}

nav button:hover {
  background: #c0392b;
}

main {
  padding: 60px 32px;
  text-align: center;
}

h1 {
  font-size: 32px;
  color: #1a1a2e;
}

/* 平板 */
@media (max-width: 600px) {
  nav {
    padding: 12px 16px;
  }

  main {
    padding: 40px 16px;
  }

  h1 {
    font-size: 24px;
  }
}
</style>
