<template>
  <div class="auth-container">
    <div class="auth-card">
      <h2>Login</h2>
      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label>Email</label>
          <input
            v-model="email"
            type="email"
            placeholder="Enter your email"
            required
            autocomplete="email"
          />
        </div>
        <div class="form-group">
          <label>Password</label>
          <input
            v-model="password"
            type="password"
            placeholder="Enter your password"
            required
            autocomplete="current-password"
          />
        </div>
        <p v-if="errorMsg" class="error">{{ errorMsg }}</p>
        <button type="submit" :disabled="loading">
          {{ loading ? 'Logging in...' : 'Login' }}
        </button>
      </form>
      <p class="switch-link">
        Don't have an account?
        <router-link to="/register">Register</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '../api/auth'

const email = ref('')
const password = ref('')
const errorMsg = ref('')
const loading = ref(false)
const router = useRouter()

async function handleLogin() {
  errorMsg.value = ''
  loading.value = true
  try {
    await login(email.value, password.value)
    router.push('/home')
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f4f8;
  padding: 16px;
  box-sizing: border-box;
}

.auth-card {
  background: white;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 400px;
  box-sizing: border-box;
}

h2 {
  margin: 0 0 24px;
  font-size: 24px;
  color: #1a1a2e;
  text-align: center;
}

.form-group {
  margin-bottom: 16px;
}

label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  font-weight: 500;
  color: #444;
}

input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 15px;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

input:focus {
  outline: none;
  border-color: #4a90e2;
}

button {
  width: 100%;
  padding: 12px;
  background: #4a90e2;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
  margin-top: 8px;
  transition: background 0.2s;
}

button:hover:not(:disabled) {
  background: #357abd;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error {
  color: #e74c3c;
  font-size: 13px;
  margin: 8px 0;
}

.switch-link {
  text-align: center;
  margin-top: 20px;
  font-size: 14px;
  color: #666;
}

.switch-link a {
  color: #4a90e2;
  text-decoration: none;
  font-weight: 500;
}

.switch-link a:hover {
  text-decoration: underline;
}

/* 平板 */
@media (max-width: 600px) {
  .auth-card {
    padding: 28px 20px;
    border-radius: 8px;
  }

  h2 {
    font-size: 20px;
  }

  input,
  button {
    font-size: 16px; /* 防止 iOS 自动缩放 */
  }
}

/* 手机竖屏 */
@media (max-width: 390px) {
  .auth-container {
    align-items: flex-start;
    padding-top: 40px;
  }

  .auth-card {
    padding: 24px 16px;
    box-shadow: none;
    border-radius: 0;
  }
}
</style>
