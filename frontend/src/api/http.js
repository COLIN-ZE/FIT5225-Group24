import { getToken } from './auth'

export const BASE_URL = import.meta.env.VITE_API_URL

export function authHeaders() {
  const token = getToken()
  return {
    'Authorization': token ? `Bearer ${token}` : '',
  }
}
