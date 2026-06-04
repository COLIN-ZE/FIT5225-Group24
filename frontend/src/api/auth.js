import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
  CognitoUserAttribute,
} from 'amazon-cognito-identity-js'

const userPool = new CognitoUserPool({
  UserPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID,
  ClientId: import.meta.env.VITE_COGNITO_CLIENT_ID,
})

export function register(email, password, firstName, lastName) {
  return new Promise((resolve, reject) => {
    const attrs = [
      new CognitoUserAttribute({ Name: 'given_name', Value: firstName }),
      new CognitoUserAttribute({ Name: 'family_name', Value: lastName }),
    ]
    userPool.signUp(email, password, attrs, null, (err, result) => {
      if (err) return reject(new Error(err.message))
      resolve(result)
    })
  })
}

export function confirmRegistration(email, code) {
  return new Promise((resolve, reject) => {
    const user = new CognitoUser({ Username: email, Pool: userPool })
    user.confirmRegistration(code, true, (err) => {
      if (err) return reject(new Error(err.message))
      resolve()
    })
  })
}

export function login(email, password) {
  return new Promise((resolve, reject) => {
    const authDetails = new AuthenticationDetails({ Username: email, Password: password })
    const user = new CognitoUser({ Username: email, Pool: userPool })
    user.authenticateUser(authDetails, {
      onSuccess(session) {
        localStorage.setItem('id_token', session.getIdToken().getJwtToken())
        localStorage.setItem('user_email', email)
        const payload = session.getIdToken().payload
        const name = payload.given_name || payload.name || email
        localStorage.setItem('user_name', name)
        localStorage.setItem('user_id', payload.sub || email)
        resolve(session)
      },
      onFailure(err) {
        reject(new Error(err.message))
      },
    })
  })
}

export function logout() {
  const user = userPool.getCurrentUser()
  if (user) user.signOut()
  localStorage.removeItem('id_token')
  localStorage.removeItem('user_email')
  localStorage.removeItem('user_name')
  localStorage.removeItem('user_id')
}

export function getToken() {
  return localStorage.getItem('id_token')
}

export function getUserId() {
  return localStorage.getItem('user_id') || localStorage.getItem('user_email') || 'demo_user'
}

export function isLoggedIn() {
  return !!getToken()
}
