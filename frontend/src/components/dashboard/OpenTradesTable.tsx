'use client'
import { tradesApi } from '@/lib/api'
import { X, TrendingUp, TrendingDown, Target, Activity } from 'lucide-react'
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
    <div className="mt-2 group/progress">
      <div className="flex justify-between text-[8px] font-bold uppercase tracking-widest mb-1 shadow-xs">
        <span className="text-rose-500 bg-rose-50 px-1 rounded border border-rose-100">SL ₹{sl?.toLocaleString()}</span>
        <span className="text-emerald-500 bg-emerald-50 px-1 rounded border border-emerald-100">Target ₹{target?.toLocaleString()}</span>
      </div>
      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden shadow-inner">
        <div
          className={clsx(
            'h-full rounded-full transition-all duration-700 ease-out',
            isProfit ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.3)]' : 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.3)]'
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
      <div className="flex flex-col items-center justify-center py-16 text-slate-400 bg-slate-50/30 rounded-2xl border-2 border-dashed border-slate-100">
        <Activity className="w-10 h-10 mb-3 opacity-20" />
        <p className="text-[11px] font-bold uppercase tracking-widest">Market Neutral - No Exposure</p>
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
            <th className="pl-0">Asset & Thesis</th>
            <th>Signal</th>
            <th className="text-right">Entry</th>
            <th className="text-right">Floating P&L</th>
            <th className="text-right">Conf</th>
            <th className="text-right">Hold</th>
            <th className="pr-0"></th>
          </tr>
        </thead>
        <tbody>
          {typed.map((trade) => (
            <tr key={trade.id} className="animate-in fade-in slide-in-from-left-2 duration-300">
              <td className="max-w-[220px] py-5 pl-0">
                <div className="flex items-center gap-2 mb-1.5">
                   <Target className="w-3 h-3 text-indigo-500" />
                   <span className="font-black text-slate-900 tracking-tight">{trade.symbol}</span>
                </div>
                <p className="text-[10px] font-medium text-slate-500 leading-relaxed line-clamp-2 italic"
                   title={trade.claude_reasoning}>
                  "{trade.claude_reasoning || 'No thesis provided'}"
                </p>
                <ProgressBar
                  entry={trade.entry_price}
                  current={trade.entry_price + (trade.pnl / (trade.quantity || 1))}
                  sl={trade.stop_loss}
                  target={trade.target}
                  signal={trade.signal}
                />
              </td>
              <td className="py-5">
                <span className={clsx('chip',
                  trade.signal.includes('BUY') ? 'chip-profit' : 'chip-loss')}>
                  {trade.signal.replace('_STOCK', '').replace('_', ' ')}
                </span>
              </td>
              <td className="text-right font-mono text-xs font-bold text-slate-900 py-5 px-4">
                ₹{trade.entry_price.toLocaleString()}
              </td>
              <td className={clsx('text-right py-5 px-4')}>
                <div className={clsx('flex items-center justify-end gap-1.5 font-black text-sm',
                  trade.pnl >= 0 ? 'text-emerald-600' : 'text-rose-600')}>
                  {trade.pnl >= 0 ? '+' : ''}₹{Math.abs(trade.pnl).toLocaleString()}
                </div>
                <div className={clsx('text-[10px] font-bold uppercase tracking-widest mt-0.5',
                  trade.pnl_percent >= 0 ? 'text-emerald-500' : 'text-rose-500')}>
                  {trade.pnl_percent >= 0 ? '+' : ''}{trade.pnl_percent?.toFixed(2)}% ROI
                </div>
              </td>
              <td className="text-right py-5 px-4">
                 <div className="flex flex-col items-end gap-1">
                    <span className="text-[10px] font-black text-slate-900">{trade.confidence?.toFixed(0)}%</span>
                    <div className="w-10 h-1 bg-slate-100 rounded-full overflow-hidden shadow-inner">
                        <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${trade.confidence}%` }} />
                    </div>
                 </div>
              </td>
              <td className="text-right text-[11px] font-bold text-slate-400 font-mono py-5 px-4">
                {duration(trade.entry_time)}
              </td>
              <td className="text-right py-5 pr-0">
                <button
                  onClick={() => handleExit(trade.id, trade.symbol)}
                  className="p-2 rounded-xl text-slate-300 hover:text-rose-600 hover:bg-rose-50 transition-all duration-200 shadow-xs border border-transparent hover:border-rose-100"
                  title="Force Close Position"
                >
                  <X className="w-4 h-4" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
