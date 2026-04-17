'use client'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import { format } from 'date-fns'
import clsx from 'clsx'

interface Trade {
  pnl: number
  exit_time: string
  symbol: string
}

interface Props {
  closedTrades: Trade[]
}

export default function PnLSparkline({ closedTrades }: Props) {
  if (!closedTrades.length) {
    return (
      <div className="card flex items-center justify-center h-28 border-dashed border-slate-700">
        <p className="text-xs text-slate-600">No closed trades today — P&L chart will appear here</p>
      </div>
    )
  }

  // Build cumulative P&L series
  let cumulative = 0
  const data = [...closedTrades]
    .sort((a, b) => new Date(a.exit_time).getTime() - new Date(b.exit_time).getTime())
    .map((t) => {
      cumulative += t.pnl
      return {
        time: format(new Date(t.exit_time), 'HH:mm'),
        pnl: Math.round(cumulative),
        trade: t.symbol,
        this_pnl: t.pnl,
      }
    })

  const finalPnl = data[data.length - 1]?.pnl ?? 0
  const isProfit = finalPnl >= 0
  const color = isProfit ? '#22c55e' : '#ef4444'
  const gradientId = isProfit ? 'pnlProfit' : 'pnlLoss'

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-sm font-semibold text-slate-200">Intraday P&L Curve</h2>
        <span className={clsx(
          'text-sm font-bold font-mono',
          isProfit ? 'text-green-400' : 'text-red-400'
        )}>
          {isProfit ? '+' : ''}₹{finalPnl.toLocaleString()}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={90}>
        <AreaChart data={data} margin={{ top: 5, right: 0, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.25} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="time" tick={{ fill: '#475569', fontSize: 10 }} tickLine={false} axisLine={false} />
          <YAxis hide />
          <ReferenceLine y={0} stroke="#334155" strokeDasharray="3 3" />
          <Tooltip
            contentStyle={{
              background: '#1e293b',
              border: '1px solid #334155',
              borderRadius: 8,
              fontSize: 11,
            }}
            labelStyle={{ color: '#94a3b8' }}
            formatter={(val: number, _name: string, props: any) => [
              `₹${val.toLocaleString()} (${props.payload.trade}: ${props.payload.this_pnl >= 0 ? '+' : ''}₹${props.payload.this_pnl})`,
              'Cumulative',
            ]}
          />
          <Area
            type="monotone"
            dataKey="pnl"
            stroke={color}
            strokeWidth={2}
            fill={`url(#${gradientId})`}
            dot={{ fill: color, r: 2.5 }}
            activeDot={{ r: 4 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
