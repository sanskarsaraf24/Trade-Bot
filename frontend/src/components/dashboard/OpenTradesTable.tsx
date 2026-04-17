'use client'
import { tradesApi } from '@/lib/api'
import { X } from 'lucide-react'
import clsx from 'clsx'

interface Trade {
  id: string
  symbol: string
  signal: string
  entry_price: number
  current_price?: number
  pnl: number
  pnl_percent: number
  stop_loss: number
  target: number
  quantity: number
  confidence: number
  claude_reasoning: string
  entry_time: string
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
      <p className="text-sm text-slate-500 text-center py-8">
        No open positions
      </p>
    )
  }

  const handleExit = async (id: string, symbol: string) => {
    if (!confirm(`Exit ${symbol}?`)) return
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
            <th>Symbol</th>
            <th>Side</th>
            <th className="text-right">Entry</th>
            <th className="text-right">SL / Target</th>
            <th className="text-right">P&amp;L</th>
            <th className="text-right">Conf.</th>
            <th className="text-right">Duration</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {typed.map((trade) => (
            <tr key={trade.id} className="animate-fade-in">
              <td>
                <span className="font-medium text-white">{trade.symbol}</span>
                <p className="text-[10px] text-slate-500 mt-0.5 max-w-[140px] truncate"
                   title={trade.claude_reasoning}>
                  {trade.claude_reasoning}
                </p>
              </td>
              <td>
                <span className={clsx('chip text-[10px]',
                  trade.signal.includes('BUY') ? 'chip-profit' : 'chip-loss')}>
                  {trade.signal}
                </span>
              </td>
              <td className="text-right font-mono text-sm">₹{trade.entry_price.toLocaleString()}</td>
              <td className="text-right text-xs">
                <span className="text-loss">₹{trade.stop_loss?.toLocaleString()}</span>
                <span className="text-slate-600"> / </span>
                <span className="text-profit">₹{trade.target?.toLocaleString()}</span>
              </td>
              <td className={clsx('text-right font-mono font-bold text-sm',
                trade.pnl >= 0 ? 'text-profit' : 'text-loss')}>
                {trade.pnl >= 0 ? '+' : ''}₹{trade.pnl.toLocaleString()}
              </td>
              <td className="text-right">
                <span className={clsx('chip text-[10px]',
                  trade.confidence >= 70 ? 'chip-profit' : 'chip-brand')}>
                  {trade.confidence?.toFixed(0)}%
                </span>
              </td>
              <td className="text-right text-xs text-slate-400">
                {duration(trade.entry_time)}
              </td>
              <td className="text-right">
                <button
                  onClick={() => handleExit(trade.id, trade.symbol)}
                  className="p-1 rounded text-slate-500 hover:text-red-400 hover:bg-red-900/20 transition-colors"
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
