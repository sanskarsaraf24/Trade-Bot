'use client'
import clsx from 'clsx'
import { format } from 'date-fns'

interface Trade {
  id: string
  symbol: string
  signal: string
  entry_price: number
  exit_price: number
  pnl: number
  exit_reason: string
  exit_time: string
  confidence: number
}

export default function RecentTradesTable({ trades }: { trades: unknown[] }) {
  const typed = trades as Trade[]

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
    <div className="overflow-x-auto">
      <table className="data-table">
        <thead>
          <tr>
            <th className="pl-0">Asset</th>
            <th>Signal</th>
            <th className="text-right">Entry</th>
            <th className="text-right">Exit</th>
            <th className="text-right">Net P&L</th>
            <th>Reason</th>
            <th className="text-right pr-0">Timestamp</th>
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
              <td className="text-right text-[10px] font-bold text-slate-400 uppercase tracking-widest py-4 pr-0">
                {trade.exit_time
                  ? format(new Date(trade.exit_time), 'hh:mm a')
                  : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
