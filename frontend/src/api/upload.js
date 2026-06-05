import { BASE_URL, fetchWithAuth } from './http'

export async function requestUploadUrl(filename, contentType, fileHash) {
  const res = await fetchWithAuth(`${BASE_URL}/requestUploadFile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename, contentType, fileHash }),
  })
  if (!res.ok) throw new Error(`Failed to get upload URL (${res.status})`)
  const { code, message, data } = await res.json()
  if (code !== 200) throw new Error(message || 'Failed to get upload URL')
  return data  // { uploadUrl, fileKey } or { exists: true, fileKey }
}

// PUT file directly to S3 via presigned URL, with upload progress callback
export function uploadToS3(uploadUrl, file, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100))
      }
    })
    xhr.addEventListener('load', () => {
      xhr.status === 200 ? resolve() : reject(new Error(`S3 upload failed (${xhr.status})`))
    })
    xhr.addEventListener('error', () => reject(new Error('Network error during upload')))
    xhr.open('PUT', uploadUrl)
    xhr.setRequestHeader('Content-Type', file.type)
    xhr.send(file)
  })
}



export async function pollResults(fileKey, onProgress, maxWaitMs = 300000) {

  const msgBuffer = new TextEncoder().encode(fileKey)
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer)
  const fileId = Array.from(new Uint8Array(hashBuffer))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('')

  return pollDetectionStatus(fileId, onProgress)
}