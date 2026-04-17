'use client'
import { useLogStore } from '@/store/trading'
import clsx from 'clsx'
import { format } from 'date-fns'
import { Activity, AlertTriangle, CheckCircle, Info, XCircle, TrendingUp, TrendingDown } from 'lucide-react'

const EVENT_CONFIG: Record<string, { icon: React.ElementType; color: string; bg: string }> = {
  trade_opened:    { icon: TrendingUp,    color: 'text-green-400',  bg: 'bg-green-900/20' },
  trade_closed:    { icon: TrendingDown,  color: 'text-blue-400',   bg: 'bg-blue-900/20' },
  signal_gen:      { icon: Activity,      color: 'text-indigo-400', bg: 'bg-indigo-900/20' },
  signals_received:{ icon: Activity,      color: 'text-indigo-400', bg: 'bg-indigo-900/20' },
  signal_skipped:  { icon: AlertTriangle, color: 'text-yellow-400', bg: 'bg-yellow-900/20' },
  bot_started:     { icon: CheckCircle,   color: 'text-green-400',  bg: 'bg-green-900/20' },
  bot_stopped:     { icon: XCircle,       color: 'text-red-400',    bg: 'bg-red-900/20' },
  engine_error:    { icon: XCircle,       color: 'text-red-400',    bg: 'bg-red-900/20' },
  claude_error:    { icon: XCircle,       color: 'text-red-400',    bg: 'bg-red-900/20' },
  cycle_start:     { icon: Info,          color: 'text-slate-400',  bg: 'bg-slate-800' },
  cycle_done:      { icon: CheckCircle,   color: 'text-slate-400',  bg: 'bg-slate-800' },
  eod_exit:        { icon: AlertTriangle, color: 'text-orange-400', bg: 'bg-orange-900/20' },
  default:         { icon: Info,          color: 'text-slate-500',  bg: 'bg-slate-800/50' },
}

export default function ActionFeed() {
  const { logs } = useLogStore()

  return (
    <div className="card h-full min-h-[400px] flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-brand-400" />
          Bot Action Feed
        </h2>
        <span className="text-[10px] text-slate-500">{logs.length} events</span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 scrollbar-thin">
        {logs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-slate-600">
            <Activity className="w-8 h-8 mb-2 opacity-40" />
            <p className="text-xs">No events yet. Start the bot to see live actions.</p>
          </div>
        ) : (
          logs.map((log, i) => {
            const cfg = EVENT_CONFIG[log.event_type] || EVENT_CONFIG.default
            const Icon = cfg.icon
            return (
              <div
                key={i}
                className={clsx(
                  'flex gap-2.5 p-2.5 rounded-lg border border-slate-700/50 animate-in fade-in slide-in-from-top-1',
                  cfg.bg,
                  i === 0 && 'ring-1 ring-brand-500/20'
                )}
              >
                <div className={clsx('mt-0.5 shrink-0', cfg.color)}>
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className={clsx('text-xs leading-relaxed', cfg.color)}>
                    {log.message}
                  </p>
                  <p className="text-[10px] text-slate-600 mt-0.5 font-mono">
                    {format(new Date(log.timestamp), 'HH:mm:ss')}
                  </p>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
