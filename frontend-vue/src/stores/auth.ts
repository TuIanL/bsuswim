import { defineStore } from 'pinia'
import { getCurrentUser, login, register, setAuthToken, demoMode } from '../services/api'
import type { LoginForm, RegisterForm, User } from '../types'

const TOKEN_KEY = 'zyys-vue-access-token'
const USER_KEY = 'zyys-vue-user'

function readStoredUser(): User | null {
  try {
    const raw = window.localStorage.getItem(USER_KEY)
    return raw ? (JSON.parse(raw) as User) : null
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: window.localStorage.getItem(TOKEN_KEY) || '',
    user: readStoredUser(),
    loading: false,
    restored: false,
    demoSignedOut: false
  }),
  getters: {
    isAuthenticated: (state) => (demoMode ? !state.demoSignedOut : Boolean(state.token && state.user)),
    role: (state) => state.user?.role,
    isCoach: (state) => demoMode || state.user?.role === 'coach' || state.user?.role === 'admin'
  },
  actions: {
    persist(remember = true) {
      setAuthToken(this.token)
      if (remember && this.token) {
        window.localStorage.setItem(TOKEN_KEY, this.token)
      } else if (!remember) {
        window.localStorage.removeItem(TOKEN_KEY)
      }
      if (this.user) {
        window.localStorage.setItem(USER_KEY, JSON.stringify(this.user))
      } else {
        window.localStorage.removeItem(USER_KEY)
      }
    },
    async restore() {
      if (this.restored) return
      this.loading = true
      try {
        setAuthToken(this.token)
        if ((demoMode && !this.demoSignedOut) || this.token) {
          this.user = await getCurrentUser()
          if (demoMode && !this.token) {
            this.token = 'demo-access-token'
          }
          this.persist(true)
        }
      } catch {
        this.logout()
      } finally {
        this.restored = true
        this.loading = false
      }
    },
    async login(input: LoginForm) {
      this.loading = true
      try {
        const token = await login(input)
        this.token = token.access_token
        this.demoSignedOut = false
        setAuthToken(this.token)
        this.user = await getCurrentUser()
        this.persist(input.remember !== false)
      } finally {
        this.loading = false
      }
    },
    async register(input: RegisterForm) {
      this.loading = true
      try {
        await register(input)
        await this.login({ username: input.username, password: input.password, remember: true })
      } finally {
        this.loading = false
      }
    },
    logout() {
      this.token = ''
      this.user = null
      this.demoSignedOut = demoMode
      setAuthToken('')
      window.localStorage.removeItem(TOKEN_KEY)
      window.localStorage.removeItem(USER_KEY)
    }
  }
})
