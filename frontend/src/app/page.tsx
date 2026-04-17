'use client'
import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore, useBotStore, useLogStore } from '@/store/trading'
import { botApi, tradesApi, metricsApi } from '@/lib/api'
import { useTradingWS } from '@/lib/websocket'
import Sidebar from '@/components/shared/Sidebar'
import MetricsBar from '@/components/dashboard/MetricsBar'
import BotControls from '@/components/dashboard/BotControls'
import OpenTradesTable from '@/components/dashboard/OpenTradesTable'
import RecentTradesTable from '@/components/dashboard/RecentTradesTable'
import SystemLog from '@/components/dashboard/SystemLog'

export default function DashboardPage() {
  const router = useRouter()
  const { token, userId } = useAuthStore()
  const { setStatus } = useBotStore()
  const { setLogs, addLog } = useLogStore()

  const [openTrades, setOpenTrades] = useState<unknown[]>([])
  const [closedTrades, setClosedTrades] = useState<unknown[]>([])
  const [dailyMetrics, setDailyMetrics] = useState<Record<string, unknown>>({})
  const [wsConnected, setWsConnected] = useState(false)

  const [loading, setLoading] = useState(true)

  // Redirect if not logged in (after hydration)
  useEffect(() => {
    // Check if token exists in localStorage directly if zustand hasn't caught up
    const storedToken = typeof window !== 'undefined' ? localStorage.getItem('trading_token') : null
    
    if (!token && !storedToken) {
      router.push('/login')
    } else {
      setLoading(false)
    }
  }, [token, router])

  // Load initial data
  const refreshAll = useCallback(async () => {
    try {
      const [statusRes, openRes, closedRes, metricsRes, logsRes] = await Promise.all([
        botApi.status(),
        tradesApi.open(),
        tradesApi.closed(20),
        metricsApi.daily(),
        metricsApi.logs(50),
      ])
      setStatus({
        status: statusRes.data.status,
        openPositions: statusRes.data.open_positions,
        uptime: statusRes.data.uptime_seconds,
        lastUpdate: statusRes.data.last_update,
      })
      setOpenTrades(openRes.data)
      setClosedTrades(closedRes.data)
      setDailyMetrics(metricsRes.data)
      setLogs(logsRes.data)
    } catch { /* ignore */ }
  }, [setStatus, setLogs])

  useEffect(() => {
    if (token) refreshAll()
    const interval = setInterval(refreshAll, 30_000)
    return () => clearInterval(interval)
  }, [token, refreshAll])

  // WebSocket live updates
  useTradingWS(userId, {
    onConnect: () => setWsConnected(true),
    onDisconnect: () => setWsConnected(false),
    onTradeUpdate: () => {
      tradesApi.open().then((r) => setOpenTrades(r.data))
      tradesApi.closed(20).then((r) => setClosedTrades(r.data))
    },
    onMetricsUpdate: (data) => {
      setStatus({
        openPositions: data.open_positions as number,
        dailyPnl: data.daily_pnl as number,
        lastUpdate: data.last_update as string,
      })
      metricsApi.daily().then((r) => setDailyMetrics(r.data))
    },
    onLogEvent: (data) => addLog({
      event_type: data.event_type as string,
      message: data.message as string,
      severity: data.severity as string,
      timestamp: new Date().toISOString(),
    }),
  })

  if (loading && !token) {
    return (
      <div className="flex items-center justify-center h-screen bg-surface-900">
        <div className="text-brand-400 font-medium animate-pulse">
          Starting system…
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen overflow-hidden bg-surface-900">
      <Sidebar active="dashboard" />

      <main className="flex-1 overflow-y-auto">
        <div className="p-6 space-y-6 max-w-screen-2xl">
          {/* Top bar */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-white">Live Dashboard</h1>
              <p className="text-xs text-slate-500">
                {wsConnected
                  ? <span className="text-green-400">● Live</span>
                  : <span className="text-yellow-400">○ Connecting…</span>}
                {' '}· Updated every 30s
              </p>
            </div>
            <BotControls onAction={refreshAll} />
          </div>

          {/* Metrics bar */}
          <MetricsBar metrics={dailyMetrics} />

          {/* Tables */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <div className="card">
              <h2 className="text-sm font-semibold text-slate-300 mb-3">
                Open Positions ({openTrades.length})
              </h2>
              <OpenTradesTable trades={openTrades} onExit={refreshAll} />
            </div>

            <div className="card">
              <h2 className="text-sm font-semibold text-slate-300 mb-3">
                Today's Closed Trades
              </h2>
              <RecentTradesTable trades={closedTrades} />
            </div>
          </div>

          {/* System log */}
          <div className="card">
            <h2 className="text-sm font-semibold text-slate-300 mb-3">System Log</h2>
            <SystemLog />
          </div>
        </div>
      </main>
    </div>
  )
}
