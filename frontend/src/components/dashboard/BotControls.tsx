'use client'
import { useState } from 'react'
import { botApi } from '@/lib/api'
import { useBotStore } from '@/store/trading'
import { Play, Pause, Square, RefreshCw } from 'lucide-react'
import clsx from 'clsx'

export default function BotControls({ onAction }: { onAction: () => void }) {
  const { status } = useBotStore()
  const [loading, setLoading] = useState(false)

  const run = async (fn: () => Promise<unknown>) => {
    setLoading(true)
    try {
      await fn()
      onAction()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      alert(err.response?.data?.detail || 'Action failed')
    } finally {
      setLoading(false)
    }
  }

  const isRunning = status === 'running'
  const isPaused = status === 'paused'
  const isStopped = status === 'stopped' || status === 'never_started'

  return (
    <div className="flex items-center gap-2">
      {/* Status badge */}
      <span className={clsx(
        'chip text-xs mr-1',
        isRunning ? 'chip-profit' : isPaused ? 'chip-brand' : 'bg-slate-800 text-slate-400'
      )}>
        <span className={clsx('status-dot', isRunning ? 'bg-profit blink' : isPaused ? 'bg-brand-400 blink' : 'bg-slate-600')} />
        {isRunning ? 'Running' : isPaused ? 'Paused' : 'Stopped'}
      </span>

      {/* Start */}
      {isStopped && (
        <button
          id="btn-start-bot"
          onClick={() => run(botApi.start)}
          disabled={loading}
          className="btn-success disabled:opacity-50"
        >
          <Play className="w-4 h-4" /> Start Bot
        </button>
      )}

      {/* Pause / Resume */}
      {isRunning && (
        <button
          id="btn-pause-bot"
          onClick={() => run(botApi.pause)}
          disabled={loading}
          className="btn-ghost disabled:opacity-50"
        >
          <Pause className="w-4 h-4" /> Pause
        </button>
      )}
      {isPaused && (
        <button
          id="btn-resume-bot"
          onClick={() => run(botApi.resume)}
          disabled={loading}
          className="btn-primary disabled:opacity-50"
        >
          <Play className="w-4 h-4" /> Resume
        </button>
      )}

      {/* Stop */}
      {(isRunning || isPaused) && (
        <button
          id="btn-stop-bot"
          onClick={() => {
            if (confirm('Stop bot and close all positions?')) run(botApi.stop)
          }}
          disabled={loading}
          className="btn-danger disabled:opacity-50"
        >
          <Square className="w-4 h-4" /> Stop
        </button>
      )}

      {/* Refresh */}
      <button
        id="btn-refresh"
        onClick={() => run(async () => { onAction() })}
        disabled={loading}
        className="btn-ghost disabled:opacity-50 !px-2"
        title="Refresh"
      >
        <RefreshCw className={clsx('w-4 h-4', loading ? 'animate-spin' : '')} />
      </button>
    </div>
  )
}
