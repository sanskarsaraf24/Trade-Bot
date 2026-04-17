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
      <div className="flex items-center gap-2">
        {/* Broker indicator */}
        {brokerType && (
          <span className="text-[10px] text-slate-500 flex items-center gap-1">
            {brokerType === 'paper' ? (
              <><WifiOff className="w-3 h-3 text-yellow-500" /> Paper</>
            ) : (
              <><Wifi className="w-3 h-3 text-green-500" /> {brokerType}</>
            )}
          </span>
        )}

        {/* Status badge */}
        <span className={clsx(
          'chip text-[10px]',
          isRunning ? 'chip-profit' : isPaused ? 'chip-brand' : 'bg-slate-800 text-slate-400'
        )}>
          <span className={clsx(
            'status-dot',
            isRunning ? 'bg-profit blink' : isPaused ? 'bg-brand-400 blink' : 'bg-slate-600'
          )} />
          {isRunning ? 'Running' : isPaused ? 'Paused' : isStopped ? 'Stopped' : status}
        </span>

        {isStopped && (
          <button id="btn-start-bot" onClick={() => run(botApi.start)} disabled={loading}
            className="btn-success disabled:opacity-50">
            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            Start Bot
          </button>
        )}

        {isRunning && (
          <button id="btn-pause-bot" onClick={() => run(botApi.pause)} disabled={loading}
            className="btn-ghost disabled:opacity-50">
            <Pause className="w-4 h-4" /> Pause
          </button>
        )}

        {isPaused && (
          <button id="btn-resume-bot" onClick={() => run(botApi.resume)} disabled={loading}
            className="btn-primary disabled:opacity-50">
            <Play className="w-4 h-4" /> Resume
          </button>
        )}

        {(isRunning || isPaused) && (
          <button id="btn-stop-bot" disabled={loading}
            onClick={() => { if (confirm('Stop bot and close all positions?')) run(botApi.stop) }}
            className="btn-danger disabled:opacity-50">
            <Square className="w-4 h-4" /> Stop
          </button>
        )}

        <button id="btn-refresh" onClick={() => { onAction() }} disabled={loading}
          className="btn-ghost disabled:opacity-50 !px-2" title="Refresh">
          <RefreshCw className={clsx('w-4 h-4', loading && 'animate-spin')} />
        </button>
      </div>

      {/* Error inline */}
      {error && (
        <p className="text-xs text-red-400 animate-in fade-in max-w-xs text-right">{error}</p>
      )}
    </div>
  )
}
