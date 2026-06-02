<template>
  <div class="auth-container">
    <div class="auth-card">
      <h2>Register</h2>
      <form @submit.prevent="handleRegister">
        <div class="form-row">
          <div class="form-group">
            <label>First Name</label>
            <input
              v-model="firstName"
              type="text"
              placeholder="First name"
              required
              autocomplete="given-name"
            />
          </div>
          <div class="form-group">
            <label>Last Name</label>
            <input
              v-model="lastName"
              type="text"
              placeholder="Last name"
              required
              autocomplete="family-name"
            />
          </div>
        </div>
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
            placeholder="At least 8 characters"
            required
            autocomplete="new-password"
          />
        </div>
        <div class="form-group">
          <label>Confirm Password</label>
          <input
            v-model="confirmPassword"
            type="password"
            placeholder="Repeat your password"
            required
            autocomplete="new-password"
          />
        </div>
        <p v-if="errorMsg" class="error">{{ errorMsg }}</p>
        <p v-if="successMsg" class="success">{{ successMsg }}</p>
        <button type="submit" :disabled="loading">
          {{ loading ? 'Creating account...' : 'Register' }}
        </button>
      </form>
      <p class="switch-link">
        Already have an account?
        <router-link to="/login">Login</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { register } from '../utils/auth'

const firstName = ref('')
const lastName = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const errorMsg = ref('')
const successMsg = ref('')
const loading = ref(false)
const router = useRouter()

async function handleRegister() {
  errorMsg.value = ''
  successMsg.value = ''

  if (password.value.length < 8) {
    errorMsg.value = 'Password must be at least 8 characters'
    return
  }
  if (password.value !== confirmPassword.value) {
    errorMsg.value = 'Passwords do not match'
    return
  }

  loading.value = true
  try {
    await register(email.value, password.value, firstName.value, lastName.value)
    successMsg.value = 'Account created! Check your email for a verification code...'
    setTimeout(() => router.push({ path: '/verify', query: { email: email.value } }), 1500)
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

.form-row {
  display: flex;
  gap: 12px;
}

.form-row .form-group {
  flex: 1;
}

.form-group {
  margin-bottom: 16px;
}

@media (max-width: 360px) {
  .form-row {
    flex-direction: column;
    gap: 0;
  }
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
    font-size: 16px;
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
