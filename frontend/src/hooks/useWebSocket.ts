/**
 * React Hook for WebSocket Real-Time Updates
 * Provides easy integration with WebSocket service for live data
 */

import { useEffect, useState, useCallback } from 'react'
import { websocketService } from './websocketService'

interface WebSocketData {
  metrics?: any
  services?: any
  activity?: any
}

export const useWebSocket = () => {
  const [isConnected, setIsConnected] = useState(false)
  const [data, setData] = useState<WebSocketData>({})

  useEffect(() => {
    // Check connection status
    setIsConnected(websocketService.isWebSocketConnected())

    // Subscribe to updates
    const cleanup = websocketService.subscribeToUpdates((eventType, eventData) => {
      setData(prev => ({
        ...prev,
        [eventType]: eventData
      }))
    })

    // Update connection status periodically
    const statusInterval = setInterval(() => {
      setIsConnected(websocketService.isWebSocketConnected())
    }, 5000)

    return () => {
      cleanup()
      clearInterval(statusInterval)
    }
  }, [])

  const requestMetricsUpdate = useCallback(() => {
    websocketService.requestMetricsUpdate()
  }, [])

  const requestServicesUpdate = useCallback(() => {
    websocketService.requestServicesUpdate()
  }, [])

  return {
    isConnected,
    data,
    requestMetricsUpdate,
    requestServicesUpdate
  }
}

export default useWebSocket
