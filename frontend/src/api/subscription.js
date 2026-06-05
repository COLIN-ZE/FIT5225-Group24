import { fetchWithAuth, BASE_URL } from './http'
import { getUserId } from './auth'

const SUB_PATH = '/subscriptions'
const SNS_SYNC_PATH = '/subscriptions/sync'

async function request(path, options = {}) {
  const res = await fetchWithAuth(`${BASE_URL}${path}`, options)
  if (!res.ok) throw new Error(`Subscription request failed (${res.status})`)
  const payload = await res.json()
  return payload.data ?? payload.subscriptions ?? payload
}

export async function getSubscriptions() {
  const userId = encodeURIComponent(getUserId())
  const email = encodeURIComponent(localStorage.getItem('user_email') || '')
  const data = await request(`${SUB_PATH}?userId=${userId}&email=${email}`)
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.tags)) {
    return data.tags.map(tag => ({ tag, createdAt: null }))
  }
  return []
}

export async function subscribe(tag) {
  const clean = tag.trim().toLowerCase()
  if (!clean) throw new Error('Tag cannot be empty')
  return request(SUB_PATH, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      tag: clean,
      userId: getUserId(),
      email: localStorage.getItem('user_email') || null,
    }),
  })
}

export async function unsubscribe(tag) {
  return request(SUB_PATH, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      tag: tag.trim().toLowerCase(),
      userId: getUserId(),
      email: localStorage.getItem('user_email') || null,
    }),
  })
}

// Called after every subscribe/unsubscribe to push the latest tag list to the
// new SNS-update endpoint on AWS API Gateway.
export async function syncSubscriptionsWithGateway() {
  const userId = getUserId()
  const email = localStorage.getItem('user_email') || ''
  const latestSubs = await getSubscriptions()
  const tags = latestSubs.map(s => s.tag)

  const fullUrl = `${BASE_URL}${SNS_SYNC_PATH}`
  console.log('[debug] sync URL:', fullUrl)  // ← 加这行

  const res = await fetchWithAuth(fullUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ userId, email, tags, status: 'active' }),
  })
}