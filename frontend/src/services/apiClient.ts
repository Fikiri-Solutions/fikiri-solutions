/**
 * API Client for Fikiri Solutions Backend
 * All HTTP calls use config.apiUrl. Hardcoded backend URLs are forbidden (Rulepack v4.1).
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

export interface GmailConnectionStatus {
  connected: boolean
  status: string
  last_sync?: string
  last_refresh_at?: string  // Backend returns this instead of last_sync
  expires_at?: string
  email?: string
  scopes?: string[]
  is_expired?: boolean
  error?: string
}

export interface OutlookConnectionStatus {
  connected: boolean
  status: string
  expires_at?: string
  scopes?: string[]
  tenant_id?: string
  is_expired?: boolean
  error?: string
}

export interface EmailSyncStatus {
  sync_status: string
  last_sync?: string
  total_emails: number
  syncing: boolean
  progress?: number  // 0-100 percentage
  emails_synced_this_job?: number
  error?: string
}

export interface AutomationRule {
  id: number
  name: string
  description: string
  trigger_type: string
  trigger_conditions: Record<string, any>
  action_type: string
  action_parameters: Record<string, any>
  status: string
}

export interface AutomationSafetyStatus {
  automation_enabled: boolean
  safety_level: string
  restrictions: string[]
  last_updated?: string
}

export interface AutomationLog {
  execution_id: number
  rule_id: number
  rule_name: string
  slug?: string
  status: string
  trigger_data: Record<string, any>
  action_result: Record<string, any>
  executed_at: string
  error_message?: string
}

export interface DocumentProcessingResult {
  document_id: string
  content: {
    text: string
    entities: Record<string, any>
    confidence: number
    metadata: Record<string, any>
  }
}

export interface KnowledgeSearchResult {
  document_id: string
  title: string
  summary: string
  relevance_score: number
  category: string
  content_preview: string
}

class ApiClient {
  private client: AxiosInstance

  constructor() {
    const cacheManager = CacheInvalidationManager.getInstance()
    
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 10000,
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json',
        ...cacheManager.getCacheHeaders() // Add cache invalidation headers
      },
    })

    // Add request interceptor for logging
    this.client.interceptors.request.use(
      (config) => {
        // Add JWT token to requests if available
        if (typeof window !== 'undefined') {
          const userData = localStorage.getItem('fikiri-user')
          if (userData) {
            try {
              const user = JSON.parse(userData)
              // Get token from user data or separate storage
              const token = localStorage.getItem('fikiri-token') || user.token
              if (token) {
                config.headers.Authorization = `Bearer ${token}`
              }
            } catch (e) {
              // Ignore parsing errors
            }
          }
        }
        
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
        // Handle 401 Unauthorized errors
        if (error.response?.status === 401) {
          // Clear any stored auth data
          if (typeof window !== 'undefined') {
            localStorage.removeItem('fikiri-user')
            localStorage.removeItem('fikiri-token')
            localStorage.removeItem('fikiri-user-id')
            
            // Dispatch event for auth context to handle
            window.dispatchEvent(new CustomEvent('auth:unauthorized'))
            
            // Redirect to login if not already there
            // Don't redirect /inbox - it handles its own auth state
            if (window.location.pathname !== '/login' && 
                !window.location.pathname.startsWith('/signup') && 
                window.location.pathname !== '/inbox') {
              window.location.href = '/login?redirect=' + encodeURIComponent(window.location.pathname)
            }
          }
        }
        
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

  // Auth endpoints (used by AuthContext – no Bearer token required for login/signup/logout)
  async login(email: string, password: string): Promise<{ success: boolean; data?: { user?: any; access_token?: string }; error?: string }> {
    const response = await this.client.post('/auth/login', { email, password })
    return response.data
  }

  async signup(signupData: Record<string, any>): Promise<{ success: boolean; data?: { user?: any; tokens?: { access_token?: string } }; error?: string }> {
    const response = await this.client.post('/auth/signup', signupData)
    return response.data
  }

  async logout(): Promise<void> {
    await this.client.post('/auth/logout')
  }

  // Gmail OAuth (accept userId for components that pass it)
  async getGmailStatus(userId: number): Promise<{ success: boolean; data?: GmailConnectionStatus; error?: string }> {
    const response = await this.client.get('/auth/gmail/status', { params: { user_id: userId } })
    return response.data
  }

  async startGmailOAuth(redirectUri: string): Promise<{ url?: string; error?: string }> {
    const response = await this.client.get('/oauth/gmail/start', { params: { redirect: redirectUri } })
    return response.data
  }

  async disconnectGmail(userId: number): Promise<{ success: boolean; error?: string }> {
    const response = await this.client.post('/auth/gmail/disconnect', { user_id: userId })
    return response.data
  }

  // Outlook OAuth
  async getOutlookStatus(userId: number): Promise<{ success: boolean; data?: OutlookConnectionStatus; error?: string }> {
    const response = await this.client.get('/auth/outlook/status', { params: { user_id: userId } })
    return response.data
  }

  async startOutlookOAuth(redirectUri: string): Promise<{ url?: string; error?: string }> {
    const response = await this.client.get('/oauth/outlook/start', { params: { redirect: redirectUri } })
    return response.data
  }

  async disconnectOutlook(userId: number): Promise<{ success: boolean; error?: string }> {
    const response = await this.client.post('/auth/outlook/disconnect', { user_id: userId })
    return response.data
  }

  // Dashboard data endpoints
  async getMetrics(): Promise<MetricData> {
    try {
      // Use dashboard/metrics endpoint (getMetrics is legacy, use getDashboardMetrics instead)
      const response = await this.client.get('/dashboard/metrics')
      return response.data
    } catch (error) {
      console.error('Failed to fetch metrics:', error)
      // Fallback to mock data if API fails
      return {
        totalEmails: Math.floor(Math.random() * 1000) + 100,
        activeLeads: Math.floor(Math.random() * 50) + 10,
        aiResponses: Math.floor(Math.random() * 100) + 50,
        avgResponseTime: Math.random() * 5 + 1
      }
    }
  }

  async getServices(): Promise<ServiceData[]> {
    try {
      // Try to get services from the new API endpoint
      const response = await this.client.get('/services')
      // API returns { success: true, data: [...], message: "..." }
      const servicesData = response.data?.data || response.data
      if (servicesData && Array.isArray(servicesData) && servicesData.length > 0) {
        return servicesData.map((s: any) => ({
          id: s.service_id,
          name: s.service_name,
          status: s.status || (s.enabled ? 'active' : 'inactive'),
          description: this.getServiceDescription(s.service_id)
        }))
      }
    } catch (error) {
      console.warn('Failed to fetch services from API, falling back to health status:', error)
    }
    
    // Fallback to health status if API fails
    try {
      const health = await this.getHealth()
      if (health?.services && typeof health.services === 'object') {
        return Object.entries(health.services).map(([id, status]: [string, any]) => ({
          id,
          name: this.formatServiceName(id),
          status: status?.status === 'healthy' ? 'active' : 'inactive',
          description: this.getServiceDescription(id)
        }))
      }
    } catch (healthError) {
      console.warn('Failed to get health status:', healthError)
    }
    
    // Final fallback: return empty array
    return []
  }

  async saveService(serviceId: string, serviceName: string, enabled: boolean, settings: any = {}): Promise<any> {
    const response = await this.client.post('/services', {
      service_id: serviceId,
      service_name: serviceName,
      enabled: enabled,
      settings: settings
    })
    // API returns { success: true, data: {...}, message: "..." }
    return response.data?.data || response.data
  }

  async updateService(serviceId: string, updates: { enabled?: boolean; settings?: any }): Promise<any> {
    const response = await this.client.put(`/services/${serviceId}`, updates)
    // API returns { success: true, data: {...}, message: "..." }
    return response.data?.data || response.data
  }

  async deleteService(serviceId: string): Promise<any> {
    const response = await this.client.delete(`/services/${serviceId}`)
    // API returns { success: true, data: {...}, message: "..." }
    return response.data?.data || response.data
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
      user_id: this.getUserId() ?? 1, // Use actual user ID or fallback to 1
      context: context || {}
    })
    // Handle both response formats: { success, data: { response, ... } } or direct { response, ... }
    if (response.data?.data?.response) {
      return response.data.data
    }
    return response.data
  }

  // Dashboard endpoints
  async getDashboardTimeseries(userId: number = 1, period: 'week' | 'month' | 'quarter' = 'week'): Promise<any> {
    const response = await this.client.get('/dashboard/timeseries', {
      params: { user_id: userId, period }
    })
    return response.data
  }

  async getDashboardMetrics(userId: number = 1): Promise<any> {
    const response = await this.client.get('/dashboard/metrics', {
      params: { user_id: userId }
    })
    return response.data
  }

  // Enhanced dashboard endpoints

  async getDashboardLeads(filters?: {
    dateRange?: { start: string; end: string };
    status?: string;
    source?: string;
  }): Promise<any> {
    const response = await this.client.get('/dashboard/leads', {
      params: filters
    })
    return response.data
  }

  async getEmailMetrics(period: 'day' | 'week' | 'month' = 'week'): Promise<any> {
    const response = await this.client.get('/dashboard/emails', {
      params: { period }
    })
    return response.data
  }

  async getAIMetrics(): Promise<any> {
    const response = await this.client.get('/dashboard/ai')
    return response.data
  }

  async getRevenueAnalytics(period: 'week' | 'month' | 'quarter' = 'month'): Promise<any> {
    const response = await this.client.get('/dashboard/revenue', {
      params: { period }
    })
    return response.data
  }

  async updateDashboardPreferences(preferences: {
    defaultView?: string;
    refreshInterval?: number;
    notifications?: boolean;
  }): Promise<any> {
    const response = await this.client.post('/dashboard/preferences', preferences)
    return response.data
  }

  async testAIAssistant(): Promise<AIResponse> {
    const response = await this.client.post('/test/ai-assistant', {
      content: 'Hi, I need help with your services.',
      sender: 'Test User',
      subject: 'Test Subject'
    })
    // Handle both response formats: direct AIResponse or wrapped in { success, data, message }
    if (response.data.data) {
      return response.data.data
    }
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
    const response = await this.client.get('/crm/leads', {
      params: { user_id: this.getUserId() ?? 1 }
    })
    const backendLeads = response.data.leads || []
    
    // Map backend data to frontend interface
    return backendLeads.map((lead: any) => this.mapLead(lead))
  }

  async getPipeline(): Promise<Record<string, LeadData[]>> {
    const response = await this.client.get('/crm/pipeline', {
      params: { user_id: this.getUserId() ?? 1 }
    })

    const pipeline = response.data.pipeline || {}
    const mapped: Record<string, LeadData[]> = {}

    Object.keys(pipeline).forEach(stage => {
      mapped[stage] = (pipeline[stage] || []).map((lead: any) => this.mapLead(lead))
    })

    return mapped
  }

  async updateLeadStage(leadId: string | number, stage: string): Promise<void> {
    await this.client.put(`/crm/leads/${leadId}`, { stage })
  }

  async getOnboardingStatus(userId?: number | string): Promise<any> {
    const response = await this.client.get('/onboarding/status', {
      params: userId != null ? { user_id: userId } : undefined
    })
    return response.data?.data || response.data
  }

  /** Generic request for any endpoint. Prefer named methods when available. */
  async request<T = any>(
    method: 'GET' | 'POST' | 'PUT' | 'DELETE',
    path: string,
    options?: { params?: Record<string, any>; data?: any }
  ): Promise<T> {
    const res = await this.client.request<T>({
      method,
      url: path,
      params: options?.params,
      data: options?.data
    })
    return res.data
  }

  async updateOnboardingStep(step: number): Promise<any> {
    const response = await this.client.put('/user/onboarding-step', { step })
    return response.data
  }

  async saveOnboarding(payload: { name: string; company: string; industry?: string }): Promise<any> {
    const response = await this.client.post('/onboarding', payload)
    return response.data
  }

  async getAutomationRules(): Promise<AutomationRule[]> {
    const userId = this.getUserId() ?? 1
    const response = await this.client.get('/automation/rules', {
      params: { user_id: userId }
    })
    return response.data?.data?.rules || response.data?.rules || []
  }

  async createAutomationRule(rule: {
    name: string
    description: string
    trigger_type: string
    trigger_conditions: Record<string, any>
    action_type: string
    action_parameters: Record<string, any>
  }): Promise<any> {
    const response = await this.client.post('/automation/rules', rule)
    return response.data
  }

  async updateAutomationRule(ruleId: number | string, updates: Partial<AutomationRule>): Promise<any> {
    const response = await this.client.put(`/automation/rules/${ruleId}`, updates)
    return response.data
  }

  async getAutomationSafetyStatus(): Promise<AutomationSafetyStatus> {
    const userId = this.getUserId() ?? 1
    const response = await this.client.get('/automation/safety-status', {
      params: { user_id: userId }
    })
    // Handle both response formats: { success, data, ... } or direct data
    const safetyData = response.data?.data || response.data
    return safetyData || {
      automation_enabled: true,
      safety_level: 'normal',
      restrictions: []
    }
  }

  async getAutomationSuggestions(): Promise<any[]> {
    const userId = this.getUserId() ?? 1
    const response = await this.client.get('/automation/suggestions', {
      params: { user_id: userId }
    })
    return response.data?.data?.suggestions || response.data?.suggestions || []
  }

  async getAutomationLogs(params?: { ruleId?: number; slug?: string; limit?: number }): Promise<AutomationLog[]> {
    const userId = this.getUserId() ?? 1
    const response = await this.client.get('/automation/logs', {
      params: {
        user_id: userId,
        rule_id: params?.ruleId,
        slug: params?.slug,
        limit: params?.limit
      }
    })
    return response.data?.data?.logs || response.data?.logs || []
  }

  async runAutomationPreset(presetId: string): Promise<any> {
    const response = await this.client.post('/automation/test', {
      preset_id: presetId
    })
    return response.data
  }

  async getGmailConnectionStatus(): Promise<GmailConnectionStatus> {
    const userId = this.getUserId()
    const response = await this.client.get('/auth/gmail/status', {
      params: { user_id: userId ?? 1 }
    })
    // Handle both response formats: { success, data, ... } or direct data
    const statusData = response.data?.data || response.data
    // Map last_refresh_at to last_sync for backward compatibility
    if (statusData?.last_refresh_at && !statusData?.last_sync) {
      statusData.last_sync = statusData.last_refresh_at
    }
    return statusData
  }

  async triggerGmailSync(): Promise<{ message: string }> {
    const response = await this.client.post('/crm/sync-gmail', {
      user_id: this.getUserId() ?? 1
    })
    return response.data
  }

  async getOutlookConnectionStatus(): Promise<OutlookConnectionStatus> {
    const userId = this.getUserId()
    const response = await this.client.get('/auth/outlook/status', {
      params: { user_id: userId ?? 1 }
    })
    return response.data?.data || response.data
  }

  async triggerOutlookSync(): Promise<{ message: string }> {
    const response = await this.client.post('/crm/sync-outlook', {
      user_id: this.getUserId() ?? 1
    })
    return response.data
  }

  async getEmailSyncStatus(): Promise<EmailSyncStatus> {
    const response = await this.client.get('/email/sync/status', {
      params: { user_id: this.getUserId() ?? 1 }
    })
    // Handle both response formats: { success, data, ... } or direct data
    const status = response.data?.data || response.data
    return status
  }

  async getEmails(params?: { filter?: string; limit?: number; query?: string; use_synced?: boolean }): Promise<any> {
    const response = await this.client.get('/email/messages', {
      params: {
        user_id: this.getUserId() ?? 1,
        use_synced: params?.use_synced ?? true, // Default to using synced emails for speed
        ...params
      }
    })
    return response.data.data || response.data
  }

  async analyzeEmail(emailId: string, subject: string, content: string, from: string): Promise<any> {
    const response = await this.client.post('/ai/analyze-email', {
      email_id: emailId,
      subject,
      content,
      from
    })
    return response.data.data || response.data
  }

  async generateReply(emailId: string, subject: string, content: string, from: string): Promise<any> {
    const response = await this.client.post('/ai/generate-reply', {
      email_id: emailId,
      subject,
      content,
      from
    })
    return response.data.data || response.data
  }

  async processDocument(file: File): Promise<DocumentProcessingResult> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('user_id', (this.getUserId() ?? 1).toString())

    const response = await this.client.post('/docs-forms/documents/process', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  }

  async addFaq(payload: {
    question: string
    answer: string
    category?: string
    keywords?: string[]
    variations?: string[]
  }): Promise<any> {
    const response = await this.client.post('/chatbot/faq', payload)
    return response.data
  }

  async addKnowledgeDocument(payload: {
    title: string
    content: string
    summary?: string
    category?: string
    tags?: string[]
    keywords?: string[]
  }): Promise<any> {
    const response = await this.client.post('/chatbot/knowledge/documents', payload)
    return response.data
  }

  async vectorizeKnowledge(payload: { content: string; metadata?: Record<string, any> }): Promise<any> {
    const response = await this.client.post('/chatbot/knowledge/vectorize', payload)
    return response.data
  }

  async searchKnowledge(query: string): Promise<KnowledgeSearchResult[]> {
    const response = await this.client.post('/chatbot/knowledge/search', { query })
    return response.data?.results || []
  }

  async getFaqStats(): Promise<any> {
    const response = await this.client.get('/chatbot/faq/statistics')
    return response.data?.statistics || {}
  }

  async getFaqCategories(): Promise<string[]> {
    const response = await this.client.get('/chatbot/faq/categories')
    return response.data?.categories || []
  }

  async getKnowledgeCategories(): Promise<string[]> {
    const response = await this.client.get('/chatbot/knowledge/categories')
    return response.data?.categories || []
  }

  async sendEmail(data: { to: string; subject: string; body: string }): Promise<{ message_id: string; thread_id?: string }> {
    const response = await this.client.post('/email/send', data)
    return response.data.data
  }

  async archiveEmail(emailId: string): Promise<{ archived: boolean }> {
    const response = await this.client.post('/email/archive', {
      email_id: emailId,
      user_id: this.getUserId() ?? 1
    })
    return response.data.data || response.data
  }

  async getEmailAttachments(emailId: string): Promise<any[]> {
    const response = await this.client.get(`/email/${emailId}/attachments`)
    // API returns { success: true, data: [...], message: "..." }
    return response.data?.data || response.data || []
  }

  async downloadEmailAttachment(emailId: string, attachmentId: string): Promise<Blob> {
    const response = await this.client.get(`/email/${emailId}/attachments/${attachmentId}/download`, {
      responseType: 'blob'
    })
    return response.data
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

  private mapLead(lead: any): LeadData {
    return {
      id: (lead.id ?? lead.lead_id ?? '').toString(),
      name: lead.name || 'Unknown',
      email: lead.email || '',
      company: lead.company || '',
      stage: lead.stage || 'new',
      score: lead.score || 0,
      lastContact: lead.last_contact || lead.updated_at || lead.created_at || new Date().toISOString(),
      source: lead.source || 'manual'
    }
  }

  private getUserId(): number | null {
    if (typeof window === 'undefined') return null
    const stored = localStorage.getItem('fikiri-user-id')
    return stored ? Number(stored) : null
  }

  // Billing & Subscription methods
  async getPricingTiers(): Promise<any> {
    const response = await this.client.get('/billing/pricing')
    return response.data?.pricing_tiers || {}
  }

  async createCheckoutSession(tierName: string, billingPeriod: 'monthly' | 'annual' = 'monthly', useTrial: boolean = true): Promise<{ checkout_url: string; session_id: string }> {
    const response = await this.client.post('/billing/checkout', {
      tier_name: tierName,
      billing_period: billingPeriod,
      trial: useTrial
    })
    if (!response.data.success) {
      throw new Error(response.data.error || 'Failed to create checkout session')
    }
    return {
      checkout_url: response.data.checkout_url,
      session_id: response.data.session_id
    }
  }

  async getCurrentSubscription(): Promise<any> {
    const response = await this.client.get('/billing/subscription/current')
    return response.data
  }

  async cancelSubscription(subscriptionId: string, atPeriodEnd: boolean = true): Promise<any> {
    const response = await this.client.post(`/billing/subscription/${subscriptionId}/cancel`, {
      at_period_end: atPeriodEnd
    })
    if (!response.data.success) {
      throw new Error(response.data.error || 'Failed to cancel subscription')
    }
    return response.data
  }

  async getInvoices(): Promise<any[]> {
    const response = await this.client.get('/billing/invoices')
    return response.data?.invoices || []
  }

  async createPortalSession(): Promise<{ url: string }> {
    const response = await this.client.post('/billing/portal')
    if (!response.data.success) {
      throw new Error(response.data.error || 'Failed to create portal session')
    }
    return { url: response.data.url }
  }

  async getPaymentMethods(): Promise<any[]> {
    const response = await this.client.get('/billing/payment-methods')
    return response.data?.payment_methods || []
  }

  async removePaymentMethod(paymentMethodId: string): Promise<any> {
    const response = await this.client.delete(`/billing/payment-methods/${paymentMethodId}`)
    if (!response.data.success) {
      throw new Error(response.data.error || 'Failed to remove payment method')
    }
    return response.data
  }

  async setDefaultPaymentMethod(paymentMethodId: string): Promise<any> {
    const response = await this.client.post(`/billing/payment-methods/${paymentMethodId}/default`)
    if (!response.data.success) {
      throw new Error(response.data.error || 'Failed to set default payment method')
    }
    return response.data
  }

  async getCustomerDetails(): Promise<any> {
    const response = await this.client.get('/billing/customer/details')
    return response.data?.customer || null
  }

  async createSetupIntent(paymentMethodTypes: string[] = ['card', 'us_bank_account']): Promise<{ client_secret: string; setup_intent_id: string }> {
    const response = await this.client.post('/billing/setup-intent', {
      payment_method_types: paymentMethodTypes
    })
    if (!response.data.success) {
      throw new Error(response.data.error || 'Failed to create setup intent')
    }
    return {
      client_secret: response.data.client_secret,
      setup_intent_id: response.data.setup_intent_id
    }
  }

  handleError(error: any): string {
    // Use friendly error messages
    const { getFriendlyError } = require('../utils/errorMessages')
    const friendly = getFriendlyError(error)
    return friendly.message
  }
}

// Export singleton instance
export const apiClient = new ApiClient()
