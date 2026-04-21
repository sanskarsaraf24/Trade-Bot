'use client'
import clsx from 'clsx'
import { format } from 'date-fns'
import { useState } from 'react'
import { Info, X } from 'lucide-react'

interface Trade {
  id: string
  symbol: string
  signal: string
  entry_price: number
  exit_price: number
  pnl: number
  exit_reason: string
  exit_time: string
  quantity?: number
  confidence: number
  claude_reasoning?: string
}

function ReasoningModal({ trade, onClose }: { trade: Trade; onClose: () => void }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative bg-white rounded-2xl shadow-2xl max-w-sm w-full mx-4 p-6 border border-slate-100"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className={clsx('chip text-xs',
                trade.signal.includes('BUY') ? 'chip-profit' : 'chip-loss')}>
                {trade.signal.replace('_STOCK', '').replace('_', ' ')}
              </span>
              <span className="font-black text-slate-900 text-base tracking-tight">{trade.symbol}</span>
            </div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
              AI Trade Reasoning
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-300 hover:text-slate-600 hover:bg-slate-100 transition-all"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Reasoning body */}
        <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-4 mb-4">
          <p className="text-xs font-medium text-slate-700 leading-relaxed">
            {trade.claude_reasoning || 'No reasoning was recorded for this trade.'}
          </p>
        </div>

        {/* Trade stats */}
        <div className="grid grid-cols-3 gap-3 text-center">
          <div className="bg-slate-50 rounded-xl p-2">
            <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400 mb-1">Entry</p>
            <p className="text-xs font-black text-slate-900">₹{trade.entry_price?.toLocaleString()}</p>
          </div>
          <div className="bg-slate-50 rounded-xl p-2">
            <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400 mb-1">Confidence</p>
            <p className="text-xs font-black text-indigo-600">{trade.confidence?.toFixed(0)}%</p>
          </div>
          <div className={clsx('rounded-xl p-2', trade.pnl >= 0 ? 'bg-emerald-50' : 'bg-rose-50')}>
            <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400 mb-1">P&L</p>
            <p className={clsx('text-xs font-black', trade.pnl >= 0 ? 'text-emerald-600' : 'text-rose-600')}>
              {trade.pnl >= 0 ? '+' : ''}₹{trade.pnl?.toLocaleString()}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function RecentTradesTable({ trades }: { trades: unknown[] }) {
  const typed = trades as Trade[]
  const [activeTrade, setActiveTrade] = useState<Trade | null>(null)

  if (!typed.length) {
    return <p className="text-[11px] font-bold uppercase tracking-widest text-slate-400 text-center py-10 opacity-50">No trades finalized today</p>
  }

  const reasonLabel = (r: string) => ({
    SL_HIT: 'Stop Loss',
    TARGET_HIT: 'Target Hit',
    MANUAL_EXIT: 'Manual Exit',
    EOD_CLOSE: 'Market Close',
  }[r] || r)

  return (
    <>
      {activeTrade && <ReasoningModal trade={activeTrade} onClose={() => setActiveTrade(null)} />}

      <div className="max-h-96 overflow-y-auto overflow-x-auto border-b border-slate-100 scrollbar-thin relative">
        <table className="data-table">
          <thead className="sticky top-0 bg-white shadow-sm z-10">
            <tr>
              <th className="pl-0 bg-white">Asset</th>
              <th className="bg-white">Signal</th>
              <th className="text-right bg-white">Qty</th>
              <th className="text-right bg-white">Entry</th>
              <th className="text-right bg-white">Exit</th>
              <th className="text-right bg-white">Net P&L</th>
              <th className="bg-white">Reason</th>
              <th className="text-right bg-white">Time</th>
              <th className="pr-0 bg-white"></th>
            </tr>
          </thead>
          <tbody>
            {typed.map((trade) => (
              <tr key={trade.id} className="animate-in fade-in duration-300">
                <td className="font-bold text-slate-900 py-4 pl-0">{trade.symbol}</td>
                <td className="py-4">
                  <span className={clsx('chip',
                    trade.signal.includes('BUY') ? 'chip-profit' : 'chip-loss')}>
                    {trade.signal.replace('_STOCK', '').replace('_', ' ')}
                  </span>
                </td>
                <td className="text-right font-mono text-xs font-bold text-slate-600 py-4 px-4">{trade.quantity || '-'}</td>
                <td className="text-right font-mono text-xs font-bold text-slate-600 py-4 px-4">₹{trade.entry_price?.toLocaleString()}</td>
                <td className="text-right font-mono text-xs font-bold text-slate-600 py-4 px-4">₹{trade.exit_price?.toLocaleString()}</td>
                <td className={clsx('text-right font-mono font-black text-sm py-4 px-4',
                  trade.pnl >= 0 ? 'text-emerald-600' : 'text-rose-600')}>
                  {trade.pnl >= 0 ? '+' : ''}₹{trade.pnl?.toLocaleString()}
                </td>
                <td className="py-4 px-4">
                  <span className={clsx('chip',
                    trade.exit_reason === 'TARGET_HIT' ? 'chip-profit'
                      : trade.exit_reason === 'SL_HIT' ? 'chip-loss' : 'chip-brand')}>
                    {reasonLabel(trade.exit_reason)}
                  </span>
                </td>
                <td className="text-right text-[10px] font-bold text-slate-400 uppercase tracking-widest py-4">
                  {trade.exit_time ? format(new Date(trade.exit_time), 'hh:mm a') : '—'}
                </td>
                {/* "I" button */}
                <td className="text-right py-4 pr-0">
                  <button
                    onClick={() => setActiveTrade(trade)}
                    title="View AI Reasoning"
                    className="p-1.5 rounded-lg text-slate-300 hover:text-indigo-600 hover:bg-indigo-50 transition-all duration-200 border border-transparent hover:border-indigo-100"
                  >
                    <Info className="w-3.5 h-3.5" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}
