'use client'
import { TrendingUp, TrendingDown, Target, Wallet, Award, Activity, Clock } from 'lucide-react'
import { useBotStore } from '@/store/trading'
import clsx from 'clsx'

interface MetricsBarProps {
  metrics: Record<string, any>
}

function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  positive,
  highlight,
}: {
  label: string
  value: string
  sub?: string
  icon: React.ElementType
  positive?: boolean
  highlight?: boolean
}) {
  return (
    <div className={clsx(
      'stat-card transition-all duration-300 group hover:-translate-y-1',
      highlight && 'bg-indigo-50/50 border-indigo-100 ring-1 ring-indigo-100 shadow-indigo-100/50'
    )}>
      <div className="flex items-center justify-between">
        <span className="stat-label">{label}</span>
        <div className={clsx(
          'p-1.5 rounded-lg transition-colors',
          positive === undefined ? 'bg-slate-50 text-slate-400'
            : positive ? 'bg-emerald-50 text-emerald-500' : 'bg-rose-50 text-rose-500'
        )}>
          <Icon className="w-3.5 h-3.5" />
        </div>
      </div>
      <div className="mt-2">
        <span className={clsx(
          'stat-value block',
          positive === undefined ? 'text-slate-900'
            : positive ? 'text-emerald-600' : 'text-rose-600'
        )}>
          {value}
        </span>
        {sub && <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest leading-none mt-1 inline-block">{sub}</span>}
      </div>
    </div>
  )
}

function fmt(n: number) {
  if (n === 0) return '₹0'
  return n >= 0 ? `+₹${n.toLocaleString()}` : `-₹${Math.abs(n).toLocaleString()}`
}

export default function MetricsBar({ metrics }: MetricsBarProps) {
  const { status, openPositions, uptime } = useBotStore()

  const pnl = Number(metrics.total_pnl || 0)
  const winRate = Number(metrics.win_rate || 0)
  const trades = Number(metrics.total_trades || 0)
  const pnlPct = Number(metrics.pnl_percent || 0)
  const openPos = Number(metrics.open_positions || openPositions || 0)
  const pf = Number(metrics.profit_factor || 0)
  const avgWin = Number(metrics.avg_win || 0)
  const avgLoss = Number(metrics.avg_loss || 0)

  const uptimeStr = uptime
    ? `${Math.floor(uptime / 3600)}h ${Math.floor((uptime % 3600) / 60)}m`
    : '—'

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 xl:grid-cols-8 gap-4">
      <StatCard
        label="Today's P&L"
        value={fmt(pnl)}
        sub={`${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(3)}% Today`}
        icon={pnl >= 0 ? TrendingUp : TrendingDown}
        positive={pnl >= 0}
        highlight={pnl !== 0}
      />
      <StatCard
        label="Active"
        value={String(openPos)}
        sub="Positions"
        icon={Activity}
        positive={openPos > 0 ? true : undefined}
      />
      <StatCard
        label="Total Trades"
        value={String(trades)}
        sub="Sessions"
        icon={Target}
      />
      <StatCard
        label="Win Rate"
        value={`${winRate.toFixed(1)}%`}
        sub={`${metrics.winning_trades || 0}W / ${metrics.losing_trades || 0}L`}
        icon={Award}
        positive={winRate >= 50}
      />
      <StatCard
        label="Profit Factor"
        value={pf ? `${pf.toFixed(2)}x` : '—'}
        sub="Gross Performance"
        icon={Wallet}
        positive={pf > 1 ? true : pf > 0 ? false : undefined}
      />
      <StatCard
        label="Avg Profit"
        value={avgWin ? `₹${avgWin.toLocaleString()}` : '—'}
        icon={TrendingUp}
        positive={avgWin > 0 ? true : undefined}
      />
      <StatCard
        label="Avg Loss"
        value={avgLoss ? `₹${avgLoss.toLocaleString()}` : '—'}
        icon={TrendingDown}
        positive={false}
      />
      <StatCard
        label="Uptime"
        value={uptimeStr}
        sub={status === 'running' ? 'Active' : 'Standby'}
        icon={Clock}
        positive={status === 'running' ? true : undefined}
      />
    </div>
  )
}
