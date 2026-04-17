'use client'
import { useState } from 'react'
import { botApi } from '@/lib/api'
import { useBotStore } from '@/store/trading'
import { Play, Pause, Square, RefreshCw, Wifi, WifiOff } from 'lucide-react'
import clsx from 'clsx'

export default function BotControls({ onAction }: { onAction: () => void }) {
  const { status, brokerType } = useBotStore()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const run = async (fn: () => Promise<unknown>) => {
    setLoading(true)
    setError('')
    try {
      await fn()
      onAction()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      const msg = err.response?.data?.detail || 'Action failed'
      setError(msg)
      setTimeout(() => setError(''), 6000)
    } finally {
      setLoading(false)
    }
  }

  const isRunning = status === 'running'
  const isPaused = status === 'paused'
  const isStopped = status === 'stopped' || status === 'never_started'

  return (
    <div className="flex flex-col items-end gap-2">
      <div className="flex items-center gap-3">
        {/* Broker indicator */}
        {brokerType && (
          <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-100 rounded-lg">
            {brokerType === 'paper' ? (
              <><WifiOff className="w-3 h-3 text-amber-500" /><span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Simulator</span></>
            ) : (
              <><Wifi className="w-3 h-3 text-emerald-500" /><span className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">Live: {brokerType}</span></>
            )}
          </div>
        )}

        {/* Status badge */}
        <div className={clsx(
          'flex items-center gap-2 px-3 py-1.5 rounded-full border shadow-sm',
          isRunning ? 'bg-emerald-50 border-emerald-100 text-emerald-700' 
            : isPaused ? 'bg-indigo-50 border-indigo-100 text-indigo-700' 
            : 'bg-slate-50 border-slate-200 text-slate-500'
        )}>
          <span className={clsx(
            'w-2 h-2 rounded-full',
            isRunning ? 'bg-emerald-500 blink' : isPaused ? 'bg-indigo-500 blink' : 'bg-slate-300'
          )} />
          <span className="text-[11px] font-bold uppercase tracking-wider">
               {isRunning ? 'System Active' : isPaused ? 'System Paused' : isStopped ? 'System Standby' : status}
          </span>
        </div>

        <div className="h-4 w-px bg-slate-200 mx-1" />

        <div className="flex items-center gap-2">
            {isStopped && (
            <button id="btn-start-bot" onClick={() => run(botApi.start)} disabled={loading}
                className="btn-primary">
                {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                <span className="ml-1 tracking-widest uppercase text-[11px] font-bold">Start Engine</span>
            </button>
            )}

            {isRunning && (
            <button id="btn-pause-bot" onClick={() => run(botApi.pause)} disabled={loading}
                className="btn-ghost">
                <Pause className="w-4 h-4" /> <span className="ml-1 tracking-widest uppercase text-[11px] font-bold">Pause</span>
            </button>
            )}

            {isPaused && (
            <button id="btn-resume-bot" onClick={() => run(botApi.resume)} disabled={loading}
                className="btn-primary">
                <Play className="w-4 h-4" /> <span className="ml-1 tracking-widest uppercase text-[11px] font-bold">Resume</span>
            </button>
            )}

            {(isRunning || isPaused) && (
            <button id="btn-stop-bot" disabled={loading}
                onClick={() => { if (confirm('Emergency Stop: Close all positions?')) run(botApi.stop) }}
                className="btn-danger">
                <Square className="w-4 h-4" /> <span className="ml-1 tracking-widest uppercase text-[11px] font-bold">Stop</span>
            </button>
            )}

            <button id="btn-refresh" onClick={() => { onAction() }} disabled={loading}
            className="btn-ghost !px-3 shadow-sm border border-slate-200" title="Manual Refresh">
            <RefreshCw className={clsx('w-4 h-4 text-slate-400', loading && 'animate-spin')} />
            </button>
        </div>
      </div>

      {/* Error inline */}
      {error && (
        <div className="animate-in slide-in-from-top-1 fade-in bg-rose-50 border border-rose-100 px-3 py-1.5 rounded-lg">
           <p className="text-[10px] font-bold text-rose-600 uppercase tracking-widest text-right">{error}</p>
        </div>
      )}
    </div>
  )
}
