const ALLOWED_IMAGE = {
  mimes: ['image/jpeg', 'image/png'],
  exts: ['.jpg', '.jpeg', '.png'],
}

const ALLOWED_VIDEO = {
  mimes: ['video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/webm'],
  exts: ['.mp4', '.mov', '.avi', '.webm'],
}

function check(file, allowed) {
  const ext = '.' + file.name.split('.').pop().toLowerCase()
  if (!allowed.mimes.includes(file.type)) {
    return `Unsupported format "${file.type}". Allowed: ${allowed.exts.join(', ')}`
  }
  if (!allowed.exts.includes(ext)) {
    return `Unsupported extension "${ext}". Allowed: ${allowed.exts.join(', ')}`
  }
  return null
}

export function validateImage(file) {
  return check(file, ALLOWED_IMAGE)
}

export function validateVideo(file) {
  return check(file, ALLOWED_VIDEO)
}
