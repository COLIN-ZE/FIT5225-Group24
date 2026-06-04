import { authHeaders, BASE_URL } from './http'
import { getUserId } from './auth'

const SUB_PATH = '/subscriptions'
const SUBSCRIPTION_BASE_URL = import.meta.env.VITE_QUERY_API_URL || BASE_URL
const USE_MOCK = import.meta.env.VITE_USE_MOCK_QUERY !== 'false' || !SUBSCRIPTION_BASE_URL

let mockSubscriptions = [
  { tag: 'koala', createdAt: '2026-06-01T08:00:00Z' },
  { tag: 'cassowary', createdAt: '2026-06-02T11:30:00Z' },
]

function delay(ms = 350) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function request(path, options = {}) {
  const res = await fetch(`${SUBSCRIPTION_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...authHeaders(),
      ...(options.headers || {}),
    },
  })
  if (!res.ok) throw new Error(`Subscription request failed (${res.status})`)
  const payload = await res.json()
  return payload.data ?? payload.subscriptions ?? payload
}

export async function getSubscriptions() {
  if (USE_MOCK) {
    await delay()
    return [...mockSubscriptions]
  }
  const userId = encodeURIComponent(getUserId())
  const email = encodeURIComponent(localStorage.getItem('user_email') || '')
  const data = await request(`${SUB_PATH}?userId=${userId}&email=${email}`)
  return Array.isArray(data) ? data : []
}

export async function subscribe(tag) {
  const clean = tag.trim().toLowerCase()
  if (!clean) throw new Error('Tag cannot be empty')
  if (USE_MOCK) {
    await delay(300)
    if (mockSubscriptions.some(s => s.tag === clean)) {
      throw new Error(`Already subscribed to "${clean}"`)
    }
    const entry = { tag: clean, createdAt: new Date().toISOString() }
    mockSubscriptions.push(entry)
    return entry
  }
  return request(SUB_PATH, {
    method: 'POST',
    body: JSON.stringify({
      tag: clean,
      userId: getUserId(),
      email: localStorage.getItem('user_email') || null,
    }),
  })
}

export async function unsubscribe(tag) {
  if (USE_MOCK) {
    await delay(250)
    mockSubscriptions = mockSubscriptions.filter(s => s.tag !== tag)
    return { tag, deleted: true }
  }
  const userId = encodeURIComponent(getUserId())
  const email = encodeURIComponent(localStorage.getItem('user_email') || '')
  return request(`${SUB_PATH}/${encodeURIComponent(tag)}?userId=${userId}&email=${email}`, { method: 'DELETE' })
}

export function isUsingMockSubscription() {
  return USE_MOCK
}
