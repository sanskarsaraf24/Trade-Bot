import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  token: string | null
  userId: string | null
  email: string | null
  setAuth: (token: string, userId: string, email: string) => void
  logout: () => void
}

interface BotState {
  status: 'never_started' | 'running' | 'paused' | 'stopped'
  openPositions: number
  dailyPnl: number
  lastUpdate: string | null
  uptime: number | null
  setStatus: (data: Partial<BotState>) => void
}

interface LogEntry {
  event_type: string
  message: string
  severity: string
  timestamp: string
}

interface LogState {
  logs: LogEntry[]
  addLog: (log: LogEntry) => void
  setLogs: (logs: LogEntry[]) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      userId: null,
      email: null,
      setAuth: (token, userId, email) => set({ token, userId, email }),
      logout: () => {
        localStorage.removeItem('trading_token')
        set({ token: null, userId: null, email: null })
      },
    }),
    { name: 'trading-auth' }
  )
)

export const useBotStore = create<BotState>((set) => ({
  status: 'never_started',
  openPositions: 0,
  dailyPnl: 0,
  lastUpdate: null,
  uptime: null,
  setStatus: (data) => set((s) => ({ ...s, ...data })),
}))

export const useLogStore = create<LogState>((set) => ({
  logs: [],
  addLog: (log) => set((s) => ({ logs: [log, ...s.logs].slice(0, 100) })),
  setLogs: (logs) => set({ logs }),
}))
