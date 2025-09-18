/**
 * API Client for Fikiri Solutions Backend
 * Connects React frontend to Flask backend at https://fikirisolutions.onrender.com
 */

import axios, { AxiosInstance, AxiosResponse } from 'axios'
import { config } from '../config'
import { CacheInvalidationManager } from '../utils/cacheInvalidation'

// API Configuration
const API_BASE_URL = config.apiUrl

// Types for API responses
export interface ServiceStatus {
  status: 'healthy' | 'unhealthy' | 'error'
  available: boolean
  initialized: boolean
  authenticated?: boolean
  enabled?: boolean
  error?: string
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy'
  timestamp: string
  version: string
  services: Record<string, ServiceStatus>
}

export interface MetricData {
  totalEmails: number
  activeLeads: number
  aiResponses: number
  avgResponseTime: number
}

export interface ServiceData {
  id: string
  name: string
  status: 'active' | 'inactive' | 'error' | string
  description: string
}

export interface ActivityItem {
  id: number
  type: string
  message: string
  timestamp: string
  status: 'success' | 'warning' | 'error' | string
}

export interface LeadData {
  id: string
  name: string
  email: string
  company: string
  stage: string
  score: number
  lastContact: string
  source: string
}

export interface AIResponse {
  classification: {
    confidence: number
    intent: string
    suggested_action: string
    urgency: string
  }
  contact_info: Record<string, any>
  response: string
  stats: {
    api_key_configured: boolean
    client_initialized: boolean
    enabled: boolean
  }
  success: boolean
}

class ApiClient {
  private client: AxiosInstance

  constructor() {
    const cacheManager = CacheInvalidationManager.getInstance()
    
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
        ...cacheManager.getCacheHeaders() // Add cache invalidation headers
      },
    })

    // Add request interceptor for logging
    this.client.interceptors.request.use(
      (config) => {
        // API request logged
        return config
      },
      (error) => {
        // API request error logged
        return Promise.reject(error)
      }
    )

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => {
        // API response logged
        return response
      },
      (error) => {
        // API response error logged
        return Promise.reject(error)
      }
    )
  }

  // Health and Status endpoints
  async getHealth(): Promise<HealthResponse> {
    const response: AxiosResponse<HealthResponse> = await this.client.get('/health')
    return response.data
  }

  async getStatus(): Promise<HealthResponse> {
    // Status endpoint redirects to health, so we use health directly
    return this.getHealth()
  }

  // Dashboard data endpoints
  async getMetrics(): Promise<MetricData> {
    // For now, we'll derive metrics from health status
    // In the future, this could be a dedicated metrics endpoint
    const health = await this.getHealth()
    
    // Calculate metrics based on service status
    const totalServices = Object.keys(health.services).length
    const healthyServices = Object.values(health.services).filter(s => s.status === 'healthy').length
    
    return {
      totalEmails: Math.floor(Math.random() * 1000) + 100, // Mock for now
      activeLeads: Math.floor(Math.random() * 50) + 10,   // Mock for now
      aiResponses: Math.floor(Math.random() * 100) + 50,  // Mock for now
      avgResponseTime: Math.random() * 5 + 1              // Mock for now
    }
  }

  async getServices(): Promise<ServiceData[]> {
    const health = await this.getHealth()
    
    return Object.entries(health.services).map(([id, status]) => ({
      id,
      name: this.formatServiceName(id),
      status: status.status === 'healthy' ? 'active' : 'inactive',
      description: this.getServiceDescription(id)
    }))
  }

  async getActivity(): Promise<ActivityItem[]> {
    // For now, return mock activity data
    // In the future, this could be a dedicated activity endpoint
    return [
      {
        id: 1,
        type: 'ai_response',
        message: 'AI Assistant responded to inquiry from john@acme.com',
        timestamp: '2 minutes ago',
        status: 'success'
      },
      {
        id: 2,
        type: 'lead_added',
        message: 'New lead added: Jane Smith from Startup Inc',
        timestamp: '15 minutes ago',
        status: 'success'
      },
      {
        id: 3,
        type: 'email_processed',
        message: 'Email automation triggered for urgent inquiry',
        timestamp: '1 hour ago',
        status: 'success'
      },
      {
        id: 4,
        type: 'service_error',
        message: 'ML Scoring service temporarily unavailable',
        timestamp: '2 hours ago',
        status: 'warning'
      }
    ]
  }

  // Service test endpoints
  async testEmailParser(): Promise<any> {
    const response = await this.client.post('/test/email-parser', {})
    return response.data
  }

  async testEmailActions(): Promise<any> {
    const response = await this.client.post('/test/email-actions', {})
    return response.data
  }

  async testCRM(): Promise<any> {
    const response = await this.client.post('/test/crm', {})
    return response.data
  }

  async sendChatMessage(message: string, context?: any): Promise<any> {
    const response = await this.client.post('/ai/chat', {
      message,
      context: context || {}
    })
    return response.data
  }

  async testAIAssistant(): Promise<AIResponse> {
    const response = await this.client.post('/test/ai-assistant', {
      content: 'Hi, I need help with your services.',
      sender: 'Test User',
      subject: 'Test Subject'
    })
    return response.data
  }

  async testMLScoring(): Promise<any> {
    const response = await this.client.post('/test/ml-scoring', {})
    return response.data
  }

  async testVectorSearch(): Promise<any> {
    const response = await this.client.post('/test/vector-search', {})
    return response.data
  }

  // CRM endpoints
  async getLeads(): Promise<LeadData[]> {
    const response = await this.client.get('/crm/leads')
    return response.data.leads || []
  }

  // Utility methods
  private formatServiceName(id: string): string {
    const nameMap: Record<string, string> = {
      'config': 'Configuration',
      'auth': 'Authentication',
      'parser': 'Email Parser',
      'gmail': 'Gmail Service',
      'actions': 'Email Actions',
      'crm': 'CRM Service',
      'ai_assistant': 'AI Assistant',
      'ml_scoring': 'ML Lead Scoring',
      'vector_search': 'Vector Search',
      'feature_flags': 'Feature Flags'
    }
    return nameMap[id] || id.charAt(0).toUpperCase() + id.slice(1)
  }

  private getServiceDescription(id: string): string {
    const descMap: Record<string, string> = {
      'config': 'System configuration and settings',
      'auth': 'User authentication and authorization',
      'parser': 'Intelligent email content analysis',
      'gmail': 'Gmail API integration and email management',
      'actions': 'Automated email actions and responses',
      'crm': 'Customer relationship management',
      'ai_assistant': 'AI-powered email responses and classification',
      'ml_scoring': 'Machine learning lead scoring and prioritization',
      'vector_search': 'Semantic search and document retrieval',
      'feature_flags': 'Feature flag management and control'
    }
    return descMap[id] || 'Service description not available'
  }

  // Error handling
  async addLead(leadData: LeadData): Promise<LeadData> {
    const response = await this.client.post('/crm/leads', leadData)
    return response.data
  }

  handleError(error: any): string {
    if (error.response) {
      // Server responded with error status
      return `Server error: ${error.response.status} - ${error.response.data?.error || error.message}`
    } else if (error.request) {
      // Request was made but no response received
      return 'Network error: Unable to connect to server'
    } else {
      // Something else happened
      return `Error: ${error.message}`
    }
  }
}

// Export singleton instance
export const apiClient = new ApiClient()
