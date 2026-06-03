<template>
  <div class="auth-container">
    <div class="auth-card">
      <h2>Verify Your Email</h2>
      <p class="subtitle">Enter the 6-digit code sent to <strong>{{ email }}</strong></p>
      <form @submit.prevent="handleVerify">
        <div class="form-group">
          <label>Verification Code</label>
          <input
            v-model="code"
            type="text"
            placeholder="Enter 6-digit code"
            required
            autocomplete="one-time-code"
            inputmode="numeric"
          />
        </div>
        <p v-if="errorMsg" class="error">{{ errorMsg }}</p>
        <p v-if="successMsg" class="success">{{ successMsg }}</p>
        <button type="submit" :disabled="loading">
          {{ loading ? 'Verifying...' : 'Verify Email' }}
        </button>
      </form>
      <p class="switch-link">
        Already verified?
        <router-link to="/login">Login</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { confirmRegistration } from '../api/auth'

const route = useRoute()
const router = useRouter()
const email = ref(route.query.email || '')
const code = ref('')
const errorMsg = ref('')
const successMsg = ref('')
const loading = ref(false)

async function handleVerify() {
  errorMsg.value = ''
  successMsg.value = ''
  loading.value = true
  try {
    await confirmRegistration(email.value, code.value)
    successMsg.value = 'Email verified! Redirecting to login...'
    setTimeout(() => router.push('/login'), 1500)
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
  margin: 0 0 8px;
  font-size: 24px;
  color: #1a1a2e;
  text-align: center;
}

.subtitle {
  text-align: center;
  color: #666;
  font-size: 14px;
  margin: 0 0 24px;
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

.success {
  color: #27ae60;
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
</style>
