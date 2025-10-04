/**
 * WebSocket Service for Real-Time Updates
 * Connects to Flask-SocketIO backend for live data updates
 */

import { io, Socket } from 'socket.io-client'
import { config } from '../config'

class WebSocketService {
  private socket: Socket | null = null
  private isConnected = false
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5

  constructor() {
    // Disabled for now - backend doesn't support WebSocket yet
    // this.connect()
  }

  private connect() {
    try {
      // Use the same base URL as the API client
      const wsUrl = config.apiUrl.replace('/api', '')
      
      this.socket = io(wsUrl, {
        transports: ['polling'], // Use polling only until WebSocket support is added to backend
        timeout: 20000,
        reconnection: true,
        reconnectionAttempts: this.maxReconnectAttempts,
        reconnectionDelay: 1000,
      })

      this.socket.on('connect', () => {
        // WebSocket connected
        this.isConnected = true
        this.reconnectAttempts = 0
        
        // Subscribe to dashboard updates
        this.socket?.emit('subscribe_dashboard')
      })

      this.socket.on('disconnect', () => {
        // WebSocket disconnected
        this.isConnected = false
      })

      this.socket.on('connect_error', (error) => {
        // WebSocket connection error
        this.reconnectAttempts++
        
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          // Max reconnection attempts reached, falling back to polling
        }
      })

      // Dashboard update handlers
      this.socket.on('metrics_update', (data) => {
        // Metrics updated
        // Emit custom event for React components to listen to
        window.dispatchEvent(new CustomEvent('metricsUpdate', { detail: data }))
      })

      this.socket.on('services_update', (data) => {
        // Services updated
        window.dispatchEvent(new CustomEvent('servicesUpdate', { detail: data }))
      })

      this.socket.on('activity_update', (data) => {
        // Activity updated
        window.dispatchEvent(new CustomEvent('activityUpdate', { detail: data }))
      })

      this.socket.on('error', (error) => {
        // WebSocket error
      })

    } catch (error) {
      // Failed to initialize WebSocket
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

  // React hook for subscribing to updates
  public subscribeToUpdates(callback: (event: string, data: any) => void) {
    const handleMetricsUpdate = (event: CustomEvent) => callback('metrics', event.detail)
    const handleServicesUpdate = (event: CustomEvent) => callback('services', event.detail)
    const handleActivityUpdate = (event: CustomEvent) => callback('activity', event.detail)

    window.addEventListener('metricsUpdate', handleMetricsUpdate as EventListener)
    window.addEventListener('servicesUpdate', handleServicesUpdate as EventListener)
    window.addEventListener('activityUpdate', handleActivityUpdate as EventListener)

    // Return cleanup function
    return () => {
      window.removeEventListener('metricsUpdate', handleMetricsUpdate as EventListener)
      window.removeEventListener('servicesUpdate', handleServicesUpdate as EventListener)
      window.removeEventListener('activityUpdate', handleActivityUpdate as EventListener)
    }
  }
}

// Export singleton instance
export const websocketService = new WebSocketService()
export default websocketService
