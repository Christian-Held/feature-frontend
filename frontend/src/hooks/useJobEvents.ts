import { useEffect, useRef, useState } from 'react'
import { apiClient } from '../lib/api'
import type { Job, JobEvent } from '../lib/api'
import { queryClient } from '../lib/queryClient'

const RECONNECT_DELAY = 5_000

type ConnectionStatus = 'connecting' | 'open' | 'closed' | 'error'

export function useJobEvents() {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)
  const [status, setStatus] = useState<ConnectionStatus>('connecting')

  useEffect(() => {
    function connect() {
      setStatus('connecting')
      const ws = new WebSocket(apiClient.websocketUrl)
      wsRef.current = ws

      ws.onopen = () => {
        setStatus('open')
      }

      ws.onmessage = (event) => {
        try {
          const data: JobEvent = JSON.parse(event.data)
          queryClient.setQueryData<Job[]>(['jobs'], (jobs = []) => {
            const idx = jobs.findIndex((job) => job.id === data.payload.id)
            if (idx >= 0) {
              const next = [...jobs]
              next[idx] = { ...jobs[idx], ...data.payload }
              return next
            }
            return [data.payload, ...jobs]
          })
        } catch (error) {
          console.error('Failed to parse job event', error)
        }
      }

      ws.onerror = () => {
        setStatus('error')
      }

      ws.onclose = () => {
        setStatus('closed')
        if (reconnectTimeoutRef.current) {
          window.clearTimeout(reconnectTimeoutRef.current)
        }
        reconnectTimeoutRef.current = window.setTimeout(connect, RECONNECT_DELAY)
      }
    }

    connect()

    return () => {
      if (reconnectTimeoutRef.current) {
        window.clearTimeout(reconnectTimeoutRef.current)
      }
      wsRef.current?.close()
    }
  }, [])

  return status
}
