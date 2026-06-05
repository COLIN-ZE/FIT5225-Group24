import { fetchWithAuth } from './http'

const QUERY_BASE_URL = import.meta.env.VITE_QUERY_API_URL || import.meta.env.VITE_API_URL
const USE_MOCK = import.meta.env.VITE_USE_MOCK_QUERY !== 'false' || !QUERY_BASE_URL
const QUERY_PATH = '/query'
const FILES_PATH = '/files'

function placeholderImage(label, bg = '#e8f2ff', fg = '#2f6fb3') {
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="640" height="420" viewBox="0 0 640 420">
      <rect width="640" height="420" fill="${bg}"/>
      <circle cx="320" cy="170" r="72" fill="#ffffff" opacity="0.72"/>
      <text x="320" y="292" text-anchor="middle" font-family="Arial, sans-serif" font-size="34" font-weight="700" fill="${fg}">${label}</text>
    </svg>
  `
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
}

const mockRecords = [
  {
    fileId: 'img-cassowary-001',
    fileName: 'Casuarius_casuarius_1.JPG',
    fileKey: 'uploads/Casuarius_casuarius_1.JPG',
    thumbnailUrl: placeholderImage('Cassowary', '#e9f6f1', '#1d7f62'),
    imageUrl: placeholderImage('Cassowary', '#e9f6f1', '#1d7f62'),
    species: 'Casuarius casuarius',
    commonName: 'southern cassowary',
    confidence: 0.94,
    count: 1,
    tags: ['cassowary', 'bird', 'rainforest'],
    uploadedAt: '2026-06-03T07:42:00Z',
  },
  {
    fileId: 'img-cat-002',
    fileName: 'Felis_catus_2.JPG',
    fileKey: 'uploads/Felis_catus_2.JPG',
    thumbnailUrl: placeholderImage('Cat', '#fdeeed', '#b93d35'),
    imageUrl: placeholderImage('Cat', '#fdeeed', '#b93d35'),
    species: 'Felis catus',
    commonName: 'domestic cat',
    confidence: 0.89,
    count: 1,
    tags: ['invasive', 'night'],
    uploadedAt: '2026-06-02T12:18:00Z',
  },
  {
    fileId: 'img-boar-003',
    fileName: 'Sus_scrofa_1.JPG',
    fileKey: 'uploads/Sus_scrofa_1.JPG',
    thumbnailUrl: placeholderImage('Boar', '#f4f0e6', '#806330'),
    imageUrl: placeholderImage('Boar', '#f4f0e6', '#806330'),
    species: 'Sus scrofa',
    commonName: 'wild boar',
    confidence: 0.86,
    count: 3,
    tags: ['invasive', 'group'],
    uploadedAt: '2026-06-01T22:06:00Z',
  },
  {
    fileId: 'img-wallaby-004',
    fileName: 'Thylogale_stigmatica_1.JPG',
    fileKey: 'uploads/Thylogale_stigmatica_1.JPG',
    thumbnailUrl: placeholderImage('Pademelon', '#edf1ff', '#4d61ad'),
    imageUrl: placeholderImage('Pademelon', '#edf1ff', '#4d61ad'),
    species: 'Thylogale stigmatica',
    commonName: 'red-legged pademelon',
    confidence: 0.91,
    count: 2,
    tags: ['mammal', 'day'],
    uploadedAt: '2026-05-31T03:33:00Z',
  },
]

function delay(ms = 350) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function normaliseRecord(record) {
  return {
    fileId: record.fileId || record.file_id || record.id,
    fileName: record.fileName || record.file_name || record.filename || 'Untitled file',
    fileKey: record.fileKey || record.file_key || '',
    thumbnailUrl: record.thumbnailUrl || record.thumbnail_url || record.thumb_url || '',
    imageUrl: record.imageUrl || record.image_url || record.file_url || '',
    species: record.species || '',
    commonName: record.commonName || record.common_name || '',
    confidence: Number(record.confidence ?? 0),
    count: Number(record.count ?? record.quantity ?? 0),
    tags: Array.isArray(record.tags) ? record.tags : [],
    uploadedAt: record.uploadedAt || record.uploaded_at || record.createdAt || '',
  }
}

function filterMock({ type, value, minCount, maxCount }) {
  const term = String(value || '').trim().toLowerCase()

  if (type === 'all' || !term && type !== 'count') {
    return mockRecords
  }

  if (type === 'tag') {
    return mockRecords.filter(record =>
      record.tags.some(tag => tag.toLowerCase().includes(term)),
    )
  }

  if (type === 'species') {
    return mockRecords.filter(record =>
      `${record.species} ${record.commonName}`.toLowerCase().includes(term),
    )
  }

  if (type === 'count') {
    const min = Number(minCount || 0)
    const max = maxCount === '' || maxCount == null ? Infinity : Number(maxCount)
    return mockRecords.filter(record => record.count >= min && record.count <= max)
  }

  if (type === 'thumbnail') {
    return mockRecords.filter(record =>
      `${record.thumbnailUrl} ${record.fileId}`.toLowerCase().includes(term),
    )
  }

  if (type === 'file') {
    return mockRecords.filter(record =>
      `${record.fileName} ${record.fileKey} ${record.fileId}`.toLowerCase().includes(term),
    )
  }

  return mockRecords
}

function mergeTagsIntoMockRecords(fileIds, tags) {
  mockRecords.forEach(record => {
    if (!fileIds.includes(record.fileId)) return
    record.tags = Array.from(new Set([...record.tags, ...tags]))
  })
}

async function request(path, options = {}) {
  const res = await fetchWithAuth(`${QUERY_BASE_URL}${path}`, options)
  if (!res.ok) throw new Error(`Query request failed (${res.status})`)
  const payload = await res.json()
  return payload.data ?? payload.results ?? payload
}

export async function queryDetections(params) {
  if (USE_MOCK) {
    await delay()
    return filterMock(params).map(normaliseRecord)
  }

  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== '' && value != null) search.set(key, value)
  })
  const data = await request(`${QUERY_PATH}?${search.toString()}`)
  return Array.isArray(data) ? data.map(normaliseRecord) : []
}

export async function addTags(fileId, tags) {
  const cleanTags = tags.map(tag => tag.trim()).filter(Boolean)
  if (USE_MOCK) {
    await delay(200)
    mergeTagsIntoMockRecords([fileId], cleanTags)
    return { fileId, tags: cleanTags }
  }

  return request(`${FILES_PATH}/${encodeURIComponent(fileId)}/tags`, {
    method: 'POST',
    body: JSON.stringify({ tags: cleanTags }),
  })
}

export async function addTagsBatch(fileIds, tags) {
  const cleanTags = tags.map(tag => tag.trim()).filter(Boolean)
  if (USE_MOCK) {
    await delay(250)
    mergeTagsIntoMockRecords(fileIds, cleanTags)
    return { fileIds, tags: cleanTags }
  }

  return request(`${FILES_PATH}/tags:batchAdd`, {
    method: 'POST',
    body: JSON.stringify({ fileIds, tags: cleanTags }),
  })
}

export async function deleteDetectionFile(fileId) {
  if (USE_MOCK) {
    await delay(250)
    const index = mockRecords.findIndex(record => record.fileId === fileId)
    if (index >= 0) mockRecords.splice(index, 1)
    return { fileId, deleted: true }
  }

  return request(`${FILES_PATH}/${encodeURIComponent(fileId)}`, {
    method: 'DELETE',
  })
}

export function isUsingMockQuery() {
  return USE_MOCK
}
