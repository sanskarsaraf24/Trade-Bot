'use client'
import { useEffect, useRef, useCallback } from 'react'

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost/ws'

type WSMessage = {
  type: 'trade_update' | 'metrics_update' | 'log_event'
  data?: Record<string, unknown>
  timestamp?: string
}

type WSHandlers = {
  onTradeUpdate?: () => void
  onMetricsUpdate?: (data: Record<string, unknown>) => void
  onLogEvent?: (data: Record<string, unknown>) => void
  onConnect?: () => void
  onDisconnect?: () => void
}

export function useTradingWS(userId: string | null, handlers: WSHandlers) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const connect = useCallback(() => {
    if (!userId) return
    const token = typeof window !== 'undefined' ? localStorage.getItem('trading_token') : ''
    if (!token) return

    const url = `${WS_URL}/${userId}?token=${token}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      handlers.onConnect?.()
      // Ping keepalive every 30s
      const ping = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping')
      }, 30_000)
      ws.addEventListener('close', () => clearInterval(ping))
    }

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data)
        switch (msg.type) {
          case 'trade_update':
            handlers.onTradeUpdate?.()
            break
          case 'metrics_update':
            handlers.onMetricsUpdate?.(msg.data || {})
            break
          case 'log_event':
            handlers.onLogEvent?.(msg.data || {})
            break
        }
      } catch { /* ignore malformed */ }
    }

    ws.onclose = () => {
      handlers.onDisconnect?.()
      // Reconnect after 5s
      reconnectRef.current = setTimeout(connect, 5_000)
    }

    ws.onerror = () => ws.close()
  }, [userId, handlers])

  useEffect(() => {
    connect()
    return () => {
      reconnectRef.current && clearTimeout(reconnectRef.current)
      wsRef.current?.close()
    }
  }, [connect])
}
