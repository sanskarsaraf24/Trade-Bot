'use client'
import { useLogStore } from '@/store/trading'
import clsx from 'clsx'
import { format } from 'date-fns'

const severityColor = {
  info:    'text-slate-400',
  warning: 'text-amber-500',
  error:   'text-rose-500',
}

export default function SystemLog() {
  const { logs } = useLogStore()

  if (!logs.length) {
    return <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 text-center py-6 opacity-50">No log entries found</p>
  }

  return (
    <div className="h-56 overflow-y-auto font-mono text-xs space-y-2 pr-2 scrollbar-thin">
      {logs.map((log, i) => (
        <div key={i} className="flex gap-4 items-start animate-in fade-in slide-in-from-left-1 duration-200">
          <span className="text-slate-300 shrink-0 tabular-nums font-bold">
            {format(new Date(log.timestamp), 'HH:mm:ss')}
          </span>
          <span className={clsx('shrink-0 uppercase font-black w-8',
            severityColor[log.severity as keyof typeof severityColor] || 'text-slate-400')}>
            {log.severity === 'info' ? 'INF' : log.severity === 'warning' ? 'WRN' : 'ERR'}
          </span>
          <span className={clsx(
            'flex-1 leading-normal',
            severityColor[log.severity as keyof typeof severityColor] || 'text-slate-600'
          )}>
            {log.message}
          </span>
        </div>
      ))}
    </div>
  )
}
