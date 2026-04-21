'use client'
import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Sidebar from '@/components/shared/Sidebar'
import MetricsBar from '@/components/dashboard/MetricsBar'
import OpenTradesTable from '@/components/dashboard/OpenTradesTable'
import RecentTradesTable from '@/components/dashboard/RecentTradesTable'
import BotControls from '@/components/dashboard/BotControls'
import PnLSparkline from '@/components/dashboard/PnLSparkline'
import ActionFeed from '@/components/dashboard/ActionFeed'
import { tradesApi, metricsApi, botApi } from '@/lib/api'
import { useAuthStore, useBotStore, useLogStore } from '@/store/trading'
import { useTradingWS } from '@/lib/websocket'
import { Activity } from 'lucide-react'

export default function Dashboard() {
  const router = useRouter()
  const { token, userId } = useAuthStore()
  const { setStatus } = useBotStore()
  const { logs, setLogs, addLog } = useLogStore()
  
  const [openTrades, setOpenTrades] = useState([])
  const [closedTrades, setClosedTrades] = useState([])
  const [dailyMetrics, setDailyMetrics] = useState<any>({})
  const [floatingPositions, setFloatingPositions] = useState<Record<string, {current_price: number, floating_pnl: number}>>({}) 
  const [loading, setLoading] = useState(true)
  const [wsConnected, setWsConnected] = useState(false)
  const [lastTradeFlash, setLastTradeFlash] = useState<string | null>(null)

  const refreshAll = useCallback(async () => {
    if (!token) return
    try {
      const [statusRes, openRes, closedRes, metricsRes, logsRes] = await Promise.all([
        botApi.status(),
        tradesApi.open(),
        tradesApi.closed(30),
        metricsApi.daily(),
        metricsApi.logs(50)
      ])
      
      setStatus({
        status: statusRes.data.status,
        openPositions: statusRes.data.open_positions,
        uptime: statusRes.data.uptime_seconds,
        brokerType: statusRes.data.broker_type,
        lastUpdate: statusRes.data.last_update,
      })
      
      setOpenTrades(openRes.data)
      setClosedTrades(closedRes.data)
      setDailyMetrics(metricsRes.data)
      setLogs(logsRes.data)
      setLoading(false)
    } catch { 
      setLoading(false)
    }
  }, [token, setStatus, setLogs])

  useEffect(() => {
    if (!token) { router.push('/login'); return }
    refreshAll()
    const interval = setInterval(refreshAll, 20_000)
    // Poll REST floating P&L every 15s as fallback when WS isn't streaming
    const floatInterval = setInterval(async () => {
      try {
        const { data } = await tradesApi.floatingPnl()
        const map: Record<string, {current_price: number, floating_pnl: number}> = {}
        ;(data?.positions || []).forEach((p: any) => { map[p.symbol] = { current_price: p.current_price, floating_pnl: p.floating_pnl } })
        setFloatingPositions(map)
      } catch {}
    }, 15_000)
    return () => { clearInterval(interval); clearInterval(floatInterval) }
  }, [token, router, refreshAll])

  useTradingWS(userId, {
    onConnect: () => setWsConnected(true),
    onDisconnect: () => setWsConnected(false),
    onTradeUpdate: (data) => {
      tradesApi.open().then((r) => setOpenTrades(r.data))
      tradesApi.closed(30).then((r) => setClosedTrades(r.data))
      metricsApi.daily().then((r) => setDailyMetrics(r.data))
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
      // Capture live prices + floating P&L from engine's WS broadcast
      const map: Record<string, {current_price: number, floating_pnl: number}> = {}
      ;((data.open_positions_detail as any[]) || []).forEach((p) => {
        map[p.symbol] = { current_price: p.current_price, floating_pnl: p.floating_pnl }
      })
      setFloatingPositions(map)
      metricsApi.daily().then((r) => setDailyMetrics(r.data))
    },
    onLogEvent: (data) => addLog(data as any),
  })

  if (loading && !token) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-50">
        <div className="text-indigo-600 font-bold animate-pulse text-sm tracking-widest uppercase">Initializing Terminal...</div>
      </div>
    )
  }

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <Sidebar active="dashboard" />

      <main className="flex-1 overflow-y-auto">
        <div className="p-8 space-y-8 max-w-screen-2xl mx-auto">

          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-black text-slate-900 tracking-tight">Market Overview</h1>
              <p className="text-xs font-semibold text-slate-400 mt-1 flex items-center gap-2 uppercase tracking-widest">
                <span className={wsConnected ? 'text-emerald-500' : 'text-amber-500'}>
                  {wsConnected ? '● WebSocket Live' : '○ Synchronizing...'}
                </span>
                <span className="text-slate-300">|</span>
                <span>Real-time monitoring</span>
              </p>
            </div>
            <div className="flex items-center gap-4">
              {lastTradeFlash && (
                <div className="animate-in slide-in-from-right-4 fade-in bg-white border border-indigo-100 shadow-soft rounded-xl px-4 py-2.5 text-xs font-bold text-slate-900 flex items-center gap-2">
                  <Activity className="w-3.5 h-3.5 text-indigo-500 animate-pulse" />
                  {lastTradeFlash}
                </div>
              )}
              <BotControls onAction={refreshAll} />
            </div>
          </div>

          {/* Metrics Bar */}
          <MetricsBar metrics={dailyMetrics} />

          {/* Layout Grid */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">

            {/* Trading Column */}
            <div className="xl:col-span-2 space-y-8">
              
              {/* Chart Section */}
              <div className="card !p-0 overflow-hidden border-none shadow-soft">
                <div className="p-6 border-b border-slate-50 flex items-center justify-between">
                  <h2 className="section-title !mb-0 tracking-widest">Equity Curve</h2>
                  <span className="text-[10px] font-bold text-slate-400 uppercase">Intraday (₹)</span>
                </div>
                <div className="h-[240px] bg-white">
                  <PnLSparkline closedTrades={closedTrades as any[]} />
                </div>
              </div>

              {/* Open Positions Table */}
              <div className="card border-none shadow-soft">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="section-title !mb-0">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse inline-block mr-1" />
                    Open Positions
                  </h2>
                  <span className="bg-slate-100 text-slate-500 text-[10px] font-bold px-2 py-1 rounded-lg">
                    {openTrades.length} Active
                  </span>
                </div>
                <OpenTradesTable trades={openTrades} floatingPositions={floatingPositions} onExit={refreshAll} />
              </div>

              {/* History Table */}
              <div className="card border-none shadow-soft">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="section-title !mb-0">Trade History</h2>
                  <span className="bg-slate-100 text-slate-500 text-[10px] font-bold px-2 py-1 rounded-lg">
                    {closedTrades.length} Executed
                  </span>
                </div>
                <RecentTradesTable trades={closedTrades} />
              </div>
            </div>

            {/* Information Column */}
            <div className="xl:col-span-1">
              <ActionFeed />
            </div>

          </div>
        </div>
      </main>
    </div>
  )
}
