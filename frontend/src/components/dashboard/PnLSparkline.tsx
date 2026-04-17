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
      <div className="flex flex-col items-center justify-center h-[240px] text-slate-400 bg-slate-50/50">
        <p className="text-[10px] font-bold uppercase tracking-widest opacity-50">Equilibrium - No Trade Data</p>
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
  const color = isProfit ? '#10b981' : '#f43f5e'
  const gradientId = isProfit ? 'pnlProfit' : 'pnlLoss'

  return (
    <div className="h-full w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 20, right: 30, left: 30, bottom: 20 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.15} />
              <stop offset="95%" stopColor={color} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <XAxis 
            dataKey="time" 
            tick={{ fill: '#94a3b8', fontSize: 10, fontWeight: 600 }} 
            tickLine={false} 
            axisLine={false}
            dy={10}
          />
          <YAxis 
            hide 
            domain={['dataMin - 50', 'dataMax + 50']}
          />
          <ReferenceLine y={0} stroke="#e2e8f0" strokeDasharray="5 5" />
          <Tooltip
            contentStyle={{
              background: '#ffffff',
              border: '1px solid #e2e8f0',
              borderRadius: '12px',
              fontSize: '11px',
              fontWeight: 600,
              boxShadow: '0 4px 12px rgba(0,0,0,0.05)'
            }}
            labelStyle={{ color: '#64748b', marginBottom: '4px', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}
            itemStyle={{ padding: '0' }}
            cursor={{ stroke: '#cbd5e1', strokeWidth: 1 }}
            formatter={(val: number, _name: string, props: any) => [
              <span className={clsx('font-black text-sm', val >= 0 ? 'text-emerald-600' : 'text-rose-600')}>
                ₹{val.toLocaleString()}
              </span>,
              <span className="text-[10px] text-slate-400 uppercase tracking-widest block mt-1">
                Net P&L after {props.payload.trade}
              </span>
            ]}
          />
          <Area
            type="monotone"
            dataKey="pnl"
            stroke={color}
            strokeWidth={3}
            fill={`url(#${gradientId})`}
            animationDuration={1500}
            dot={{ fill: '#ffffff', stroke: color, strokeWidth: 2, r: 4 }}
            activeDot={{ r: 6, stroke: '#ffffff', strokeWidth: 3, fill: color }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
