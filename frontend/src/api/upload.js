import { BASE_URL, authHeaders } from './http'

export async function requestUploadUrl(filename, contentType, fileHash) {
  const res = await fetch(`${BASE_URL}/requestUploadFile`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ filename, contentType, fileHash }),
  })
  if (!res.ok) throw new Error(`Failed to get upload URL (${res.status})`)
  return res.json()  // { uploadUrl, fileKey } or { exists: true, fileKey }
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

export async function pollResults(fileKey, maxWaitMs = 60000) {
  const interval = 2000
  const maxTries = maxWaitMs / interval

  for (let i = 0; i < maxTries; i++) {
    await new Promise(r => setTimeout(r, interval))
    const res = await fetch(`${BASE_URL}/results/${encodeURIComponent(fileKey)}`, {
      headers: authHeaders(),
    })
    if (!res.ok) throw new Error(`Failed to fetch results (${res.status})`)
    const data = await res.json()
    if (data.status === 'done') return data.results
  }
  throw new Error('Detection timed out. Please try again.')
}
