import { getToken, logout, isTokenExpired } from './auth'

export const BASE_URL = import.meta.env.VITE_API_URL

export function authHeaders() {
  const token = getToken()
  return {
    'Authorization': token ? `Bearer ${token}` : '',
  }
}

// Drop-in replacement for fetch() that redirects to /login on expired token or 401
export async function fetchWithAuth(url, options = {}) {
  if (isTokenExpired()) {
    logout()
    window.location.href = '/login'
    return
  }

  const res = await fetch(url, {
    ...options,
    headers: { ...authHeaders(), ...(options.headers || {}) },
  })

  if (res.status === 401) {
    logout()
    window.location.href = '/login'
    return
  }

  return res
}
