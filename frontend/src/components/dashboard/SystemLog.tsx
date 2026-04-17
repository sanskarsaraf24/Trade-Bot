'use client'
import { useLogStore } from '@/store/trading'
import clsx from 'clsx'
import { format } from 'date-fns'

const severityColor = {
  info:    'text-slate-400',
  warning: 'text-yellow-400',
  error:   'text-red-400',
}

export default function SystemLog() {
  const { logs } = useLogStore()

  if (!logs.length) {
    return <p className="text-sm text-slate-500 text-center py-6">No log events yet</p>
  }

  return (
    <div className="h-56 overflow-y-auto font-mono text-xs space-y-1 pr-1">
      {logs.map((log, i) => (
        <div key={i} className="flex gap-3 items-start animate-fade-in">
          <span className="text-slate-600 shrink-0 tabular-nums">
            {format(new Date(log.timestamp), 'HH:mm:ss')}
          </span>
          <span className={clsx('shrink-0 uppercase font-medium w-7',
            severityColor[log.severity as keyof typeof severityColor] || 'text-slate-400')}>
            {log.severity === 'info' ? 'INF' : log.severity === 'warning' ? 'WRN' : 'ERR'}
          </span>
          <span className={clsx(
            severityColor[log.severity as keyof typeof severityColor] || 'text-slate-400'
          )}>
            {log.message}
          </span>
        </div>
      ))}
    </div>
  )
}
