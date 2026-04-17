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
    return <p className="text-sm text-slate-500 text-center py-8">No closed trades today</p>
  }

  const reasonLabel = (r: string) => ({
    SL_HIT: 'SL Hit',
    TARGET_HIT: '✓ Target',
    MANUAL_EXIT: 'Manual',
    EOD_CLOSE: 'EOD',
  }[r] || r)

  return (
    <div className="overflow-x-auto">
      <table className="data-table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Side</th>
            <th className="text-right">Entry</th>
            <th className="text-right">Exit</th>
            <th className="text-right">P&amp;L</th>
            <th>Reason</th>
            <th className="text-right">Time</th>
          </tr>
        </thead>
        <tbody>
          {typed.map((trade) => (
            <tr key={trade.id} className="animate-fade-in">
              <td className="font-medium text-white">{trade.symbol}</td>
              <td>
                <span className={clsx('chip text-[10px]',
                  trade.signal.includes('BUY') ? 'chip-profit' : 'chip-loss')}>
                  {trade.signal}
                </span>
              </td>
              <td className="text-right font-mono text-sm">₹{trade.entry_price?.toLocaleString()}</td>
              <td className="text-right font-mono text-sm">₹{trade.exit_price?.toLocaleString()}</td>
              <td className={clsx('text-right font-mono font-bold text-sm',
                trade.pnl >= 0 ? 'text-profit' : 'text-loss')}>
                {trade.pnl >= 0 ? '+' : ''}₹{trade.pnl?.toLocaleString()}
              </td>
              <td>
                <span className={clsx('chip text-[10px]',
                  trade.exit_reason === 'TARGET_HIT' ? 'chip-profit'
                    : trade.exit_reason === 'SL_HIT' ? 'chip-loss' : 'chip-brand')}>
                  {reasonLabel(trade.exit_reason)}
                </span>
              </td>
              <td className="text-right text-xs text-slate-400">
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
