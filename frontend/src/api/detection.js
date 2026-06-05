import { BASE_URL, authHeaders } from './http'

async function request(path) {
  const res = await fetch(`${BASE_URL}${path}`, { headers: authHeaders() })
  if (!res.ok) throw new Error(`Detection status request failed (${res.status})`)
  const payload = await res.json()
  return payload.data ?? payload
}

export async function getDetectionStatus(fileId) {
  return request(`/detection-status/${encodeURIComponent(fileId)}`)
}

export function pollDetectionStatus(fileId, onProgress) {
  return new Promise((resolve, reject) => {
    const timer = setInterval(async () => {
      try {
        const data = await getDetectionStatus(fileId)
        onProgress?.(data)
        if (data.status === 'processed') {
          clearInterval(timer)
          resolve(data)
        } else if (data.status === 'failed') {
          clearInterval(timer)
          reject(new Error(data.error || 'Detection failed'))
        }
      } catch (e) {
        clearInterval(timer)
        reject(e)
      }
    }, 3000)
  })
}
