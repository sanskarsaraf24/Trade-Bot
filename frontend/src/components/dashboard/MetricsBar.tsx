'use client'
import { TrendingUp, TrendingDown, Target, Wallet, Award, Activity, Clock, Zap } from 'lucide-react'
import { useBotStore } from '@/store/trading'
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
      'stat-card transition-all duration-300',
      highlight && 'ring-1 ring-brand-500/30 bg-brand-900/10'
    )}>
      <div className="flex items-center justify-between">
        <span className="stat-label">{label}</span>
        <Icon className={clsx(
          'w-4 h-4',
          positive === undefined ? 'text-slate-500'
            : positive ? 'text-profit' : 'text-loss'
        )} />
      </div>
      <span className={clsx(
        'stat-value',
        positive === undefined ? 'text-white'
          : positive ? 'text-profit' : 'text-loss'
      )}>
        {value}
      </span>
      {sub && <span className="text-[10px] text-slate-500">{sub}</span>}
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
    <div className="grid grid-cols-2 sm:grid-cols-4 xl:grid-cols-8 gap-3">
      <StatCard
        label="Today's P&L"
        value={fmt(pnl)}
        sub={`${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(3)}%`}
        icon={pnl >= 0 ? TrendingUp : TrendingDown}
        positive={pnl >= 0}
        highlight={pnl !== 0}
      />
      <StatCard
        label="Open"
        value={String(openPos)}
        sub="positions"
        icon={Activity}
        positive={openPos > 0 ? undefined : undefined}
      />
      <StatCard
        label="Trades"
        value={String(trades)}
        sub="today"
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
        sub="gross P / gross L"
        icon={Wallet}
        positive={pf > 1 ? true : pf > 0 ? false : undefined}
      />
      <StatCard
        label="Avg Win"
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
        label="Bot Uptime"
        value={uptimeStr}
        sub={status === 'running' ? 'running' : status}
        icon={Clock}
        positive={status === 'running' ? true : undefined}
      />
    </div>
  )
}
