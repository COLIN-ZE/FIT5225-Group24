<template>
  <div class="page">
    <nav>
      <span class="nav-brand">AussieEcoLense</span>
      <div class="nav-links">
        <router-link to="/home">Upload</router-link>
        <router-link to="/query">Query</router-link>
        <router-link to="/subscription">Subscriptions</router-link>
      </div>
      <span class="nav-user">Welcome, {{ userEmail }}</span>
      <button class="btn-logout" @click="handleLogout">Logout</button>
    </nav>

    <main>
      <section class="toolbar">
        <div>
          <h1>Detection Query</h1>
          <p>{{ mockLabel }}</p>
        </div>
        <button class="btn-refresh" type="button" @click="runQuery">Refresh</button>
      </section>

      <section class="query-panel">
        <div class="mode-tabs" role="tablist" aria-label="Query mode">
          <button
            v-for="mode in queryModes"
            :key="mode.value"
            type="button"
            class="mode-tab"
            :class="{ active: queryType === mode.value }"
            @click="setQueryType(mode.value)"
          >
            {{ mode.label }}
          </button>
        </div>

        <form class="query-form" @submit.prevent="runQuery">
          <template v-if="queryType === 'count'">
            <label>
              Min
              <input v-model="minCount" type="number" min="0" placeholder="0" />
            </label>
            <label>
              Max
              <input v-model="maxCount" type="number" min="0" placeholder="Any" />
            </label>
          </template>

          <label v-else class="wide-field">
            {{ activePlaceholder.label }}
            <input v-model="queryValue" type="text" :placeholder="activePlaceholder.placeholder" />
          </label>

          <button class="btn-primary" type="submit" :disabled="loading">
            {{ loading ? 'Searching...' : 'Search' }}
          </button>
        </form>
      </section>

      <section v-if="selectedIds.length" class="batch-bar">
        <strong>{{ selectedIds.length }} selected</strong>
        <input
          v-model="batchTagText"
          type="text"
          placeholder="Batch tags, comma separated"
          @keydown.enter.prevent="handleBatchTags"
        />
        <button type="button" class="btn-secondary" @click="handleBatchTags">Add Tags</button>
        <button type="button" class="btn-ghost" @click="clearSelection">Clear</button>
      </section>

      <p v-if="message" class="message">{{ message }}</p>
      <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

      <section class="results-header">
        <h2>Results</h2>
        <span>{{ results.length }} files</span>
      </section>

      <section v-if="loading" class="state-panel">Loading detections...</section>
      <section v-else-if="!results.length" class="state-panel">No matching detections found.</section>
      <section v-else class="result-list">
        <ResultCard
          v-for="record in results"
          :key="record.fileId"
          :record="record"
          :selected="selectedIds.includes(record.fileId)"
          @toggle-select="toggleSelect"
          @preview="openPreview"
          @add-tags="handleAddTags"
          @delete="confirmDelete"
        />
      </section>
    </main>

    <div v-if="previewRecord" class="modal-backdrop" @click.self="closePreview">
      <div class="modal">
        <button class="modal-close" type="button" @click="closePreview">Close</button>
        <div class="preview-media">
          <img v-if="previewRecord.imageUrl || previewRecord.thumbnailUrl" :src="previewRecord.imageUrl || previewRecord.thumbnailUrl" alt="" />
          <span v-else>No preview available</span>
        </div>
        <div class="preview-info">
          <h2>{{ previewRecord.fileName }}</h2>
          <p>{{ previewRecord.fileKey }}</p>
          <dl>
            <div>
              <dt>Species</dt>
              <dd>{{ previewRecord.species }}</dd>
            </div>
            <div>
              <dt>Common name</dt>
              <dd>{{ previewRecord.commonName || 'Unknown' }}</dd>
            </div>
            <div>
              <dt>Confidence</dt>
              <dd>{{ (previewRecord.confidence * 100).toFixed(1) }}%</dd>
            </div>
            <div>
              <dt>Count</dt>
              <dd>{{ previewRecord.count }}</dd>
            </div>
          </dl>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { logout } from '../api/auth'
import {
  addTags,
  addTagsBatch,
  deleteDetectionFile,
  isUsingMockQuery,
  queryDetections,
} from '../api/query'
import ResultCard from '../components/ResultCard.vue'

const userEmail = localStorage.getItem('user_name') || localStorage.getItem('user_email') || 'User'
const router = useRouter()

const queryModes = [
  { value: 'all', label: 'All' },
  { value: 'tag', label: 'Tag' },
  { value: 'species', label: 'Species' },
  { value: 'count', label: 'Count' },
  { value: 'thumbnail', label: 'Thumbnail' },
  { value: 'file', label: 'File' },
]

const placeholders = {
  all: { label: 'Keyword', placeholder: 'Leave empty to show all records' },
  tag: { label: 'Tag', placeholder: 'invasive, night, bird' },
  species: { label: 'Species', placeholder: 'Felis catus or domestic cat' },
  thumbnail: { label: 'Thumbnail key or file id', placeholder: 'thumb key, URL, or file id' },
  file: { label: 'File name, key, or id', placeholder: 'Sus_scrofa_1.JPG or uploads/...' },
}

const queryType = ref('all')
const queryValue = ref('')
const minCount = ref('')
const maxCount = ref('')
const loading = ref(false)
const errorMsg = ref('')
const message = ref('')
const results = ref([])
const selectedIds = ref([])
const batchTagText = ref('')
const previewRecord = ref(null)

const activePlaceholder = computed(() => placeholders[queryType.value] || placeholders.all)
const mockLabel = computed(() =>
  isUsingMockQuery()
    ? 'Using mock query data until the GCP Cloud Function endpoint is ready.'
    : 'Connected to the configured query API.',
)

onMounted(() => {
  runQuery()
})

function setQueryType(type) {
  queryType.value = type
  queryValue.value = ''
  minCount.value = ''
  maxCount.value = ''
  clearSelection()
}

function parseTags(text) {
  return text.split(',').map(tag => tag.trim()).filter(Boolean)
}

function normaliseTag(tag) {
  return String(tag || '').trim().toLowerCase()
}

function uniqueTags(tags) {
  const seen = new Set()
  return tags.filter(tag => {
    const key = normaliseTag(tag)
    if (!key || seen.has(key)) return false
    seen.add(key)
    return true
  })
}

function findExistingTags(record, tags) {
  const existing = new Set((record.tags || []).map(normaliseTag))
  return uniqueTags(tags).filter(tag => existing.has(normaliseTag(tag)))
}

function applyTagsLocally(fileIds, tags) {
  results.value = results.value.map(record => {
    if (!fileIds.includes(record.fileId)) return record
    return {
      ...record,
      tags: Array.from(new Set([...record.tags, ...tags])),
    }
  })
}

async function runQuery() {
  loading.value = true
  errorMsg.value = ''
  message.value = ''

  try {
    results.value = await queryDetections({
      type: queryType.value,
      value: queryValue.value,
      minCount: minCount.value,
      maxCount: maxCount.value,
    })
    selectedIds.value = selectedIds.value.filter(id =>
      results.value.some(record => record.fileId === id),
    )
  } catch (e) {
    errorMsg.value = e.message || 'Query failed. Please try again.'
  } finally {
    loading.value = false
  }
}

function toggleSelect(fileId) {
  if (selectedIds.value.includes(fileId)) {
    selectedIds.value = selectedIds.value.filter(id => id !== fileId)
    return
  }
  selectedIds.value = [...selectedIds.value, fileId]
}

function clearSelection() {
  selectedIds.value = []
  batchTagText.value = ''
}

async function handleAddTags(record, tags) {
  errorMsg.value = ''
  message.value = ''
  const cleanTags = uniqueTags(tags)
  const existingTags = findExistingTags(record, cleanTags)

  if (!cleanTags.length) return

  if (existingTags.length) {
    errorMsg.value = `Tag already exists on this file: ${existingTags.join(', ')}.`
    return
  }

  try {
    await addTags(record.fileId, cleanTags)
    applyTagsLocally([record.fileId], cleanTags)
    message.value = `Added ${cleanTags.length} tag${cleanTags.length === 1 ? '' : 's'} to ${record.fileName}.`
  } catch (e) {
    errorMsg.value = e.message || 'Failed to add tags.'
  }
}

async function handleBatchTags() {
  const tags = parseTags(batchTagText.value)
  if (!selectedIds.value.length || !tags.length) return

  errorMsg.value = ''
  message.value = ''

  try {
    await addTagsBatch(selectedIds.value, tags)
    applyTagsLocally(selectedIds.value, tags)
    message.value = `Added ${tags.length} tag${tags.length === 1 ? '' : 's'} to ${selectedIds.value.length} files.`
    batchTagText.value = ''
  } catch (e) {
    errorMsg.value = e.message || 'Failed to add batch tags.'
  }
}

async function confirmDelete(record) {
  const confirmed = window.confirm(`Delete ${record.fileName}? This will remove the Firestore record and storage objects when the real API is connected.`)
  if (!confirmed) return

  errorMsg.value = ''
  message.value = ''

  try {
    await deleteDetectionFile(record.fileId)
    results.value = results.value.filter(item => item.fileId !== record.fileId)
    selectedIds.value = selectedIds.value.filter(id => id !== record.fileId)
    message.value = `${record.fileName} deleted.`
  } catch (e) {
    errorMsg.value = e.message || 'Failed to delete file.'
  }
}

function openPreview(record) {
  previewRecord.value = record
}

function closePreview() {
  previewRecord.value = null
}

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

.nav-brand {
  font-weight: 700;
  font-size: 18px;
  color: #1a1a2e;
}

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

.nav-user {
  font-size: 14px;
  color: #555;
}

.btn-logout {
  padding: 7px 16px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}

.btn-logout:hover {
  background: #c0392b;
}

main {
  max-width: 1040px;
  margin: 0 auto;
  padding: 40px 24px;
}

.toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

h1 {
  margin: 0;
  color: #172033;
  font-size: 26px;
}

.toolbar p {
  margin: 6px 0 0;
  color: #6b7785;
  font-size: 14px;
}

.query-panel,
.batch-bar,
.state-panel {
  background: white;
  border: 1px solid #e4e9f0;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(20, 32, 48, 0.06);
}

.query-panel {
  padding: 18px;
}

.mode-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.mode-tab {
  border: 1px solid #d9e2ec;
  border-radius: 6px;
  background: white;
  color: #4b5b6b;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  padding: 8px 12px;
}

.mode-tab.active {
  border-color: #4a90e2;
  background: #4a90e2;
  color: white;
}

.query-form {
  display: grid;
  grid-template-columns: minmax(140px, 1fr) minmax(140px, 1fr) auto;
  gap: 12px;
  align-items: end;
}

.query-form label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: #435466;
  font-size: 13px;
  font-weight: 700;
}

.query-form .wide-field {
  grid-column: span 2;
}

input {
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid #d9e2ec;
  border-radius: 6px;
  font: inherit;
}

.btn-primary,
.btn-refresh,
.btn-secondary,
.btn-ghost {
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  padding: 10px 14px;
}

.btn-primary {
  background: #2ecc71;
  color: white;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-refresh,
.btn-secondary {
  background: #e8f2ff;
  color: #2f6fb3;
}

.btn-ghost {
  background: #eef2f6;
  color: #435466;
}

.batch-bar {
  display: grid;
  grid-template-columns: auto minmax(180px, 1fr) auto auto;
  gap: 10px;
  align-items: center;
  margin-top: 16px;
  padding: 12px 14px;
}

.message,
.error {
  margin: 14px 0 0;
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 13px;
}

.message {
  background: #eaf4ec;
  color: #2f7d46;
}

.error {
  background: #fdebea;
  color: #c0392b;
}

.results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 24px 0 12px;
}

.results-header h2 {
  margin: 0;
  color: #172033;
  font-size: 18px;
}

.results-header span {
  color: #6b7785;
  font-size: 13px;
}

.result-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.state-panel {
  padding: 32px;
  color: #6b7785;
  text-align: center;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(17, 24, 39, 0.58);
}

.modal {
  width: min(860px, 100%);
  max-height: 90vh;
  overflow: auto;
  position: relative;
  display: grid;
  grid-template-columns: minmax(260px, 1.1fr) minmax(240px, 0.9fr);
  gap: 20px;
  padding: 20px;
  background: white;
  border-radius: 8px;
}

.modal-close {
  position: absolute;
  top: 12px;
  right: 12px;
  border: none;
  border-radius: 6px;
  padding: 7px 10px;
  background: rgba(23, 32, 51, 0.82);
  color: white;
  cursor: pointer;
  font-size: 12px;
}

.preview-media {
  min-height: 320px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 6px;
  background: #f3f6fa;
  color: #6b7785;
}

.preview-media img {
  width: 100%;
  height: 100%;
  max-height: 62vh;
  object-fit: contain;
  display: block;
}

.preview-info {
  padding-top: 28px;
}

.preview-info h2 {
  margin: 0;
  color: #172033;
  font-size: 20px;
  word-break: break-word;
}

.preview-info p {
  margin: 8px 0 18px;
  color: #6b7785;
  font-size: 13px;
  word-break: break-word;
}

dl {
  display: grid;
  gap: 12px;
  margin: 0;
}

dl div {
  display: grid;
  gap: 4px;
}

dt {
  color: #6b7785;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}

dd {
  margin: 0;
  color: #172033;
}

@media (max-width: 760px) {
  nav {
    padding: 12px 16px;
  }

  main {
    padding: 28px 16px;
  }

  .toolbar,
  .results-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .query-form,
  .batch-bar {
    grid-template-columns: 1fr;
  }

  .query-form .wide-field {
    grid-column: span 1;
  }

  .modal {
    grid-template-columns: 1fr;
  }

  .preview-info {
    padding-top: 0;
  }
}
</style>
