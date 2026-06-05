<template>
  <div class="home">
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
      <div class="upload-card">
        <h2>Wildlife Species Detection</h2>
        <p class="subtitle">Upload a camera-trap image or video to identify Australian wildlife</p>

        <!-- File type tabs -->
        <div class="type-tabs">
          <button
            class="tab"
            :class="{ active: activeTab === 'image' }"
            @click="switchTab('image')"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
            Image
          </button>
          <button
            class="tab"
            :class="{ active: activeTab === 'video' }"
            @click="switchTab('video')"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2"/></svg>
            Video
          </button>
        </div>

        <!-- Drop zone -->
        <div
          class="drop-zone"
          :class="{ 'drag-over': isDragging, 'has-file': previewUrl }"
          @dragover.prevent="isDragging = true"
          @dragleave.prevent="isDragging = false"
          @drop.prevent="onDrop"
          @click="triggerFileInput"
        >
          <input
            ref="fileInput"
            type="file"
            :accept="acceptTypes"
            style="display:none"
            @change="onFileChange"
          />

          <!-- Empty state -->
          <template v-if="!previewUrl">
            <div class="drop-icon" :class="activeTab">
              <!-- Image icon -->
              <svg v-if="activeTab === 'image'" xmlns="http://www.w3.org/2000/svg" width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              <!-- Video icon -->
              <svg v-else xmlns="http://www.w3.org/2000/svg" width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">
                <polygon points="23 7 16 12 23 17 23 7"/>
                <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
              </svg>
            </div>
            <p class="drop-text">Drag &amp; drop {{ activeTab === 'image' ? 'an image' : 'a video' }} here</p>
            <p class="drop-hint">or click to browse &nbsp;·&nbsp; {{ activeTab === 'image' ? 'JPG / PNG' : 'MP4 / MOV / AVI' }}</p>
          </template>

          <!-- Image preview -->
          <template v-else-if="activeTab === 'image'">
            <img :src="previewUrl" class="preview-img" alt="preview" />
            <button class="btn-remove" @click.stop="removeFile">Remove</button>
          </template>

          <!-- Video preview -->
          <template v-else>
            <video
              :src="previewUrl"
              class="preview-video"
              controls
              preload="metadata"
              @click.stop
            />
            <button class="btn-remove" @click.stop="removeFile">Remove</button>
          </template>
        </div>

        <!-- File info -->
        <p v-if="selectedFile" class="file-info">
          <span class="file-tag" :class="activeTab">{{ activeTab === 'image' ? 'IMAGE' : 'VIDEO' }}</span>
          {{ selectedFile.name }}
          &nbsp;·&nbsp;
          {{ fileSizeLabel }}
        </p>

        <!-- Large file warning -->
        <p v-if="sizeWarning" class="warning">{{ sizeWarning }}</p>

        <!-- Upload progress bar -->
        <div v-if="uploadStep === 'uploading'" class="progress-wrap">
          <div class="progress-bar" :style="{ width: uploadProgress + '%' }"></div>
          <span class="progress-label">Uploading {{ uploadProgress }}%</span>
        </div>

        <!-- Detection progress: stage pipeline -->
        <div v-if="uploadStep === 'analysing'" class="analysis-panel">
          <p class="analysis-title">
            <span class="spinner spinner-green"></span>
            Analysing — {{ stageLabel }}
          </p>
          <div class="stage-pipeline">
            <template v-for="(stage, si) in STAGES" :key="stage.key">
              <div class="stage-node" :class="stageNodeClass(si)">
                <div class="node-circle">
                  <svg v-if="si < currentStageIndex" width="10" height="10" viewBox="0 0 10 10" fill="none">
                    <polyline points="1.5,5.5 4,8 8.5,2" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                  <span v-else-if="si === currentStageIndex" class="node-spinner"></span>
                </div>
                <span class="node-label">{{ stage.label }}</span>
              </div>
              <div v-if="si < STAGES.length - 1" class="stage-connector" :class="{ filled: si < currentStageIndex }"></div>
            </template>
          </div>
          <div class="analysis-bar-wrap">
            <div class="analysis-bar" :style="{ width: detectionProgress + '%' }"></div>
          </div>
          <span class="analysis-pct">{{ detectionProgress }}%</span>
        </div>

        <!-- Detection complete banner -->
        <div v-if="uploadStep === 'done'" class="done-banner">
          <div class="done-check">
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
              <circle cx="11" cy="11" r="10" fill="#2ecc71"/>
              <polyline points="5.5,11 9,14.5 16.5,7.5" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="done-text">
            <strong>Detection complete</strong>
            <span>Your file has been analysed successfully</span>
          </div>
          <router-link to="/query" class="btn-view-results">View Results →</router-link>
        </div>

        <!-- Upload button -->
        <button
          v-if="uploadStep !== 'done'"
          class="btn-upload"
          :disabled="!selectedFile || uploading"
          @click="handleUpload"
        >
          <span v-if="uploading" class="spinner"></span>
          {{ stepLabel }}
        </button>
        <button
          v-else
          class="btn-upload btn-reset"
          @click="resetForNewUpload"
        >
          Detect Another
        </button>

        <!-- Duplicate notice -->
        <p v-if="isDuplicate" class="notice">
          This file has already been uploaded before — showing existing results.
        </p>

        <!-- Error -->
        <p v-if="errorMsg" class="error">{{ errorMsg }}</p>
      </div>

      <!-- Results: Image -->
      <div v-if="results.length && activeTab === 'image'" class="results-card">
        <h3>Detection Results</h3>
        <div class="result-list">
          <div v-for="(item, i) in results" :key="i" class="result-item">
            <span class="rank">{{ i + 1 }}</span>
            <span class="species">{{ item.species.replace(/_/g, ' ') }}</span>
            <div class="confidence-bar-wrap">
              <div class="confidence-bar" :style="{ width: (item.confidence * 100).toFixed(1) + '%' }"></div>
            </div>
            <span class="confidence-pct">{{ (item.confidence * 100).toFixed(1) }}%</span>
          </div>
        </div>
      </div>

      <!-- Results: Video (timeline) -->
      <div v-if="videoResults.length && activeTab === 'video'" class="results-card">
        <h3>Detection Results &nbsp;<span class="frame-count">{{ videoResults.length }} frames analysed</span></h3>
        <div class="timeline">
          <div v-for="(frame, fi) in videoResults" :key="fi" class="frame-block">
            <div class="frame-header">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#4a90e2" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              <span class="frame-time">{{ frame.timestamp }}</span>
            </div>
            <div class="result-list">
              <div v-for="(item, i) in frame.detections" :key="i" class="result-item">
                <span class="rank">{{ i + 1 }}</span>
                <span class="species">{{ item.species.replace(/_/g, ' ') }}</span>
                <div class="confidence-bar-wrap">
                  <div class="confidence-bar" :style="{ width: (item.confidence * 100).toFixed(1) + '%' }"></div>
                </div>
                <span class="confidence-pct">{{ (item.confidence * 100).toFixed(1) }}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { logout } from '../api/auth'
import { validateImage, validateVideo } from '../utils/validate'
import { hashFile } from '../utils/hash'
import { requestUploadUrl, uploadToS3 } from '../api/upload'
import { pollDetectionStatus } from '../api/detection'

const userEmail = localStorage.getItem('user_name') || localStorage.getItem('user_email') || 'User'
const router = useRouter()

const activeTab = ref('image')
const fileInput = ref(null)
const selectedFile = ref(null)
const previewUrl = ref('')
const isDragging = ref(false)
const uploading = ref(false)
const uploadStep = ref('')      // 'hashing' | 'requesting' | 'uploading' | 'analysing' | 'done'
const uploadProgress = ref(0)
const detectionProgress = ref(0)
const detectionStage = ref('')
const detectedFileKey = ref('')
const isDuplicate = ref(false)
const errorMsg = ref('')
const results = ref([])
const videoResults = ref([])

const STAGES = [
  { key: 'queued',      label: 'Queued' },
  { key: 'downloading', label: 'Downloading' },
  { key: 'detecting',   label: 'Detecting' },
  { key: 'classifying', label: 'Classifying' },
  { key: 'saving',      label: 'Saving' },
  { key: 'completed',   label: 'Complete' },
]

const currentStageIndex = computed(() => {
  const idx = STAGES.findIndex(s => s.key === detectionStage.value)
  return idx >= 0 ? idx : 0
})

function stageNodeClass(i) {
  if (i < currentStageIndex.value) return 'stage-done'
  if (i === currentStageIndex.value) return 'stage-active'
  return 'stage-pending'
}

const ACCEPTED_IMAGE = 'image/jpeg,image/png,image/jpg'
const ACCEPTED_VIDEO = 'video/mp4,video/quicktime,video/x-msvideo,video/webm'

const acceptTypes = computed(() =>
  activeTab.value === 'image' ? ACCEPTED_IMAGE : ACCEPTED_VIDEO
)

const fileSizeLabel = computed(() => {
  if (!selectedFile.value) return ''
  const kb = selectedFile.value.size / 1024
  return kb >= 1024 ? (kb / 1024).toFixed(1) + ' MB' : kb.toFixed(1) + ' KB'
})

const stepLabel = computed(() => {
  const labels = {
    hashing:    'Preparing...',
    requesting: 'Requesting upload...',
    uploading:  `Uploading ${uploadProgress.value}%...`,
    analysing:  'Analysing...',
  }
  return labels[uploadStep.value] ?? 'Detect Species'
})

const STAGE_LABELS = {
  queued:      'Queued — waiting to start…',
  downloading: 'Downloading file…',
  detecting:   'Detecting objects…',
  classifying: 'Classifying species…',
  saving:      'Saving results…',
  completed:   'Complete',
  failed:      'Failed',
}
const stageLabel = computed(() => STAGE_LABELS[detectionStage.value] || 'Analysing…')

const sizeWarning = computed(() => {
  if (!selectedFile.value) return ''
  const mb = selectedFile.value.size / 1024 / 1024
  if (activeTab.value === 'video' && mb > 100) return `Large file (${mb.toFixed(0)} MB) — upload may take a while.`
  return ''
})

function switchTab(tab) {
  if (tab === activeTab.value) return
  activeTab.value = tab
  removeFile()
}

function triggerFileInput() {
  fileInput.value.click()
}

function onFileChange(e) {
  const file = e.target.files[0]
  if (file) setFile(file)
}

function onDrop(e) {
  isDragging.value = false
  const file = e.dataTransfer.files[0]
  if (file) setFile(file)
}

function setFile(file) {
  const validationError = activeTab.value === 'image' ? validateImage(file) : validateVideo(file)
  if (validationError) {
    errorMsg.value = validationError
    return
  }

  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  selectedFile.value = file
  previewUrl.value = URL.createObjectURL(file)
  errorMsg.value = ''
  results.value = []
  videoResults.value = []
}

function removeFile() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  selectedFile.value = null
  previewUrl.value = ''
  results.value = []
  videoResults.value = []
  isDuplicate.value = false
  errorMsg.value = ''
  if (fileInput.value) fileInput.value.value = ''
}

function resetForNewUpload() {
  removeFile()
  uploadStep.value = ''
  detectedFileKey.value = ''
}

async function handleUpload() {
  if (!selectedFile.value) return
  uploading.value = true
  isDuplicate.value = false
  uploadProgress.value = 0
  errorMsg.value = ''
  results.value = []
  videoResults.value = []
  detectedFileKey.value = ''

  try {
    uploadStep.value = 'hashing'
    const fileHash = await hashFile(selectedFile.value)

    uploadStep.value = 'requesting'
    const { uploadUrl, fileKey, exists } = await requestUploadUrl(
      selectedFile.value.name,
      selectedFile.value.type,
      fileHash,
    )
    if (exists) {
      isDuplicate.value = true
    } else {
      uploadStep.value = 'uploading'
      await uploadToS3(uploadUrl, selectedFile.value, (pct) => {
        uploadProgress.value = pct
      })
    }

    uploadStep.value = 'analysing'
    detectionProgress.value = 0
    detectionStage.value = 'queued'

    const finalData = await pollDetectionStatus(fileKey, (status) => {
      detectionProgress.value = status.progress ?? 0
      detectionStage.value = status.stage ?? ''
    })

    detectedFileKey.value = fileKey
    uploadStep.value = 'done'

    // Parse inline results if the API returns species data
    const raw = finalData?.results ?? finalData?.detections ?? []
    if (Array.isArray(raw) && raw.length) {
      if (activeTab.value === 'image') {
        results.value = raw.map(r => ({
          species: r.species || r.label || '',
          confidence: Number(r.confidence ?? r.score ?? 0),
        }))
      } else {
        videoResults.value = raw
      }
    }

  } catch (e) {
    errorMsg.value = e.message || 'Upload failed. Please try again.'
    uploadStep.value = ''
  } finally {
    uploading.value = false
  }
}

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

/* ── Main layout ── */
main {
  max-width: 700px;
  margin: 0 auto;
  padding: 48px 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* ── Upload card ── */
.upload-card {
  background: white;
  border-radius: 16px;
  padding: 40px 36px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  text-align: center;
}
h2 { margin: 0 0 8px; font-size: 22px; color: #1a1a2e; }
.subtitle { color: #666; font-size: 14px; margin: 0 0 24px; }

/* ── Tabs ── */
.type-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  justify-content: center;
}
.tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 20px;
  border: 2px solid #e0e7ef;
  border-radius: 99px;
  background: white;
  color: #888;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.18s;
}
.tab:hover { border-color: #4a90e2; color: #4a90e2; }
.tab.active {
  border-color: #4a90e2;
  background: #4a90e2;
  color: white;
}

/* ── Drop zone ── */
.drop-zone {
  border: 2px dashed #c8d6e5;
  border-radius: 12px;
  padding: 48px 24px;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
  position: relative;
  min-height: 200px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
}
.drop-zone:hover,
.drop-zone.drag-over { border-color: #4a90e2; background: #f0f7ff; }
.drop-zone.has-file  { border-style: solid; border-color: #4a90e2; padding: 16px; }

.drop-icon { color: #adb5bd; }
.drop-icon.video { color: #9b59b6; }
.drop-text { font-size: 15px; color: #444; margin: 0; }
.drop-hint { font-size: 13px; color: #aaa; margin: 0; }

/* ── Previews ── */
.preview-img {
  max-height: 320px;
  max-width: 100%;
  border-radius: 8px;
  object-fit: contain;
}
.preview-video {
  max-height: 320px;
  max-width: 100%;
  border-radius: 8px;
  background: #000;
}
.btn-remove {
  position: absolute;
  top: 10px;
  right: 10px;
  padding: 4px 10px;
  background: rgba(0,0,0,0.55);
  color: white;
  border: none;
  border-radius: 5px;
  font-size: 12px;
  cursor: pointer;
}
.btn-remove:hover { background: rgba(0,0,0,0.75); }

/* ── File info ── */
.file-info {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 13px;
  color: #888;
  margin: 10px 0 0;
  flex-wrap: wrap;
}
.file-tag {
  padding: 2px 7px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.5px;
}
.file-tag.image { background: #e8f4fd; color: #4a90e2; }
.file-tag.video { background: #f3e8fd; color: #9b59b6; }

.warning {
  color: #e67e22;
  font-size: 13px;
  margin: 6px 0 0;
}

/* ── Upload button ── */
.btn-upload {
  margin-top: 20px;
  width: 100%;
  padding: 13px;
  background: #2ecc71;
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.btn-upload:hover:not(:disabled) { background: #27ae60; }
.btn-upload:disabled { opacity: 0.5; cursor: not-allowed; }

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.4);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Upload progress ── */
.progress-wrap {
  margin-top: 14px;
  position: relative;
  height: 8px;
  background: #e8f0fe;
  border-radius: 4px;
  overflow: hidden;
}
.progress-bar {
  height: 100%;
  background: #4a90e2;
  border-radius: 4px;
  transition: width 0.3s ease;
}
.progress-label {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 600;
  color: #4a90e2;
  margin-top: 12px;
}

.notice {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #fff8e1;
  border: 1px solid #ffe082;
  color: #b8860b;
  font-size: 13px;
  padding: 10px 14px;
  border-radius: 8px;
  margin-top: 12px;
}
.notice::before {
  content: '⚠';
  flex-shrink: 0;
}

.progress-wrap {
  margin-top: 14px;
  height: 8px;
  background: #e8f0fe;
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}
.progress-bar {
  height: 100%;
  background: #4a90e2;
  border-radius: 4px;
  transition: width 0.3s ease;
}
.progress-label {
  font-size: 11px;
  color: #4a90e2;
  font-weight: 600;
  margin-top: 4px;
  display: block;
  text-align: right;
}

/* ── Analysis panel ── */
.analysis-panel {
  margin-top: 16px;
  background: #f8fffe;
  border: 1px solid #d4f5e9;
  border-radius: 12px;
  padding: 18px 20px 14px;
  text-align: left;
}
.analysis-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #1a6b47;
  margin: 0 0 16px;
}
.spinner-green {
  border-color: rgba(46,204,113,0.25);
  border-top-color: #2ecc71;
  width: 14px;
  height: 14px;
  border-width: 2px;
}

/* Stage pipeline */
.stage-pipeline {
  display: flex;
  align-items: center;
  gap: 0;
  margin-bottom: 14px;
  overflow-x: auto;
  padding-bottom: 4px;
}
.stage-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  flex-shrink: 0;
}
.node-circle {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.3s, border-color 0.3s;
}
.stage-done .node-circle  { background: #2ecc71; border: 2px solid #2ecc71; }
.stage-active .node-circle { background: white; border: 2px solid #2ecc71; }
.stage-pending .node-circle { background: white; border: 2px solid #dde4ec; }

.node-spinner {
  width: 10px;
  height: 10px;
  border: 2px solid rgba(46,204,113,0.25);
  border-top-color: #2ecc71;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: block;
}
.node-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.3px;
  white-space: nowrap;
}
.stage-done .node-label  { color: #2ecc71; }
.stage-active .node-label { color: #1a6b47; }
.stage-pending .node-label { color: #b0bec5; }

.stage-connector {
  flex: 1;
  height: 2px;
  background: #dde4ec;
  min-width: 12px;
  max-width: 40px;
  margin-bottom: 15px;
  transition: background 0.3s;
}
.stage-connector.filled { background: #2ecc71; }

/* Progress bar inside analysis panel */
.analysis-bar-wrap {
  height: 6px;
  background: #d4f5e9;
  border-radius: 3px;
  overflow: hidden;
}
.analysis-bar {
  height: 100%;
  background: linear-gradient(90deg, #2ecc71, #27ae60);
  border-radius: 3px;
  transition: width 0.4s ease;
}
.analysis-pct {
  display: block;
  text-align: right;
  font-size: 11px;
  font-weight: 700;
  color: #2ecc71;
  margin-top: 4px;
}

/* ── Done banner ── */
.done-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  background: #f0fdf7;
  border: 1px solid #a8edca;
  border-radius: 12px;
  padding: 14px 16px;
}
.done-check { flex-shrink: 0; }
.done-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.done-text strong { font-size: 14px; color: #166534; }
.done-text span   { font-size: 12px; color: #4ade80; }
.btn-view-results {
  flex-shrink: 0;
  padding: 8px 16px;
  background: #2ecc71;
  color: white;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
  transition: background 0.2s;
}
.btn-view-results:hover { background: #27ae60; }

/* Reset button variant */
.btn-reset {
  background: #e8f2ff;
  color: #2f6fb3;
}
.btn-reset:hover:not(:disabled) { background: #cce0ff; }

.error { color: #e74c3c; font-size: 13px; margin-top: 10px; }

/* ── Results card ── */
.results-card {
  background: white;
  border-radius: 16px;
  padding: 28px 36px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
}
.results-card h3 {
  margin: 0 0 20px;
  font-size: 17px;
  color: #1a1a2e;
  display: flex;
  align-items: center;
  gap: 10px;
}
.frame-count {
  font-size: 12px;
  font-weight: 400;
  color: #888;
  background: #f0f4f8;
  padding: 2px 8px;
  border-radius: 99px;
}

/* ── Result rows ── */
.result-list { display: flex; flex-direction: column; gap: 10px; }
.result-item {
  display: grid;
  grid-template-columns: 24px 1fr auto auto;
  align-items: center;
  gap: 10px;
}
.rank { font-size: 13px; color: #aaa; font-weight: 600; text-align: center; }
.species { font-size: 14px; color: #222; font-style: italic; }
.confidence-bar-wrap {
  width: 120px;
  height: 8px;
  background: #eee;
  border-radius: 4px;
  overflow: hidden;
}
.confidence-bar {
  height: 100%;
  background: #2ecc71;
  border-radius: 4px;
  transition: width 0.5s ease;
}
.confidence-pct { font-size: 13px; color: #555; font-weight: 600; min-width: 44px; text-align: right; }

/* ── Video timeline ── */
.timeline { display: flex; flex-direction: column; gap: 20px; }
.frame-block {
  border-left: 3px solid #4a90e2;
  padding-left: 16px;
}
.frame-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}
.frame-time { font-size: 13px; font-weight: 600; color: #4a90e2; }

/* ── Responsive ── */
@media (max-width: 600px) {
  nav { padding: 12px 16px; }
  .upload-card, .results-card { padding: 28px 20px; }
  .confidence-bar-wrap { width: 70px; }
  h2 { font-size: 18px; }
}
</style>
