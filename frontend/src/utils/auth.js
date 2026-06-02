const API_BASE = import.meta.env.VITE_API_URL || ''

export async function register(email, password, firstName, lastName) {
  // TODO: replace with real API call
  // const res = await fetch(`${API_BASE}/auth/register`, {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify({ email, password, firstName, lastName })
  // })
  // if (!res.ok) throw new Error((await res.json()).error)

  // Mock
  const users = JSON.parse(localStorage.getItem('mock_users') || '{}')
  if (users[email]) throw new Error('User already exists')
  users[email] = { password, firstName, lastName }
  localStorage.setItem('mock_users', JSON.stringify(users))
}

export async function login(email, password) {
  // TODO: replace with real API call
  // const res = await fetch(`${API_BASE}/auth/login`, {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify({ email, password })
  // })
  // if (!res.ok) throw new Error((await res.json()).error)
  // const { id_token } = await res.json()
  // localStorage.setItem('id_token', id_token)

  // Mock
  const users = JSON.parse(localStorage.getItem('mock_users') || '{}')
  const user = users[email]
  if (!user || user.password !== password) throw new Error('Invalid email or password')
  localStorage.setItem('id_token', 'mock-token-' + email)
  localStorage.setItem('user_email', email)
  localStorage.setItem('user_name', `${user.firstName} ${user.lastName}`)
}

export function logout() {
  localStorage.removeItem('id_token')
  localStorage.removeItem('user_email')
}

export function getToken() {
  return localStorage.getItem('id_token')
}

export function isLoggedIn() {
  return !!getToken()
}
