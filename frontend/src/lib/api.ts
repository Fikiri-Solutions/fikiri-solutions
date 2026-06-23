// lib/api.ts
// Shared fetch helper with cookie credentials for Fikiri Solutions
// Rule 5.2: All fetches must use config.apiUrl

import { config } from '../config';
import { useAuth } from '../store/auth';

const API_BASE_URL = config.apiUrl;

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
  error_code?: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public errorCode?: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

function getCurrentAccessToken(): string | null {
  const inMemoryToken = useAuth.getState().accessToken;
  if (inMemoryToken) {
    return inMemoryToken;
  }

  if (typeof window !== 'undefined') {
    return localStorage.getItem('fikiri-token');
  }

  return null;
}

export async function api<T = any>(
  url: string, 
  init: RequestInit = {}
): Promise<T> {
  const fullUrl = `${API_BASE_URL}${url}`;
  
  const accessToken = getCurrentAccessToken();
  const headers = new Headers(init.headers || {});
  if (!headers.has('Content-Type') && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  if (accessToken && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }

  const config: RequestInit = {
    ...init,
    headers,
  };

  // Handle request body
  if (init.body && typeof init.body === 'object' && !(init.body instanceof FormData)) {
    config.body = JSON.stringify(init.body);
  }

  try {
    const response = await fetch(fullUrl, config);
    
    // Handle 401 unauthorized
    if (response.status === 401) {
      throw new ApiError('Unauthorized', 401, 'UNAUTHORIZED');
    }
    
    // Handle other errors
    if (!response.ok) {
      const errorText = await response.text();
      let errorData;
      try {
        errorData = JSON.parse(errorText);
      } catch {
        errorData = { error: errorText };
      }
      
      throw new ApiError(
        errorData.error || errorData.message || 'Request failed',
        response.status,
        errorData.error_code
      );
    }
    
    const data: ApiResponse<T> = await response.json();
    
    if (!data.success) {
      throw new ApiError(
        data.error || data.message || 'Request failed',
        response.status,
        data.error_code
      );
    }
    
    return data.data || data as T;
    
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof Error && error.name === 'AbortError') {
      throw error;
    }
    
    // Network or other errors
    throw new ApiError(
      error instanceof Error ? error.message : 'Network error',
      0
    );
  }
}

async function apiRaw<T = any>(
  url: string,
  init: RequestInit = {}
): Promise<ApiResponse<T>> {
  const fullUrl = `${API_BASE_URL}${url}`;
  const accessToken = getCurrentAccessToken();
  const headers = new Headers(init.headers || {});
  if (!headers.has('Content-Type') && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  if (accessToken && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }

  const requestConfig: RequestInit = {
    ...init,
    headers,
  };

  if (init.body && typeof init.body === 'object' && !(init.body instanceof FormData)) {
    requestConfig.body = JSON.stringify(init.body);
  }

  try {
    const response = await fetch(fullUrl, requestConfig);
    const responseText = await response.text();
    const data = responseText ? JSON.parse(responseText) : {};

    if (!response.ok) {
      throw new ApiError(
        data.error || data.message || 'Request failed',
        response.status,
        data.error_code
      );
    }

    if (data.success === false) {
      throw new ApiError(
        data.error || data.message || 'Request failed',
        response.status,
        data.error_code
      );
    }

    return data;
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw error;
    }
    throw error;
  }
}

// Convenience methods
export const apiGet = <T = any>(url: string, init?: RequestInit) =>
  api<T>(url, { ...init, method: 'GET' });

export const apiPost = <T = any>(url: string, body?: any, init?: RequestInit) =>
  api<T>(url, { ...init, method: 'POST', body });

export const apiPut = <T = any>(url: string, body?: any, init?: RequestInit) =>
  api<T>(url, { ...init, method: 'PUT', body });

export const apiPatch = <T = any>(url: string, body?: any, init?: RequestInit) =>
  api<T>(url, { ...init, method: 'PATCH', body });

export const apiDelete = <T = any>(url: string, init?: RequestInit) =>
  api<T>(url, { ...init, method: 'DELETE' });

// Auth-specific API calls
export const authApi = {
  login: (email: string, password: string) =>
    apiPost<{
      user: {
        id: number;
        email: string;
        name: string;
        role: string;
        onboarding_completed: boolean;
        onboarding_step: number;
      };
      access_token: string;
      refresh_token?: string;
      expires_in: number;
      token_type: string;
    }>('/auth/login', { email, password }),
    
  signup: (userData: {
    email: string;
    password: string;
    name: string;
    business_name?: string;
    business_email?: string;
    industry?: string;
    team_size?: string;
  }) =>
    apiPost<{
      user: {
        id: number;
        email: string;
        name: string;
        role: string;
        onboarding_completed: boolean;
        onboarding_step: number;
      };
      access_token: string;
      refresh_token?: string;
      expires_in: number;
      token_type: string;
    }>('/auth/signup', userData),
    
  refresh: (refreshToken: string) =>
    apiPost<{
      tokens?: {
        access_token: string;
        refresh_token?: string;
        expires_in: number;
        token_type: string;
      };
      access_token: string;
      refresh_token?: string;
      expires_in: number;
      token_type: string;
    }>('/auth/refresh', { refresh_token: refreshToken }),
    
  whoami: () =>
    apiGet<{
      authenticated: boolean;
      user?: {
        id: number;
        email: string;
        name: string;
        role: string;
        onboarding_completed: boolean;
        onboarding_step: number;
      };
      session_exists: boolean;
      token_valid: boolean;
      cookies: {
        fikiri_session: boolean;
        fikiri_refresh_token: boolean;
      };
      headers: {
        authorization: boolean;
        origin?: string;
        user_agent?: string;
      };
    }>('/auth/whoami'),
    
  logout: () =>
    apiPost('/auth/logout'),
};

export interface ServiceStatus {
  status: 'healthy' | 'unhealthy' | 'error';
  available: boolean;
  initialized: boolean;
  authenticated?: boolean;
  enabled?: boolean;
  error?: string;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  version: string;
  services: Record<string, ServiceStatus>;
}

export interface MetricData {
  totalEmails: number;
  activeLeads: number;
  aiResponses: number;
  avgResponseTime: number;
}

export interface ServiceData {
  id: string;
  name: string;
  status: 'active' | 'inactive' | 'error' | string;
  description: string;
}

export interface ActivityItem {
  id: number;
  type: string;
  message: string;
  timestamp: string;
  status: 'success' | 'warning' | 'error' | string;
}

export interface LeadData {
  id: string;
  name: string;
  email: string;
  company: string;
  stage: string;
  score: number;
  lastContact: string;
  source: string;
}

const formatServiceName = (id: string): string => {
  const nameMap: Record<string, string> = {
    config: 'Configuration',
    auth: 'Authentication',
    parser: 'Email Parser',
    gmail: 'Gmail Service',
    actions: 'Email Actions',
    crm: 'CRM Service',
    ai_assistant: 'AI Assistant',
    ml_scoring: 'ML Lead Scoring',
    vector_search: 'Vector Search',
    feature_flags: 'Feature Flags',
  };
  return nameMap[id] || id.charAt(0).toUpperCase() + id.slice(1);
};

const getServiceDescription = (id: string): string => {
  const descMap: Record<string, string> = {
    config: 'System configuration and settings',
    auth: 'User authentication and authorization',
    parser: 'Intelligent email content analysis',
    gmail: 'Gmail API integration and email management',
    actions: 'Automated email actions and responses',
    crm: 'Customer relationship management',
    ai_assistant: 'AI-powered email responses and classification',
    ml_scoring: 'Machine learning lead scoring and prioritization',
    vector_search: 'Semantic search and document retrieval',
    feature_flags: 'Feature flag management and control',
  };
  return descMap[id] || 'Service description not available';
};

export const apiClient = {
  getHealth: () => api<HealthResponse>('/health'),

  getStatus: () => api<HealthResponse>('/health'),

  async getMetrics(): Promise<MetricData> {
    try {
      return await api<MetricData>('/metrics');
    } catch {
      return {
        totalEmails: Math.floor(Math.random() * 1000) + 100,
        activeLeads: Math.floor(Math.random() * 50) + 10,
        aiResponses: Math.floor(Math.random() * 100) + 50,
        avgResponseTime: Math.random() * 5 + 1,
      };
    }
  },

  async getServices(): Promise<ServiceData[]> {
    const health = await apiClient.getHealth();
    return Object.entries(health.services).map(([id, status]) => ({
      id,
      name: formatServiceName(id),
      status: status.status === 'healthy' ? 'active' : 'inactive',
      description: getServiceDescription(id),
    }));
  },

  getActivity: async (_limit?: number): Promise<ActivityItem[]> => [
    {
      id: 1,
      type: 'ai_response',
      message: 'AI Assistant responded to inquiry from john@acme.com',
      timestamp: '2 minutes ago',
      status: 'success',
    },
    {
      id: 2,
      type: 'lead_added',
      message: 'New lead added: Jane Smith from Startup Inc',
      timestamp: '15 minutes ago',
      status: 'success',
    },
    {
      id: 3,
      type: 'email_processed',
      message: 'Email automation triggered for urgent inquiry',
      timestamp: '1 hour ago',
      status: 'success',
    },
    {
      id: 4,
      type: 'service_error',
      message: 'ML Scoring service temporarily unavailable',
      timestamp: '2 hours ago',
      status: 'warning',
    },
  ],

  testEmailParser: () => apiPost('/test/email-parser', {}),
  testEmailActions: () => apiPost('/test/email-actions', {}),
  testCRM: () => apiPost('/test/crm', {}),
  testMLScoring: () => apiPost('/test/ml-scoring', {}),
  testVectorSearch: () => apiPost('/test/vector-search', {}),

  sendChatMessage: (message: string, context?: any) =>
    apiPost('/ai/chat', {
      message,
      user_id: 1,
      context: context || {},
    }),

  getDashboardTimeseries: (userId: number = 1, period: 'week' | 'month' | 'quarter' = 'week') =>
    apiRaw(`/dashboard/timeseries?user_id=${encodeURIComponent(userId)}&period=${encodeURIComponent(period)}`),

  getDashboardMetrics: (userId: number = 1) =>
    apiRaw(`/dashboard/metrics?user_id=${encodeURIComponent(userId)}`),

  getDashboardLeads: (filters?: {
    dateRange?: { start: string; end: string };
    status?: string;
    source?: string;
  }) => {
    const params = new URLSearchParams();
    if (filters?.status) params.set('status', filters.status);
    if (filters?.source) params.set('source', filters.source);
    if (filters?.dateRange?.start) params.set('start', filters.dateRange.start);
    if (filters?.dateRange?.end) params.set('end', filters.dateRange.end);
    const query = params.toString();
    return apiRaw(`/dashboard/leads${query ? `?${query}` : ''}`);
  },

  getEmailMetrics: (period: 'day' | 'week' | 'month' = 'week') =>
    apiRaw(`/dashboard/emails?period=${encodeURIComponent(period)}`),

  getAIMetrics: () => apiRaw('/dashboard/ai'),

  getRevenueAnalytics: (period: 'week' | 'month' | 'quarter' = 'month') =>
    apiRaw(`/dashboard/revenue?period=${encodeURIComponent(period)}`),

  updateDashboardPreferences: (preferences: {
    defaultView?: string;
    refreshInterval?: number;
    notifications?: boolean;
  }) => apiPost('/dashboard/preferences', preferences),

  testAIAssistant: () =>
    apiPost('/test/ai-assistant', {
      content: 'Hi, I need help with your services.',
      sender: 'Test User',
      subject: 'Test Subject',
    }),

  async getLeads(): Promise<LeadData[]> {
    const response = await apiRaw<any>('/crm/leads?user_id=1');
    const backendLeads = response.data?.leads || (response as any).leads || [];
    return backendLeads.map((lead: any) => ({
      id: lead.id,
      name: lead.name,
      email: lead.email,
      company: lead.company || '',
      stage: lead.stage,
      score: lead.score || 0,
      lastContact: lead.last_contact || lead.created_at,
      source: lead.source,
    }));
  },

  addLead: (leadData: LeadData) => apiPost<LeadData>('/crm/leads', leadData),

  handleError(error: any): string {
    if (error instanceof ApiError) {
      return `Server error: ${error.status} - ${error.message}`;
    }
    if (error?.response) {
      return `Server error: ${error.response.status} - ${error.response.data?.error || error.message}`;
    }
    if (error?.request) {
      return 'Network error: Unable to connect to server';
    }
    return `Error: ${error?.message || 'Request failed'}`;
  },
};
