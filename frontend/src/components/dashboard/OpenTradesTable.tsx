'use client'
import { tradesApi } from '@/lib/api'
import { X, TrendingUp, TrendingDown } from 'lucide-react'
import clsx from 'clsx'

interface Trade {
  id: string
  symbol: string
  signal: string
  entry_price: number
  pnl: number
  pnl_percent: number
  stop_loss: number
  target: number
  quantity: number
  confidence: number
  claude_reasoning: string
  entry_time: string
}

function ProgressBar({ entry, current, sl, target, signal }: {
  entry: number; current: number; sl: number; target: number; signal: string
}) {
  if (!sl || !target || !entry) return null
  const isBuy = signal.includes('BUY')
  const range = Math.abs(target - sl)
  if (range <= 0) return null

  const pct = isBuy
    ? ((current - sl) / range) * 100
    : ((sl - current) / range) * 100

  const clampedPct = Math.max(0, Math.min(100, pct))
  const isProfit = isBuy ? current > entry : current < entry

  return (
    <div className="mt-1.5">
      <div className="flex justify-between text-[9px] text-slate-600 mb-0.5">
        <span className="text-red-400">SL ₹{sl?.toLocaleString()}</span>
        <span className="text-green-400">T ₹{target?.toLocaleString()}</span>
      </div>
      <div className="h-1 bg-slate-700 rounded-full overflow-hidden">
        <div
          className={clsx(
            'h-full rounded-full transition-all duration-500',
            isProfit ? 'bg-green-500' : 'bg-red-500'
          )}
          style={{ width: `${clampedPct}%` }}
        />
      </div>
    </div>
  )
}

export default function OpenTradesTable({
  trades,
  onExit,
}: {
  trades: unknown[]
  onExit: () => void
}) {
  const typed = trades as Trade[]

  if (!typed.length) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-slate-600">
        <TrendingUp className="w-8 h-8 mb-2 opacity-30" />
        <p className="text-sm">No open positions</p>
        <p className="text-xs mt-1">The bot will open trades when it finds setups</p>
      </div>
    )
  }

  const handleExit = async (id: string, symbol: string) => {
    if (!confirm(`Exit ${symbol} now?`)) return
    try {
      await tradesApi.exitOne(id)
      onExit()
    } catch { alert('Failed to exit trade') }
  }

  const duration = (entryTime: string) => {
    const mins = Math.floor((Date.now() - new Date(entryTime).getTime()) / 60000)
    if (mins < 60) return `${mins}m`
    return `${Math.floor(mins / 60)}h ${mins % 60}m`
  }

  return (
    <div className="overflow-x-auto">
      <table className="data-table">
        <thead>
          <tr>
            <th>Symbol & Setup</th>
            <th>Side</th>
            <th className="text-right">Entry</th>
            <th className="text-right">P&amp;L</th>
            <th className="text-right">Conf</th>
            <th className="text-right">Age</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {typed.map((trade) => (
            <tr key={trade.id} className="animate-fade-in align-top">
              <td className="max-w-[180px]">
                <span className="font-semibold text-white">{trade.symbol}</span>
                <p className="text-[10px] text-slate-500 mt-0.5 leading-relaxed line-clamp-2"
                   title={trade.claude_reasoning}>
                  {trade.claude_reasoning || '—'}
                </p>
                <ProgressBar
                  entry={trade.entry_price}
                  current={trade.entry_price + (trade.pnl / (trade.quantity || 1))}
                  sl={trade.stop_loss}
                  target={trade.target}
                  signal={trade.signal}
                />
              </td>
              <td>
                <span className={clsx('chip text-[10px]',
                  trade.signal.includes('BUY') ? 'chip-profit' : 'chip-loss')}>
                  {trade.signal.replace('_STOCK', '').replace('_', ' ')}
                </span>
              </td>
              <td className="text-right font-mono text-xs">
                ₹{trade.entry_price.toLocaleString()}
              </td>
              <td className={clsx('text-right font-mono font-bold text-sm',
                trade.pnl >= 0 ? 'text-profit' : 'text-loss')}>
                <div className="flex items-center justify-end gap-1">
                  {trade.pnl >= 0
                    ? <TrendingUp className="w-3 h-3" />
                    : <TrendingDown className="w-3 h-3" />}
                  {trade.pnl >= 0 ? '+' : ''}₹{Math.abs(trade.pnl).toLocaleString()}
                </div>
                <div className={clsx('text-[10px] font-normal',
                  trade.pnl_percent >= 0 ? 'text-green-500' : 'text-red-500')}>
                  {trade.pnl_percent >= 0 ? '+' : ''}{trade.pnl_percent?.toFixed(2)}%
                </div>
              </td>
              <td className="text-right">
                <span className={clsx('chip text-[10px]',
                  trade.confidence >= 75 ? 'chip-profit'
                    : trade.confidence >= 60 ? 'chip-brand' : 'bg-slate-700 text-slate-400')}>
                  {trade.confidence?.toFixed(0)}%
                </span>
              </td>
              <td className="text-right text-xs text-slate-400 font-mono">
                {duration(trade.entry_time)}
              </td>
              <td className="text-right">
                <button
                  onClick={() => handleExit(trade.id, trade.symbol)}
                  className="p-1.5 rounded text-slate-600 hover:text-red-400 hover:bg-red-900/20 transition-colors"
                  title="Exit trade"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
