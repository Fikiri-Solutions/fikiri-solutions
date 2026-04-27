/**
 * API Client for Fikiri Solutions Backend
 * All HTTP calls use config.apiUrl. Hardcoded backend URLs are forbidden (Rulepack v4.1).
 */

import axios, { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { config } from '../config'
import { CacheInvalidationManager } from '../utils/cacheInvalidation'

// API Configuration
const API_BASE_URL = config.apiUrl

/** Single-flight refresh so concurrent 401s share one POST /auth/refresh. */
let refreshInFlight: Promise<string | null> | null = null

function persistTokensFromRefreshPayload(data: unknown): string | null {
  const body = data as { data?: { tokens?: { access_token?: string; refresh_token?: string } } }
  const tokens = body?.data?.tokens
  if (tokens?.access_token && typeof window !== 'undefined') {
    localStorage.setItem('fikiri-token', tokens.access_token)
    if (tokens.refresh_token) {
      localStorage.setItem('fikiri-refresh-token', tokens.refresh_token)
    }
    return tokens.access_token
  }
  return null
}

async function refreshSessionAccessToken(): Promise<string | null> {
  if (typeof window === 'undefined') return null
  const rt = localStorage.getItem('fikiri-refresh-token')
  if (!rt) return null
  try {
    const res = await axios.post(
      `${API_BASE_URL}/auth/refresh`,
      { refresh_token: rt },
      {
        headers: { 'Content-Type': 'application/json' },
        withCredentials: true,
        timeout: 20000,
      }
    )
    return persistTokensFromRefreshPayload(res.data)
  } catch {
    return null
  }
}

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

export interface IndustryPromptConfig {
  industry: string
  tone: string
  focus_areas: string[]
  tools: string[]
  pricing_tier: string
}

export interface IndustryUsageMetrics {
  tier: string
  responses: number
  tool_calls: number
  tokens: number
  monthly_cost: number
}

export interface ServiceData {
  id: string
  name: string
  status: 'active' | 'inactive' | 'error' | string
  description: string
  settings?: Record<string, any>
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
  /** 0–100 from backend `LeadScoringService`. */
  score: number
  scoreBreakdown?: Record<string, number | string>
  scoringVersion?: string
  lastContact: string
  source: string
}

/** Row from GET /crm/leads/:id/events (append-only CRM timeline). */
export interface LeadCrmEvent {
  id: number
  created_at: string
  event_type: string
  entity_type: string
  entity_id: number
  correlation_id?: string | null
  status?: string | null
  source?: string | null
  [key: string]: unknown
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

/** GET /api/migration/capabilities — structured import & migration map */
export interface ContentMigrationCapabilities {
  feature: string
  version: number
  sections: {
    knowledge_marketing: {
      title: string
      description: string
      modes: Array<{ id: string; label: string; notes: string }>
      api: Array<{ method: string; path: string; auth: string; notes?: string; role?: string }>
      related_ui_path: string
    }
    documents: {
      title: string
      description: string
      supported_file_extensions: string[]
      file_categories: Record<string, string[]>
      api: Array<{ method: string; path: string; auth: string; notes?: string; role?: string }>
      document_templates: Array<{
        id: string
        name: string
        document_type: string
        industry: string
        variable_count: number
      }>
      related_ui_path: string
    }
    forms: {
      title: string
      description: string
      api: Array<{ method: string; path: string; auth: string; notes?: string }>
      form_templates: Array<{
        id: string
        name: string
        industry: string
        purpose: string
        field_count: number
      }>
    }
    contacts: {
      title: string
      description: string
      csv_requirements: {
        required_columns: string[]
        optional_columns: string[]
        max_file_mb: number
        max_rows: number
      }
      on_duplicate_policies: string[]
      api: Array<{ method: string; path: string; auth: string; notes?: string }>
      related_ui_path: string
    }
  }
}

export interface DocsFormsDocumentTemplateSummary {
  id: string
  name: string
  description: string
  document_type: string
  industry: string
  format: string
  variable_count: number
  created_at: string
}

export interface DocsFormsFormTemplateSummary {
  id: string
  name: string
  description: string
  industry: string
  purpose: string
  field_count: number
  created_at: string
}

export interface ApiKeySummary {
  id: number
  key_prefix: string
  name: string
  description?: string
  tenant_id?: string
  scopes?: string[]
  rate_limit_per_minute?: number
  rate_limit_per_hour?: number
  is_active?: boolean
  expires_at?: string
  last_used_at?: string
  created_at?: string
}

export interface ApiKeyCreateResponse {
  api_key: string
  key_info: {
    key_prefix: string
    name: string
    scopes: string[]
    tenant_id?: string
    rate_limit_per_minute?: number
    rate_limit_per_hour?: number
    expires_at?: string | null
  }
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
          const token = localStorage.getItem('fikiri-token')
          
          if (userData) {
            try {
              const user = JSON.parse(userData)
              // Get token from separate storage or user data
              const authToken = token || user.token || user.access_token
              if (authToken) {
                config.headers.Authorization = `Bearer ${authToken}`
                if (process.env.NODE_ENV === 'development') {
                  console.log(`[apiClient] Added auth token to ${config.method?.toUpperCase()} ${config.url}`)
                }
              } else {
                if (process.env.NODE_ENV === 'development') {
                  console.warn(`[apiClient] No auth token found for ${config.method?.toUpperCase()} ${config.url}`)
                }
              }
            } catch (e) {
              console.error('[apiClient] Error parsing user data:', e)
            }
          } else {
            if (process.env.NODE_ENV === 'development' && config.url && !config.url.includes('/auth/')) {
              console.warn(`[apiClient] No user data in localStorage for ${config.method?.toUpperCase()} ${config.url}`)
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
        // Log login responses in development
        if (process.env.NODE_ENV === 'development' && response.config.url?.includes('/auth/login')) {
          console.log('[apiClient] Login response received:', {
            status: response.status,
            data: response.data,
            hasSuccess: response.data?.success,
            hasData: !!response.data?.data,
            hasUser: !!response.data?.data?.user,
            hasToken: !!response.data?.data?.access_token
          })
        }
        // API response logged
        return response
      },
      async (error) => {
        // Handle 401: try refresh-token rotation once, then optional logout redirect
        if (error.response?.status === 401 && error.config) {
          const cfg = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
          const reqUrl = String(cfg.url || '')
          const isAuthCall =
            reqUrl.includes('/auth/refresh') ||
            reqUrl.includes('/auth/login') ||
            reqUrl.includes('/auth/signup')
          if (!isAuthCall && !cfg._retry && typeof window !== 'undefined') {
            const hasRefresh = !!localStorage.getItem('fikiri-refresh-token')
            if (hasRefresh) {
              if (!refreshInFlight) {
                refreshInFlight = refreshSessionAccessToken().finally(() => {
                  refreshInFlight = null
                })
              }
              const newAccess = await refreshInFlight
              if (newAccess) {
                cfg._retry = true
                cfg.headers = cfg.headers ?? {}
                cfg.headers.Authorization = `Bearer ${newAccess}`
                return this.client.request(cfg)
              }
            }
          }

          const method = String(cfg.method || 'get').toLowerCase()
          // Optional asset when logged out — do not redirect
          if (method === 'get' && reqUrl.includes('/user/customization/logo')) {
            return Promise.reject(error)
          }

          const isLoginRequest = reqUrl.includes('/auth/login')
          const isOnLoginPage = window.location.pathname === '/login'

          if (!isLoginRequest && !isOnLoginPage) {
            if (typeof window !== 'undefined') {
              console.log('[apiClient] 401 error - clearing localStorage and redirecting to login')
              localStorage.removeItem('fikiri-user')
              localStorage.removeItem('fikiri-token')
              localStorage.removeItem('fikiri-refresh-token')
              localStorage.removeItem('fikiri-user-id')

              window.dispatchEvent(new CustomEvent('auth:unauthorized'))

              if (
                window.location.pathname !== '/login' &&
                !window.location.pathname.startsWith('/signup') &&
                window.location.pathname !== '/inbox'
              ) {
                window.location.href =
                  '/login?redirect=' + encodeURIComponent(window.location.pathname)
              }
            }
          } else if (import.meta.env.DEV) {
            console.log('[apiClient] 401 error on login endpoint or login page - NOT clearing localStorage')
          }
        }

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

  async verifyEmail(token: string): Promise<any> {
    const response = await this.client.get('/auth/verify-email', {
      params: { token }
    })
    return response.data
  }

  async whoami(): Promise<any> {
    const response = await this.client.get('/auth/whoami')
    return response.data
  }

  async resendEmailVerification(): Promise<any> {
    const response = await this.client.post('/auth/resend-email-verification')
    return response.data
  }

  async logout(): Promise<void> {
    await this.client.post('/auth/logout')
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<{ message?: string; error?: string }> {
    const response = await this.client.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword
    })
    const data = response.data?.data ?? response.data
    return data
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
      const userId = this.getUserId()
      const response = await this.client.get('/dashboard/metrics', {
        params: userId ? { user_id: userId } : undefined
      })
      const raw = response.data?.data || response.data || {}
      // Map backend shape to frontend MetricData (leads.total, email.total_emails, etc.)
      const activeLeads = raw.leads?.total ?? 0
      const totalEmails = raw.email?.total_emails ?? raw.emails?.total ?? 0
      let avgResponseTime = 0
      const rt = raw.performance?.response_time
      if (typeof rt === 'number') avgResponseTime = rt
      else if (typeof rt === 'string') {
        const parsed = parseFloat(rt.replace(/[^\d.]/g, ''))
        if (!Number.isNaN(parsed)) avgResponseTime = parsed
      }
      return {
        activeLeads,
        totalEmails,
        aiResponses: raw.ai?.total ?? raw.aiResponses ?? 0,
        avgResponseTime,
        // Keep raw for any component that reads nested shape
        ...raw,
        leads: raw.leads ?? { total: activeLeads },
        email: raw.email ?? { total_emails: totalEmails }
      } as MetricData
    } catch (error: any) {
      console.error('[apiClient] Failed to fetch metrics:', error)
      return {
        totalEmails: 0,
        activeLeads: 0,
        aiResponses: 0,
        avgResponseTime: 0
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
          description: this.getServiceDescription(s.service_id),
          // Preserve saved settings so the UI can't clobber them silently.
          settings: (() => {
            const raw = s.settings
            if (raw && typeof raw === 'object' && !Array.isArray(raw)) return raw
            if (typeof raw === 'string') {
              try {
                const parsed = JSON.parse(raw)
                if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) return parsed
              } catch {
                // ignore parse errors; fall back to empty object
              }
            }
            return {}
          })(),
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
          description: this.getServiceDescription(id),
          settings: {},
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
    try {
      const response = await this.client.get('/dashboard/activity')
      const data = response.data?.data || response.data
      const activities = data?.activities ?? (Array.isArray(data) ? data : [])
      if (!Array.isArray(activities) || activities.length === 0) return []
      return activities.map((a: any, i: number) => ({
        id: a.id ?? i + 1,
        type: a.type ?? 'system_update',
        message: a.message ?? '',
        timestamp: a.timestamp ?? new Date().toISOString(),
        status: (a.status ?? 'info') as ActivityItem['status']
      }))
    } catch {
      return []
    }
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
  async getDashboardTimeseries(userId?: number, period: 'week' | 'month' | 'quarter' = 'week'): Promise<any> {
    const uid = userId ?? this.getUserId() ?? 1
    const response = await this.client.get('/dashboard/timeseries', {
      params: { user_id: uid, period }
    })
    return response.data
  }

  async getIndustryPrompts(): Promise<Record<string, IndustryPromptConfig>> {
    const response = await this.client.get('/dashboard/industry/prompts')
    const data = response.data?.data || response.data || {}
    return data.prompts || {}
  }

  async getIndustryPricingTiers(): Promise<Record<string, any>> {
    const response = await this.client.get('/dashboard/industry/pricing')
    const data = response.data?.data || response.data || {}
    return data.pricing_tiers || {}
  }

  async getIndustryUsage(userId?: number): Promise<IndustryUsageMetrics> {
    const uid = userId ?? this.getUserId() ?? 1
    const response = await this.client.get('/dashboard/industry/usage', {
      params: { user_id: uid }
    })
    const data = response.data?.data || response.data || {}
    return data.usage || {
      tier: 'starter',
      responses: 0,
      tool_calls: 0,
      tokens: 0,
      monthly_cost: 49
    }
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
  /**
   * Loads leads for the current user. The API paginates (default 100, max 500 per request);
   * we page until `has_more` is false so the CRM board matches the full dataset up to a
   * safety cap (large inboxes should move to server-side filters + virtualized UI later).
   */
  async getLeads(): Promise<LeadData[]> {
    const pageSize = 500
    const maxLeads = 25000
    const uid = this.getUserId() ?? 1
    const out: LeadData[] = []
    let offset = 0

    while (out.length < maxLeads) {
      const response = await this.client.get('/crm/leads', {
        params: { user_id: uid, limit: pageSize, offset }
      })
      const payload = response.data?.data ?? response.data
      const backendLeads = payload?.leads ?? []
      const pagination = payload?.pagination as
        | { has_more?: boolean }
        | undefined

      out.push(...backendLeads.map((lead: any) => this.mapLead(lead)))

      const hasMore = pagination?.has_more === true
      if (!hasMore || backendLeads.length === 0) break
      offset += backendLeads.length
    }

    return out
  }

  async getPipeline(): Promise<Record<string, LeadData[]>> {
    const response = await this.client.get('/crm/pipeline', {
      params: { user_id: this.getUserId() ?? 1 }
    })

    const payload = response.data?.data ?? response.data
    const pipeline = payload?.pipeline || {}
    const mapped: Record<string, LeadData[]> = {}

    Object.keys(pipeline).forEach(stage => {
      mapped[stage] = (pipeline[stage] || []).map((lead: any) => this.mapLead(lead))
    })

    return mapped
  }

  /** CRM event timeline for a lead; includes correlation_id when present. */
  async getLeadCrmEvents(
    leadId: string | number,
    params?: { limit?: number; offset?: number }
  ): Promise<{ events: LeadCrmEvent[]; limit: number; offset: number }> {
    const response = await this.client.get(`/crm/leads/${leadId}/events`, {
      params: {
        limit: params?.limit ?? 50,
        offset: params?.offset ?? 0
      }
    })
    const data = response.data?.data ?? response.data
    return {
      events: (data?.events as LeadCrmEvent[]) ?? [],
      limit: data?.limit ?? 50,
      offset: data?.offset ?? 0
    }
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

  async getProfile(): Promise<{ user: { phone?: string; sms_consent?: boolean; sms_consent_at?: string; [k: string]: any } }> {
    const response = await this.client.get('/user/profile')
    const data = response.data?.data ?? response.data
    return { user: data?.user ?? {} }
  }

  async updateProfile(payload: {
    name?: string
    business_name?: string
    business_email?: string
    industry?: string
    team_size?: string
    phone?: string
    sms_consent?: boolean
    timezone?: string
    notification_preferences?: Record<string, any>
  }): Promise<{ user: Record<string, any> }> {
    const response = await this.client.put('/user/profile', payload)
    const data = response.data?.data ?? response.data
    return { user: data?.user ?? {} }
  }

  async deleteAccount(): Promise<{ message?: string }> {
    const response = await this.client.post('/user/delete-account')
    const data = response.data?.data ?? response.data
    return data ?? {}
  }

  async getUserCustomizationLogo(): Promise<{ logoUrl?: string }> {
    const response = await this.client.get('/user/customization/logo')
    const customization = response.data?.data?.customization ?? {}
    return { logoUrl: customization?.logoUrl || undefined }
  }

  async uploadUserCustomizationLogo(file: File): Promise<{ logoUrl?: string }> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await this.client.post('/user/customization/logo', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })

    const customization = response.data?.data?.customization ?? {}
    return { logoUrl: customization?.logoUrl || undefined }
  }

  async deleteUserCustomizationLogo(): Promise<void> {
    await this.client.delete('/user/customization/logo')
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

  async getAutomationCapabilities(): Promise<{ action_type: string; capability: 'implemented' | 'partial' | 'stub'; description?: string }[]> {
    const response = await this.client.get('/automation/capabilities')
    return response.data?.data?.capabilities || response.data?.capabilities || []
  }

  async getTriggerConditionMetadata(): Promise<{
    if_match_values: string[]
    operator_labels: Record<string, string>
    triggers: Record<
      string,
      {
        fields: { value: string; label: string }[]
        string_operators: string[]
        numeric_operators: string[]
        numeric_fields: string[]
      }
    >
  }> {
    const response = await this.client.get('/automation/trigger-condition-metadata')
    const raw = response.data?.data ?? response.data
    return (
      raw ?? {
        if_match_values: ['all'],
        operator_labels: {},
        triggers: {},
      }
    )
  }

  async getAutomationQueueStats(): Promise<{
    queued: number
    running: number
    success: number
    failed: number
    retrying: number
    dead: number
  }> {
    const response = await this.client.get('/automation/queue-stats')
    return response.data?.data || response.data || {}
  }

  async getAutomationMetrics(params?: { hours?: number }): Promise<{
    queued: number
    running: number
    success: number
    failed: number
    retrying: number
    dead: number
    success_rate_24h?: number | null
    total_success_24h?: number
    total_failed_24h?: number
    total_dead_24h?: number
    p95_duration_seconds?: number | null
    period_hours?: number
  }> {
    const response = await this.client.get('/automation/metrics', {
      params: params?.hours ? { hours: params.hours } : undefined
    })
    return response.data?.data || response.data || {}
  }

  async getAutomationJobStatus(jobId: string): Promise<{
    job_id: string
    user_id: number
    payload_type: string
    status: string
    attempt: number
    max_attempts: number
    created_at: string
    started_at?: string
    completed_at?: string
    error_message?: string
    correlation_id?: string | null
    result?: any
  } | null> {
    const response = await this.client.get(`/automation/jobs/${encodeURIComponent(jobId)}`)
    return response.data?.data || response.data || null
  }

  /** Debug: stitched domain rows for one correlation_id (auth required; see docs/CORRELATION_AND_EVENTS.md). */
  async getCorrelationTrace(correlationId: string): Promise<{
    correlation_id: string
    user_id: number
    limits: { per_section: number }
    sections: Record<string, unknown[]>
    notes?: string[]
  } | null> {
    const response = await this.client.get(
      `/debug/correlation/${encodeURIComponent(correlationId)}`
    )
    return response.data?.data ?? null
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
    const correlationId =
      typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2, 12)}`
    const response = await this.client.post(
      '/automation/test/preset',
      { preset_id: presetId, correlation_id: correlationId },
      { headers: { 'X-Correlation-ID': correlationId } }
    )
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

  async getEmails(params?: {
    filter?: string
    limit?: number
    query?: string
    use_synced?: boolean
    /** false = list only (snippets); full body via getEmailMessage(id) */
    include_body?: boolean
  }): Promise<any> {
    const response = await this.client.get('/email/messages', {
      params: {
        ...params,
        user_id: this.getUserId() ?? 1,
        use_synced: params?.use_synced ?? true,
        include_body: params?.include_body ?? false
      }
    })
    return response.data.data || response.data
  }

  /** Full email body (synced row or Gmail). Use after list fetch with include_body=false. */
  async getEmailMessage(emailId: string): Promise<any | null> {
    const enc = encodeURIComponent(emailId)
    const response = await this.client.get(`/email/messages/${enc}`, {
      params: { user_id: this.getUserId() ?? 1 }
    })
    const data = response.data?.data ?? response.data
    return data?.email ?? null
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

  /** Aggregated migration map: formats, endpoints, template inventory */
  async getContentMigrationCapabilities(): Promise<ContentMigrationCapabilities> {
    const response = await this.client.get('/migration/capabilities')
    const data = response.data?.data ?? response.data
    return data as ContentMigrationCapabilities
  }

  async listDocsFormsDocumentTemplates(): Promise<DocsFormsDocumentTemplateSummary[]> {
    const response = await this.client.get('/docs-forms/templates')
    return response.data?.templates || []
  }

  async listDocsFormsFormTemplates(): Promise<DocsFormsFormTemplateSummary[]> {
    const response = await this.client.get('/docs-forms/forms/templates')
    return response.data?.templates || []
  }

  /**
   * POST /api/chatbot/knowledge/import — same shape as public API; uses session JWT.
   */
  async importKnowledgeItem(payload: {
    title?: string
    content?: string
    question?: string
    answer?: string
    category?: string
    document_type?: string
    tags?: string[]
    keywords?: string[]
  }): Promise<{ success?: boolean; document_id?: string }> {
    const response = await this.client.post('/chatbot/knowledge/import', payload)
    return response.data
  }

  async bulkImportKnowledgeDocuments(documents: Record<string, unknown>[]): Promise<{
    success?: boolean
    imported?: number
    total?: number
    results?: Array<{ index: number; success: boolean; document_id?: string; error?: string }>
  }> {
    const response = await this.client.post('/chatbot/knowledge/import/bulk', { documents })
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

  async markEmailRead(emailId: string): Promise<{ read: boolean }> {
    const response = await this.client.post('/email/mark-read', {
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

  /** Export all leads as CSV file download. */
  async exportLeadsCsv(): Promise<void> {
    const response = await this.client.get('/crm/leads/export', { responseType: 'blob' })
    const blob = response.data as Blob
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'leads.csv'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  /**
   * Import leads from a CSV file. Returns summary: imported, created, updated, skipped, skipped_details.
   * onDuplicate: skip | update | merge (server default update).
   */
  async importLeadsCsv(
    file: File,
    options?: { onDuplicate?: 'skip' | 'update' | 'merge' }
  ): Promise<{
    imported: number
    created: number
    updated: number
    skipped: number
    skipped_details: Array<{ row: number; reason: string; email?: string }>
    total_rows: number
  }> {
    const formData = new FormData()
    formData.append('file', file)
    const onDup = options?.onDuplicate ?? 'update'
    formData.append('on_duplicate', onDup)
    const response = await this.client.post('/crm/leads/import/csv', formData, {
      params: { on_duplicate: onDup },
    })
    const data = response.data?.data ?? response.data
    return data
  }

  private mapLead(lead: any): LeadData {
    const metadata =
      lead && typeof lead.metadata === 'object'
        ? lead.metadata
        : (() => {
            if (typeof lead?.metadata !== 'string') return {}
            try {
              return JSON.parse(lead.metadata)
            } catch {
              return {}
            }
          })()
    const breakdown =
      metadata && typeof metadata.score_breakdown === 'object'
        ? (metadata.score_breakdown as Record<string, number | string>)
        : undefined
    const scoringVersion =
      typeof metadata?.scoring_version === 'string'
        ? metadata.scoring_version
        : typeof breakdown?.version === 'string'
          ? breakdown.version
          : undefined

    return {
      id: (lead.id ?? lead.lead_id ?? '').toString(),
      name: lead.name || 'Unknown',
      email: lead.email || '',
      company: lead.company || '',
      stage: lead.stage || 'new',
      score: lead.score || 0,
      scoreBreakdown: breakdown,
      scoringVersion,
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

  async createCheckoutSession(
    tierName: string,
    billingPeriod: 'monthly' | 'annual' = 'monthly',
    useTrial: boolean = true,
    paymentMethodTypes: string[] = ['card', 'us_bank_account']
  ): Promise<{ checkout_url: string; session_id: string }> {
    const response = await this.client.post('/billing/checkout', {
      tier_name: tierName,
      billing_period: billingPeriod,
      trial: useTrial,
      payment_method_types: paymentMethodTypes,
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

  async redeemTestAccessCode(code: string): Promise<{
    success: boolean
    message?: string
    access?: { status: string; tier: string; expires_at: number }
  }> {
    const response = await this.client.post('/billing/test-access/redeem', { code })
    if (!response.data?.success) {
      throw new Error(response.data?.error || 'Failed to redeem access code')
    }
    return response.data
  }

  async getTestAccessAudit(limit = 50): Promise<Array<{
    id: number
    user_id: number
    email: string | null
    code_hint: string | null
    redeemed_at: number
    expires_at: number
    currently_active: boolean
  }>> {
    const response = await this.client.get('/billing/test-access/audit', {
      params: { limit }
    })
    if (!response.data?.success) {
      throw new Error(response.data?.error || 'Failed to load test access audit')
    }
    return response.data?.audit || []
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

  /**
   * Stripe customer record for the logged-in user, or null when unavailable / misconfigured Stripe.
   */
  async getCustomerDetails(): Promise<{
    customer: Record<string, unknown> | null
    billingUnavailable?: boolean
    message?: string
  }> {
    const response = await this.client.get('/billing/customer/details')
    const d = response.data
    return {
      customer: (d?.customer as Record<string, unknown> | undefined) ?? null,
      billingUnavailable: Boolean(d?.billing_unavailable),
      message: typeof d?.message === 'string' ? d.message : undefined,
    }
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

  async createSetupCheckoutSession(paymentMethodTypes: string[] = ['card']): Promise<{ url: string; session_id?: string }> {
    const response = await this.client.post('/billing/setup-checkout', {
      payment_method_types: paymentMethodTypes
    })
    if (!response.data.success) {
      throw new Error(response.data.error || 'Failed to create setup checkout session')
    }
    return {
      url: response.data.url,
      session_id: response.data.session_id
    }
  }

  async getApiKeys(): Promise<ApiKeySummary[]> {
    const response = await this.client.get('/user/api-keys')
    return response.data?.data?.keys || []
  }

  async createApiKey(params?: {
    name?: string
    description?: string
    scopes?: string[]
    allowed_origins?: string[] | string
  }): Promise<ApiKeyCreateResponse> {
    const response = await this.client.post('/user/api-keys', params || {})
    if (!response.data?.success) {
      throw new Error(response.data?.error || 'Failed to create API key')
    }
    return response.data?.data
  }

  /** Public contact form → info@fikirisolutions.com. UTF-8, enforced limits on backend. */
  async submitContact(payload: {
    name: string
    email: string
    phone?: string
    company?: string
    subject?: string
    message: string
  }): Promise<{ success: boolean; message?: string; error?: string }> {
    const response = await this.client.post('/contact', payload, {
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
    })
    return response.data
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
