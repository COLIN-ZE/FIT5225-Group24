import { authHeaders, BASE_URL } from './http'
import { getUserId } from './auth'

const SUB_PATH = '/subscriptions'
async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
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
