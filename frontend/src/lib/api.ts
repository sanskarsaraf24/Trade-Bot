import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost/api'

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('trading_token')
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('trading_token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', new URLSearchParams({ username: email, password }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }),
  register: (email: string, password: string) =>
    api.post('/auth/register', { email, password }),
  me: () => api.get('/auth/me'),
  kiteLogin: () => api.get('/auth/kite/login'),
}

export const configApi = {
  get: () => api.get('/config'),
  save: (data: Record<string, unknown>) => api.post('/config', data),
  update: (data: Record<string, unknown>) => api.post('/config', data),
  reset: () => api.delete('/config'),
}

export const botApi = {
  start: () => api.post('/bot/start'),
  pause: () => api.post('/bot/pause'),
  resume: () => api.post('/bot/resume'),
  stop: () => api.post('/bot/stop'),
  status: () => api.get('/bot/status'),
}

export const tradesApi = {
  open: () => api.get('/trades/open'),
  closed: (limit = 30) => api.get(`/trades/closed?limit=${limit}`),
  exitOne: (tradeId: string) => api.post(`/trades/exit/${tradeId}`),
  exitAll: () => api.post('/trades/exit-all'),
}

export const metricsApi = {
  daily: () => api.get('/metrics/daily'),
  weekly: () => api.get('/metrics/weekly'),
  claudeAccuracy: () => api.get('/metrics/claude-accuracy'),
  logs: (limit = 50) => api.get(`/logs?limit=${limit}`),
}

export default api
