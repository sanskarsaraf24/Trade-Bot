'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/trading'
import { metricsApi } from '@/lib/api'
import Sidebar from '@/components/shared/Sidebar'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts'
import { RefreshCw } from 'lucide-react'

export default function AnalyticsPage() {
  const { token } = useAuthStore()
  const router = useRouter()
  const [weekly, setWeekly] = useState<{ date: string; pnl: number; trades: number }[]>([])
  const [accuracy, setAccuracy] = useState<{
    profitable_signals?: number
    losing_signals?: number
    accuracy_percent?: number
    total_signals?: number
    avg_confidence?: number
  }>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token) { router.push('/login'); return }
    Promise.all([metricsApi.weekly(), metricsApi.claudeAccuracy()])
      .then(([wRes, aRes]) => {
        setWeekly(wRes.data)
        setAccuracy(aRes.data)
      })
      .finally(() => setLoading(false))
  }, [token, router])

  const profitable = Number(accuracy.profitable_signals || 0)
  const losing = Number(accuracy.losing_signals || 0)
  const pieData = [
    { name: 'Wins', value: profitable },
    { name: 'Losses', value: losing },
  ]
  const COLORS = ['#22c55e', '#ef4444']

  const CustomTooltip = ({ active, payload, label }: {
    active?: boolean
    payload?: { value: number }[]
    label?: string
  }) => {
    if (!active || !payload?.length) return null
    const val = payload[0].value
    return (
      <div className="bg-surface-800 border border-slate-700 rounded-lg p-3 text-xs shadow-xl">
        <p className="text-slate-400 mb-1">{label}</p>
        <p className={val >= 0 ? 'text-profit font-bold' : 'text-loss font-bold'}>
          {val >= 0 ? '+' : ''}₹{val.toLocaleString()}
        </p>
      </div>
    )
  }

  return (
    <div className="flex h-screen overflow-hidden bg-surface-900">
      <Sidebar active="analytics" />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="max-w-5xl space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-white">Analytics</h1>
              <p className="text-xs text-slate-500">7-day performance overview</p>
            </div>
            {loading && <RefreshCw className="w-4 h-4 text-slate-500 animate-spin" />}
          </div>

          {/* 7-day P&L chart */}
          <div className="card">
            <h2 className="text-sm font-semibold text-slate-300 mb-4">Weekly P&amp;L</h2>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={weekly} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="pnlGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }}
                  tickFormatter={(v) => v.slice(5)} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }}
                  tickFormatter={(v) => `₹${(v / 1000).toFixed(1)}k`} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="pnl" stroke="#6366f1" strokeWidth={2}
                  fill="url(#pnlGrad)" dot={{ fill: '#6366f1', r: 3 }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Trade count + AI accuracy */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Bar chart — trades per day */}
            <div className="card">
              <h2 className="text-sm font-semibold text-slate-300 mb-4">Trades Per Day</h2>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={weekly} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }}
                    tickFormatter={(v) => v.slice(5)} />
                  <YAxis tick={{ fill: '#64748b', fontSize: 11 }} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ background: '#1e293b', border: '1px solid #334155',
                      borderRadius: 8, fontSize: 12 }}
                    labelStyle={{ color: '#94a3b8' }}
                  />
                  <Bar dataKey="trades" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Claude accuracy pie */}
            <div className="card flex flex-col items-center justify-center">
              <h2 className="text-sm font-semibold text-slate-300 mb-4 self-start">Claude AI Accuracy</h2>
              {profitable + losing > 0 ? (
                <>
                  <PieChart width={180} height={180}>
                    <Pie data={pieData} cx={90} cy={90} innerRadius={55} outerRadius={80}
                      paddingAngle={3} dataKey="value">
                      {pieData.map((_, i) => (
                        <Cell key={i} fill={COLORS[i]} />
                      ))}
                    </Pie>
                  </PieChart>
                  <p className="text-2xl font-bold text-white -mt-2">
                    {accuracy.accuracy_percent?.toString()}%
                  </p>
                  <p className="text-xs text-slate-400">
                    {profitable}W / {losing}L · {accuracy.total_signals || 0} signals
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    Avg confidence: {accuracy.avg_confidence?.toString()}%
                  </p>
                </>
              ) : (
                <p className="text-sm text-slate-500">No signals yet</p>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
