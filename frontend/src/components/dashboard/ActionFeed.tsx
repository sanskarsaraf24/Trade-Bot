'use client'
import { useLogStore } from '@/store/trading'
import clsx from 'clsx'
import { format } from 'date-fns'
import { Activity, AlertTriangle, CheckCircle, Info, XCircle, TrendingUp, TrendingDown } from 'lucide-react'

const EVENT_CONFIG: Record<string, { icon: React.ElementType; color: string; bg: string; border: string }> = {
  trade_opened:    { icon: TrendingUp,    color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-100' },
  trade_closed:    { icon: TrendingDown,  color: 'text-blue-600',    bg: 'bg-blue-50',    border: 'border-blue-100' },
  signal_gen:      { icon: Activity,      color: 'text-indigo-600',  bg: 'bg-indigo-50',  border: 'border-indigo-100' },
  signals_received:{ icon: Activity,      color: 'text-indigo-600',  bg: 'bg-indigo-50',  border: 'border-indigo-100' },
  signal_skipped:  { icon: AlertTriangle, color: 'text-amber-600',  bg: 'bg-amber-50',   border: 'border-amber-100' },
  bot_started:     { icon: CheckCircle,   color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-100' },
  bot_stopped:     { icon: XCircle,       color: 'text-rose-600',    bg: 'bg-rose-50',    border: 'border-rose-100' },
  engine_error:    { icon: XCircle,       color: 'text-rose-600',    bg: 'bg-rose-50',    border: 'border-rose-100' },
  claude_error:    { icon: XCircle,       color: 'text-rose-600',    bg: 'bg-rose-50',    border: 'border-rose-100' },
  cycle_start:     { icon: Info,          color: 'text-slate-500',   bg: 'bg-slate-50',   border: 'border-slate-100' },
  cycle_done:      { icon: CheckCircle,   color: 'text-slate-500',   bg: 'bg-slate-50',   border: 'border-slate-100' },
  eod_exit:        { icon: AlertTriangle, color: 'text-orange-600',  bg: 'bg-orange-50',  border: 'border-orange-100' },
  default:         { icon: Info,          color: 'text-slate-400',   bg: 'bg-slate-50',   border: 'border-slate-100' },
}

export default function ActionFeed() {
  const { logs } = useLogStore()

  return (
    <div className="card h-full min-h-[500px] flex flex-col border-none shadow-soft">
      <div className="flex items-center justify-between mb-6">
        <h2 className="section-title !mb-0">
          <Activity className="w-3.5 h-3.5 text-indigo-500" />
          Execution Log
        </h2>
        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{logs.length} Total</span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 pr-2 scrollbar-thin">
        {logs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-slate-400">
            <Activity className="w-10 h-10 mb-3 opacity-20" />
            <p className="text-[11px] font-bold uppercase tracking-widest">Awaiting bot activity...</p>
          </div>
        ) : (
          logs.map((log, i) => {
            const cfg = EVENT_CONFIG[log.event_type] || EVENT_CONFIG.default
            const Icon = cfg.icon
            return (
              <div
                key={i}
                className={clsx(
                  'flex gap-3 p-3.5 rounded-xl border animate-in fade-in slide-in-from-top-2 duration-300',
                  cfg.bg,
                  cfg.border,
                  i === 0 && 'ring-2 ring-indigo-500/10 shadow-sm'
                )}
              >
                <div className={clsx('mt-0.5 shrink-0 p-1.5 rounded-lg bg-white bg-opacity-60 shadow-xs', cfg.color)}>
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-bold text-slate-900 leading-relaxed">
                    {log.message}
                  </p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className={clsx('text-[10px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded bg-white bg-opacity-40 transition-colors', cfg.color)}>
                      {log.event_type.replace(/_/g, ' ')}
                    </span>
                    <span className="text-[10px] font-bold text-slate-400 font-mono">
                      {format(new Date(log.timestamp + (log.timestamp.endsWith('Z') ? '' : 'Z')), 'HH:mm:ss')}
                    </span>
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
