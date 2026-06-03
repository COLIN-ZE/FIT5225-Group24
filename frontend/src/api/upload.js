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
