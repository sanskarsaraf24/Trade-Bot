'use client'
import { TrendingUp, TrendingDown, Target, Wallet, Award, Activity } from 'lucide-react'
import clsx from 'clsx'

interface MetricsBarProps {
  metrics: Record<string, unknown>
}

function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  positive,
}: {
  label: string
  value: string
  sub?: string
  icon: React.ElementType
  positive?: boolean
}) {
  return (
    <div className="stat-card">
      <div className="flex items-center justify-between">
        <span className="stat-label">{label}</span>
        <Icon className={clsx('w-4 h-4', positive === undefined ? 'text-slate-500'
            : positive ? 'text-profit' : 'text-loss')} />
      </div>
      <span className={clsx(
        'stat-value',
        positive === undefined ? 'text-white'
          : positive ? 'text-profit' : 'text-loss'
      )}>
        {value}
      </span>
      {sub && <span className="text-xs text-slate-500">{sub}</span>}
    </div>
  )
}

function fmt(n: number) {
  return n >= 0 ? `+₹${n.toLocaleString()}` : `-₹${Math.abs(n).toLocaleString()}`
}

export default function MetricsBar({ metrics }: MetricsBarProps) {
  const pnl = Number(metrics.total_pnl || 0)
  const winRate = Number(metrics.win_rate || 0)
  const trades = Number(metrics.total_trades || 0)
  const pnlPct = Number(metrics.pnl_percent || 0)
  const openPos = Number(metrics.open_positions || 0)
  const pf = Number(metrics.profit_factor || 0)

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
      <StatCard
        label="Today's P&L"
        value={fmt(pnl)}
        sub={`${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(3)}%`}
        icon={pnl >= 0 ? TrendingUp : TrendingDown}
        positive={pnl >= 0}
      />
      <StatCard
        label="Open Positions"
        value={String(openPos)}
        icon={Activity}
      />
      <StatCard
        label="Total Trades"
        value={String(trades)}
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
        icon={Wallet}
        positive={pf >= 1}
      />
      <StatCard
        label="Avg Win / Loss"
        value={metrics.avg_win
          ? `₹${Number(metrics.avg_win).toLocaleString()} / ₹${Number(metrics.avg_loss).toLocaleString()}`
          : '—'}
        icon={TrendingUp}
      />
    </div>
  )
}
