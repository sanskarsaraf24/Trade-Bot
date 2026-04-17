'use client'
import { useEffect, useRef, useCallback } from 'react'

// WS_URL should be the base, e.g. ws://host — we append /api/ws/{userId}
const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost'

type WSMessage = {
  type: 'trade_update' | 'metrics_update' | 'log_event'
  data?: Record<string, unknown>
  timestamp?: string
}

type WSHandlers = {
  onTradeUpdate?: (data: Record<string, unknown>) => void
  onMetricsUpdate?: (data: Record<string, unknown>) => void
  onLogEvent?: (data: Record<string, unknown>) => void
  onConnect?: () => void
  onDisconnect?: () => void
}

export function useTradingWS(userId: string | null, handlers: WSHandlers) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const handlersRef = useRef(handlers)
  handlersRef.current = handlers

  const connect = useCallback(() => {
    if (!userId) return
    const token = typeof window !== 'undefined' ? localStorage.getItem('trading_token') : ''
    if (!token) return

    // Correct path: /api/ws/{user_id}
    const wsUrl = WS_BASE.replace(/\/api\/ws\/?$/, '').replace(/\/$/, '')
    const url = `${wsUrl}/api/ws/${userId}?token=${token}`

    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        handlersRef.current.onConnect?.()
        // Keepalive ping every 25s
        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send('ping')
        }, 25_000)
        ws.addEventListener('close', () => clearInterval(pingInterval))
      }

      ws.onmessage = (event) => {
        if (event.data === 'pong') return
        try {
          const msg: WSMessage = JSON.parse(event.data)
          switch (msg.type) {
            case 'trade_update':
              handlersRef.current.onTradeUpdate?.(msg.data || {})
              break
            case 'metrics_update':
              handlersRef.current.onMetricsUpdate?.(msg.data || {})
              break
            case 'log_event':
              handlersRef.current.onLogEvent?.(msg.data || {})
              break
          }
        } catch { /* ignore malformed */ }
      }

      ws.onclose = () => {
        handlersRef.current.onDisconnect?.()
        // Reconnect after 5s
        reconnectRef.current = setTimeout(connect, 5_000)
      }

      ws.onerror = () => ws.close()
    } catch (e) {
      console.warn('WebSocket connection failed:', e)
      reconnectRef.current = setTimeout(connect, 5_000)
    }
  }, [userId])

  useEffect(() => {
    connect()
    return () => {
      reconnectRef.current && clearTimeout(reconnectRef.current)
      wsRef.current?.close()
    }
  }, [connect])
}
