'use client'
import { useEffect, useState, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore, useBotStore, useLogStore } from '@/store/trading'
import { botApi, tradesApi, metricsApi } from '@/lib/api'
import { useTradingWS } from '@/lib/websocket'
import Sidebar from '@/components/shared/Sidebar'
import MetricsBar from '@/components/dashboard/MetricsBar'
import BotControls from '@/components/dashboard/BotControls'
import OpenTradesTable from '@/components/dashboard/OpenTradesTable'
import RecentTradesTable from '@/components/dashboard/RecentTradesTable'
import ActionFeed from '@/components/dashboard/ActionFeed'
import PnLSparkline from '@/components/dashboard/PnLSparkline'

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
  const [lastTradeFlash, setLastTradeFlash] = useState<string | null>(null)

  useEffect(() => {
    const storedToken = typeof window !== 'undefined' ? localStorage.getItem('trading_token') : null
    if (!token && !storedToken) {
      router.push('/login')
    } else {
      setLoading(false)
    }
  }, [token, router])

  const refreshAll = useCallback(async () => {
    try {
      const [statusRes, openRes, closedRes, metricsRes, logsRes] = await Promise.all([
        botApi.status(),
        tradesApi.open(),
        tradesApi.closed(30),
        metricsApi.daily(),
        metricsApi.logs(100),
      ])
      setStatus({
        status: statusRes.data.status,
        openPositions: statusRes.data.open_positions,
        uptime: statusRes.data.uptime_seconds,
        lastUpdate: statusRes.data.last_update,
        brokerType: statusRes.data.broker_type,
      })
      setOpenTrades(openRes.data)
      setClosedTrades(closedRes.data)
      setDailyMetrics(metricsRes.data)
      setLogs(logsRes.data)
    } catch { /* ignore */ }
  }, [setStatus, setLogs])

  useEffect(() => {
    if (token) refreshAll()
    const interval = setInterval(refreshAll, 20_000)
    return () => clearInterval(interval)
  }, [token, refreshAll])

  useTradingWS(userId, {
    onConnect: () => setWsConnected(true),
    onDisconnect: () => setWsConnected(false),
    onTradeUpdate: (data) => {
      tradesApi.open().then((r) => setOpenTrades(r.data))
      tradesApi.closed(30).then((r) => setClosedTrades(r.data))
      metricsApi.daily().then((r) => setDailyMetrics(r.data))
      // Flash notification
      if (data.symbol) {
        setLastTradeFlash(`${data.action === 'opened' ? '🟢' : '🔴'} ${data.symbol} ${data.action}`)
        setTimeout(() => setLastTradeFlash(null), 4000)
      }
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
        <div className="text-brand-400 font-medium animate-pulse">Starting system…</div>
      </div>
    )
  }

  return (
    <div className="flex h-screen overflow-hidden bg-surface-900">
      <Sidebar active="dashboard" />

      <main className="flex-1 overflow-y-auto">
        <div className="p-5 space-y-5 max-w-screen-2xl">

          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">Live Dashboard</h1>
              <p className="text-xs text-slate-500 mt-0.5 flex items-center gap-2">
                <span className={wsConnected ? 'text-green-400' : 'text-yellow-500'}>
                  {wsConnected ? '● Live' : '○ Reconnecting…'}
                </span>
                <span className="text-slate-700">·</span>
                <span>Auto-refresh every 20s</span>
              </p>
            </div>
            <div className="flex items-center gap-3">
              {/* Trade flash notification */}
              {lastTradeFlash && (
                <div className="animate-in slide-in-from-right-2 fade-in bg-surface-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white">
                  {lastTradeFlash}
                </div>
              )}
              <BotControls onAction={refreshAll} />
            </div>
          </div>

          {/* Metrics */}
          <MetricsBar metrics={dailyMetrics} />

          {/* Main content grid */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">

            {/* Left: 2/3 width — trades */}
            <div className="xl:col-span-2 space-y-5">

              {/* P&L Sparkline */}
              <PnLSparkline closedTrades={closedTrades as any[]} />

              {/* Open Positions */}
              <div className="card">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse inline-block" />
                    Open Positions
                    <span className="bg-slate-700 text-slate-300 text-[10px] px-1.5 py-0.5 rounded-full">
                      {openTrades.length}
                    </span>
                  </h2>
                  {openTrades.length > 0 && (
                    <button
                      onClick={async () => {
                        if (confirm('Exit ALL open positions?')) {
                          await tradesApi.exitAll()
                          refreshAll()
                        }
                      }}
                      className="text-xs text-red-400 hover:text-red-300 transition-colors border border-red-900/50 hover:border-red-700/50 px-2 py-1 rounded"
                    >
                      Exit All
                    </button>
                  )}
                </div>
                <OpenTradesTable trades={openTrades} onExit={refreshAll} />
              </div>

              {/* Closed Trades */}
              <div className="card">
                <h2 className="text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
                  Today's Closed Trades
                  <span className="bg-slate-700 text-slate-300 text-[10px] px-1.5 py-0.5 rounded-full">
                    {closedTrades.length}
                  </span>
                </h2>
                <RecentTradesTable trades={closedTrades} />
              </div>
            </div>

            {/* Right: 1/3 width — action feed */}
            <div className="xl:col-span-1">
              <ActionFeed />
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
