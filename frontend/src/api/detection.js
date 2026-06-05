import { BASE_URL, fetchWithAuth } from './http'

async function request(path) {
  const res = await fetchWithAuth(`${BASE_URL}${path}`)
  if (!res.ok) throw new Error(`Detection status request failed (${res.status})`)
  const payload = await res.json()
  return payload.data ?? payload
}

export async function getDetectionStatus(fileKey) {
  return request(`/detection-status?fileKey=${encodeURIComponent(fileKey)}`)
}

export function pollDetectionStatus(fileKey, onProgress) {
  return new Promise((resolve, reject) => {
    const INTERVAL = 8000   
    const MAX_ATTEMPTS = 15 
    let attempts = 0

    const timer = setInterval(async () => {
      attempts++

      if (attempts > MAX_ATTEMPTS) {
        clearInterval(timer)
        reject(new Error('Detection timeout: exceeded maximum attempts'))
        return
      }

      try {
        const data = await getDetectionStatus(fileKey)
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
    }, INTERVAL)
  })
}