'use client'
import { tradesApi } from '@/lib/api'
import { X, Edit2, Check, TrendingUp, TrendingDown, Target, Activity } from 'lucide-react'
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

import { useState } from 'react'
function ProgressBar({ tradeId, entry, current, sl: initialSl, target: initialTarget, signal, onUpdate }: {
  tradeId: string; entry: number; current: number; sl: number; target: number; signal: string; onUpdate: () => void;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [sl, setSl] = useState(initialSl);
  const [target, setTarget] = useState(initialTarget);
  const [updating, setUpdating] = useState(false);

  const handleSave = async () => {
    setUpdating(true);
    try {
      await tradesApi.updateTrade(tradeId, { stop_loss: sl, target });
      setIsEditing(false);
      onUpdate();
    } catch { alert('Failed to update') }
    setUpdating(false);
  };

  if (!initialSl || !initialTarget || !entry) return null
  const isBuy = signal.includes('BUY')
  const range = Math.abs(target - sl)
  if (range <= 0) return null

  const pct = isBuy
    ? ((current - sl) / range) * 100
    : ((sl - current) / range) * 100

  const clampedPct = Math.max(0, Math.min(100, pct))
  const isProfit = isBuy ? current > entry : current < entry

  return (
    <div className="mt-2 group/progress relative">
      <div className="flex justify-between items-center text-[8px] font-bold uppercase tracking-widest mb-1 shadow-xs">
        {isEditing ? (
          <div className="flex items-center gap-1">
             <input type="number" step="0.1" value={sl} onChange={e => setSl(Number(e.target.value))} className="w-16 px-1 py-0.5 border border-rose-200 text-rose-600 rounded bg-rose-50" />
          </div>
        ) : (
          <button onClick={() => setIsEditing(true)} className="text-rose-500 bg-rose-50 px-1 rounded border border-rose-100 hover:bg-rose-100 flex items-center gap-1 cursor-pointer">
            SL ₹{sl?.toLocaleString()} <Edit2 className="w-2 h-2" />
          </button>
        )}
        
        {isEditing ? (
          <div className="flex items-center gap-1">
             <button onClick={handleSave} disabled={updating} className="bg-indigo-500 text-white p-0.5 rounded mr-1"><Check className="w-3 h-3" /></button>
             <input type="number" step="0.1" value={target} onChange={e => setTarget(Number(e.target.value))} className="w-16 px-1 py-0.5 border border-emerald-200 text-emerald-600 rounded bg-emerald-50 text-right" />
          </div>
        ) : (
          <button onClick={() => setIsEditing(true)} className="text-emerald-500 bg-emerald-50 px-1 rounded border border-emerald-100 hover:bg-emerald-100 flex items-center gap-1 cursor-pointer">
            <Edit2 className="w-2 h-2" /> Target ₹{target?.toLocaleString()}
          </button>
        )}
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
  floatingPositions = {},
  onExit,
}: {
  trades: unknown[]
  floatingPositions?: Record<string, {current_price: number, floating_pnl: number}>
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
    const mins = Math.floor((Date.now() - new Date(entryTime + (entryTime.endsWith('Z') ? '' : 'Z')).getTime()) / 60000)
    if (mins < 60) return `${mins}m`
    return `${Math.floor(mins / 60)}h ${mins % 60}m`
  }

  return (
    <div className="max-h-96 overflow-y-auto overflow-x-auto border-b border-slate-100 scrollbar-thin relative">
      <table className="data-table">
        <thead className="sticky top-0 bg-white shadow-sm z-10">
          <tr>
            <th className="pl-0 bg-white">Asset & Thesis</th>
            <th className="bg-white">Signal</th>
            <th className="text-right bg-white">Qty</th>
            <th className="text-right bg-white">Entry / LTP</th>
            <th className="text-right bg-white">Floating P&L</th>
            <th className="text-right bg-white">Conf</th>
            <th className="text-right bg-white">Hold</th>
            <th className="pr-0 bg-white"></th>
          </tr>
        </thead>
        <tbody>
          {typed.map((trade) => {
            // Use live broker price from WS/REST polling if available
            const liveData = floatingPositions[trade.symbol]
            const livePnl = liveData ? liveData.floating_pnl : trade.pnl
            const livePrice = liveData ? liveData.current_price : trade.entry_price
            const livePnlPct = liveData && trade.entry_price && trade.quantity
              ? (liveData.floating_pnl / (trade.entry_price * trade.quantity)) * 100
              : trade.pnl_percent
            return (
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
                  tradeId={trade.id}
                  entry={trade.entry_price}
                  current={livePrice}
                  sl={trade.stop_loss}
                  target={trade.target}
                  signal={trade.signal}
                  onUpdate={onExit}
                />
              </td>
              <td className="py-5">
                <span className={clsx('chip',
                  trade.signal.includes('BUY') ? 'chip-profit' : 'chip-loss')}>
                  {trade.signal.replace('_STOCK', '').replace('_', ' ')}
                </span>
              </td>
              <td className="text-right font-mono text-xs font-bold text-slate-600 py-5 px-4">{trade.quantity || '-'}</td>
              <td className="text-right font-mono text-xs font-bold py-5 px-4">
                <div className="text-slate-900">₹{trade.entry_price.toLocaleString()}</div>
                {liveData && <div className="text-[10px] text-indigo-600 mt-0.5" title="Last Traded Price">LTP: ₹{livePrice.toLocaleString()}</div>}
              </td>
              <td className={clsx('text-right py-5 px-4')}>
                <div className={clsx('flex items-center justify-end gap-1.5 font-black text-sm',
                  livePnl >= 0 ? 'text-emerald-600' : 'text-rose-600')}>
                  {liveData && <span className="text-[8px] font-black tracking-widest text-indigo-400 mr-1">LIVE</span>}
                  {livePnl >= 0 ? '+' : ''}₹{Math.abs(livePnl).toLocaleString()}
                </div>
                <div className={clsx('text-[10px] font-bold uppercase tracking-widest mt-0.5',
                  livePnlPct >= 0 ? 'text-emerald-500' : 'text-rose-500')}>
                  {livePnlPct >= 0 ? '+' : ''}{livePnlPct?.toFixed(2)}% ROI
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
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
