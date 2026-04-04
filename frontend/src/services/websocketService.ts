/**
 * WebSocket Service for Real-Time Updates
 * Connects to Flask-SocketIO backend for live data updates
 *
 * Connections are disabled unless the production build sets
 * VITE_ENABLE_WEBSOCKET=true (and realTimeUpdates is true in config).
 * This avoids console noise when the CDN serves an older bundle or Socket.IO is not ready.
 */

import type { Socket } from 'socket.io-client'
import { config, isFeatureEnabled } from '../config'

function websocketBuildEnabled(): boolean {
  return import.meta.env.VITE_ENABLE_WEBSOCKET === 'true'
}

class WebSocketService {
  private socket: Socket | null = null
  private isConnected = false
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private connectStarted = false

  constructor() {
    if (websocketBuildEnabled() && isFeatureEnabled('realTimeUpdates')) {
      void this.connect()
    }
  }

  private async connect() {
    if (this.connectStarted) {
      return
    }
    if (!websocketBuildEnabled() || !isFeatureEnabled('realTimeUpdates')) {
      return
    }
    this.connectStarted = true

    try {
      const { io } = await import('socket.io-client')
      const wsUrl = config.apiUrl.replace('/api', '')

      this.socket = io(wsUrl, {
        transports: ['websocket', 'polling'],
        timeout: 5000,
        reconnection: true,
        reconnectionAttempts: this.maxReconnectAttempts,
        reconnectionDelay: 1000,
      })

      this.socket.on('connect', () => {
        this.isConnected = true
        this.reconnectAttempts = 0
        this.socket?.emit('subscribe_dashboard')
      })

      this.socket.on('disconnect', () => {
        this.isConnected = false
      })

      this.socket.on('connect_error', () => {
        this.reconnectAttempts++
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          this.socket?.disconnect()
        }
      })

      this.socket.on('metrics_update', (data) => {
        window.dispatchEvent(new CustomEvent('metricsUpdate', { detail: data }))
      })

      this.socket.on('services_update', (data) => {
        window.dispatchEvent(new CustomEvent('servicesUpdate', { detail: data }))
      })

      this.socket.on('activity_update', (data) => {
        window.dispatchEvent(new CustomEvent('activityUpdate', { detail: data }))
      })

      this.socket.on('error', () => {})
    } catch {
      this.connectStarted = false
    }
  }

  public requestMetricsUpdate() {
    if (this.isConnected && this.socket) {
      this.socket.emit('request_metrics_update')
    }
  }

  public requestServicesUpdate() {
    if (this.isConnected && this.socket) {
      this.socket.emit('request_services_update')
    }
  }

  public isWebSocketConnected(): boolean {
    return this.isConnected && this.socket?.connected === true
  }

  public disconnect() {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
      this.isConnected = false
    }
  }

  public subscribeToUpdates(callback: (event: string, data: any) => void) {
    const handleMetricsUpdate = (event: CustomEvent) => callback('metrics', event.detail)
    const handleServicesUpdate = (event: CustomEvent) => callback('services', event.detail)
    const handleActivityUpdate = (event: CustomEvent) => callback('activity', event.detail)

    window.addEventListener('metricsUpdate', handleMetricsUpdate as EventListener)
    window.addEventListener('servicesUpdate', handleServicesUpdate as EventListener)
    window.addEventListener('activityUpdate', handleActivityUpdate as EventListener)

    return () => {
      window.removeEventListener('metricsUpdate', handleMetricsUpdate as EventListener)
      window.removeEventListener('servicesUpdate', handleServicesUpdate as EventListener)
      window.removeEventListener('activityUpdate', handleActivityUpdate as EventListener)
    }
  }
}

export const websocketService = new WebSocketService()
export default websocketService
