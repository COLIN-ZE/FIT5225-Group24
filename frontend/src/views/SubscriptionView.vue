<template>
  <div class="page">
    <nav>
      <span class="nav-brand">AussieEcoLense</span>
      <div class="nav-links">
        <router-link to="/home">Upload</router-link>
        <router-link to="/query">Query</router-link>
        <router-link to="/subscription">Subscriptions</router-link>
      </div>
      <span class="nav-user">Welcome, {{ userName }}</span>
      <button class="btn-logout" @click="handleLogout">Logout</button>
    </nav>

    <main>
      <section class="toolbar">
        <div>
          <h1>Tag Notifications</h1>
        </div>
      </section>

      <!-- Subscribe form -->
      <section class="panel">
        <h2>Subscribe to a Species / Tag</h2>
        <p class="desc">
          Enter a species name or tag. You will receive an email notification
          whenever a matching file is added or updated in the system.
        </p>

        <!-- Quick-pick chips (loaded from system tags) -->
        <div class="chip-row">
          <span class="chip-label">Available tags:</span>
          <span v-if="tagsLoading" class="chip-hint">Loading…</span>
          <span v-else-if="!availableTags.length" class="chip-hint">No tags found in system.</span>
          <button
            v-for="tag in availableTags"
            :key="tag"
            type="button"
            class="chip"
            :disabled="isSubscribed(tag)"
            @click="newTag = tag"
          >{{ tag }}</button>
        </div>

        <form class="sub-form" @submit.prevent="handleSubscribe">
          <input
            v-model="newTag"
            type="text"
            placeholder="e.g. koala, dingo, cassowary …"
            :disabled="subscribing"
          />
          <button class="btn-primary" type="submit" :disabled="!newTag.trim() || subscribing">
            <span v-if="subscribing" class="spinner"></span>
            {{ subscribing ? 'Subscribing…' : 'Subscribe' }}
          </button>
        </form>

        <p v-if="subError" class="error">{{ subError }}</p>
        <p v-if="subSuccess" class="success">{{ subSuccess }}</p>
      </section>

      <!-- Current subscriptions -->
      <section class="panel">
        <div class="list-header">
          <h2>Current Subscriptions</h2>
          <span class="count-badge">{{ subscriptions.length }}</span>
        </div>

        <p v-if="loadError" class="error">{{ loadError }}</p>

        <div v-if="loading" class="state-empty">Loading subscriptions…</div>

        <div v-else-if="!subscriptions.length" class="state-empty">
          You have no active subscriptions. Subscribe to a species above to start receiving notifications.
        </div>

        <ul v-else class="sub-list">
          <li v-for="sub in subscriptions" :key="sub.tag" class="sub-item">
            <div class="sub-info">
              <span class="tag-pill">{{ sub.tag }}</span>
              <span class="sub-date">Subscribed {{ formatDate(sub.createdAt) }}</span>
            </div>
            <button
              class="btn-remove"
              type="button"
              :disabled="removingTag === sub.tag"
              @click="handleUnsubscribe(sub.tag)"
            >
              <span v-if="removingTag === sub.tag" class="spinner spinner-sm"></span>
              {{ removingTag === sub.tag ? 'Removing…' : 'Unsubscribe' }}
            </button>
          </li>
        </ul>
      </section>

      <!-- Info box -->
      <section class="info-box">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2f6fb3" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        <div>
          <strong>How notifications work</strong>
          <p>
            Notifications are delivered to <strong>{{ userEmail }}</strong>.
            Each time a new image or video containing your subscribed species is uploaded and
            processed, you will receive an email with a link to the file.
          </p>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { logout } from '../api/auth'
import {
  getSubscriptions,
  subscribe,
  unsubscribe,
} from '../api/subscription'

const userName = localStorage.getItem('user_name') || localStorage.getItem('user_email') || 'User'
const userEmail = localStorage.getItem('user_email') || ''
const router = useRouter()

const subscriptions = ref([])
const availableTags = ref([])
const newTag = ref('')
const loading = ref(false)
const tagsLoading = ref(false)
const subscribing = ref(false)
const removingTag = ref('')
const loadError = ref('')
const subError = ref('')
const subSuccess = ref('')


function isSubscribed(tag) {
  return subscriptions.value.some(s => s.tag === tag.toLowerCase())
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' })
}

async function loadSubscriptions() {
  loading.value = true
  loadError.value = ''
  try {
    subscriptions.value = await getSubscriptions()
  } catch (e) {
    loadError.value = e.message || 'Failed to load subscriptions.'
  } finally {
    loading.value = false
  }
}

async function loadAvailableTags() {
  tagsLoading.value = true
  try {
    availableTags.value = await getAllTags()
  } catch {
    // silently fall back — chips are optional
  } finally {
    tagsLoading.value = false
  }
}

async function handleSubscribe() {
  if (!newTag.value.trim()) return
  subscribing.value = true
  subError.value = ''
  subSuccess.value = ''
  try {
    const tagName = newTag.value.trim().toLowerCase()
    await subscribe(newTag.value)
    newTag.value = ''
    await loadSubscriptions()
    subSuccess.value = `Subscribed to "${tagName}". You will receive email alerts at ${userEmail || userName}.`
  } catch (e) {
    subError.value = e.message || 'Subscription failed.'
  } finally {
    subscribing.value = false
  }
}

async function handleUnsubscribe(tag) {
  removingTag.value = tag
  subError.value = ''
  subSuccess.value = ''
  try {
    await unsubscribe(tag)
    subscriptions.value = subscriptions.value.filter(s => s.tag !== tag)
    subSuccess.value = `Unsubscribed from "${tag}".`
  } catch (e) {
    subError.value = e.message || 'Failed to unsubscribe.'
  } finally {
    removingTag.value = ''
  }
}

function handleLogout() {
  logout()
  router.push('/login')
}

onMounted(() => {
  loadSubscriptions()
  loadAvailableTags()
})
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #f0f4f8;
}

/* ── Nav ── */
nav {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 32px;
  background: white;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  flex-wrap: wrap;
}
.nav-brand { font-weight: 700; font-size: 18px; color: #1a1a2e; }
.nav-links {
  display: flex;
  gap: 8px;
  flex: 1;
}
.nav-links a {
  padding: 7px 10px;
  border-radius: 6px;
  color: #4b5b6b;
  text-decoration: none;
  font-size: 13px;
  font-weight: 700;
}
.nav-links a.router-link-active {
  background: #e8f2ff;
  color: #2f6fb3;
}
.nav-user { font-size: 14px; color: #555; }
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

/* ── Main ── */
main {
  max-width: 720px;
  margin: 0 auto;
  padding: 40px 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.toolbar h1 { margin: 0; color: #172033; font-size: 26px; }
.toolbar p { margin: 6px 0 0; color: #6b7785; font-size: 14px; }

/* ── Panels ── */
.panel {
  background: white;
  border: 1px solid #e4e9f0;
  border-radius: 10px;
  padding: 24px 28px;
  box-shadow: 0 1px 4px rgba(20,32,48,0.06);
}

.panel h2 {
  margin: 0 0 6px;
  font-size: 17px;
  color: #172033;
}

.desc {
  color: #6b7785;
  font-size: 13px;
  margin: 0 0 16px;
}

/* ── Quick-pick chips ── */
.chip-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}
.chip-label { font-size: 12px; color: #888; font-weight: 600; white-space: nowrap; }
.chip-hint { font-size: 12px; color: #aaa; }
.chip {
  padding: 4px 12px;
  border-radius: 99px;
  border: 1px solid #c8d6e5;
  background: #f8fafc;
  color: #4b5b6b;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.chip:hover:not(:disabled) { border-color: #4a90e2; color: #4a90e2; background: #f0f7ff; }
.chip:disabled { opacity: 0.4; cursor: not-allowed; }

/* ── Subscribe form ── */
.sub-form {
  display: flex;
  gap: 10px;
}
.sub-form input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #d9e2ec;
  border-radius: 7px;
  font: inherit;
  font-size: 14px;
}
.sub-form input:focus { outline: none; border-color: #4a90e2; box-shadow: 0 0 0 3px rgba(74,144,226,0.15); }

/* ── List header ── */
.list-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}
.list-header h2 { margin: 0; font-size: 17px; color: #172033; }
.count-badge {
  background: #e8f2ff;
  color: #2f6fb3;
  font-size: 12px;
  font-weight: 700;
  padding: 2px 9px;
  border-radius: 99px;
}

/* ── Sub list ── */
.sub-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.sub-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid #e4e9f0;
  border-radius: 8px;
  background: #fafbfc;
}
.sub-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}
.tag-pill {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 99px;
  background: #e8f2ff;
  color: #2f6fb3;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
  text-transform: capitalize;
}
.sub-date { font-size: 12px; color: #9aabbb; }

/* ── Buttons ── */
.btn-primary {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background: #2ecc71;
  color: white;
  border: none;
  border-radius: 7px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.2s;
}
.btn-primary:hover:not(:disabled) { background: #27ae60; }
.btn-primary:disabled { opacity: 0.55; cursor: not-allowed; }

.btn-remove {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  background: #fdebea;
  color: #c0392b;
  border: 1px solid #f5c0bb;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s;
}
.btn-remove:hover:not(:disabled) { background: #fbd7d5; }
.btn-remove:disabled { opacity: 0.55; cursor: not-allowed; }

/* ── Spinner ── */
.spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.4);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
}
.spinner-sm {
  border-color: rgba(192,57,43,0.3);
  border-top-color: #c0392b;
  width: 12px;
  height: 12px;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Messages ── */
.error {
  margin-top: 12px;
  padding: 10px 14px;
  background: #fdebea;
  color: #c0392b;
  border-radius: 6px;
  font-size: 13px;
}
.success {
  margin-top: 12px;
  padding: 10px 14px;
  background: #eaf4ec;
  color: #2f7d46;
  border-radius: 6px;
  font-size: 13px;
}

.state-empty {
  text-align: center;
  padding: 32px;
  color: #9aabbb;
  font-size: 14px;
}

/* ── Info box ── */
.info-box {
  display: flex;
  gap: 14px;
  padding: 16px 20px;
  background: #f0f7ff;
  border: 1px solid #c5daf5;
  border-radius: 8px;
  font-size: 13px;
  color: #3a5a80;
}
.info-box svg { flex-shrink: 0; margin-top: 2px; }
.info-box strong { display: block; margin-bottom: 4px; color: #1a3a5c; font-size: 14px; }
.info-box p { margin: 0; line-height: 1.6; }

/* ── Responsive ── */
@media (max-width: 600px) {
  nav { padding: 12px 16px; }
  main { padding: 28px 16px; }
  .panel { padding: 18px 16px; }
  .sub-form { flex-direction: column; }
  .sub-item { flex-direction: column; align-items: flex-start; }
}
</style>
