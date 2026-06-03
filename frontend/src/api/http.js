import { getToken } from './auth'

export const BASE_URL = import.meta.env.VITE_API_URL

export function authHeaders() {
  return {
    'Authorization': `Bearer ${getToken()}`,
    'Content-Type': 'application/json',
  }
}
