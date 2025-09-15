/**
 * Mock Data for Local Testing
 * 
 * Use this data while backend stabilizes.
 * Swap to real API calls when ready.
 */

export const mockServices = [
  {
    id: 'ai-assistant',
    name: 'AI Email Assistant',
    status: 'active',
    description: 'Automated email responses and lead management',
    metrics: {
      totalResponses: 89,
      avgResponseTime: '2.3h',
      successRate: '94%'
    }
  },
  {
    id: 'crm',
    name: 'CRM Service',
    status: 'active',
    description: 'Lead tracking and customer relationship management',
    metrics: {
      totalLeads: 23,
      activeLeads: 15,
      conversionRate: '12%'
    }
  },
  {
    id: 'email-parser',
    name: 'Email Parser',
    status: 'active',
    description: 'Intelligent email content analysis',
    metrics: {
      emailsProcessed: 156,
      accuracy: '97%',
      avgProcessingTime: '0.3s'
    }
  },
  {
    id: 'ml-scoring',
    name: 'ML Lead Scoring',
    status: 'inactive',
    description: 'AI-powered lead prioritization',
    metrics: {
      leadsScored: 0,
      avgScore: 0,
      modelAccuracy: 'N/A'
    }
  }
]

export const mockMetrics = {
  totalEmails: 156,
  activeLeads: 23,
  aiResponses: 89,
  avgResponseTime: 2.3,
  conversionRate: 12.5,
  customerSatisfaction: 4.7
}

export const mockActivity = [
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

export const mockLeads = [
  {
    id: '1',
    name: 'John Smith',
    email: 'john@acme.com',
    company: 'Acme Corp',
    stage: 'qualified',
    score: 8.5,
    lastContact: '2 hours ago',
    source: 'email'
  },
  {
    id: '2',
    name: 'Jane Doe',
    email: 'jane@startup.io',
    company: 'Startup Inc',
    stage: 'new',
    score: 6.2,
    lastContact: '1 day ago',
    source: 'website'
  },
  {
    id: '3',
    name: 'Bob Johnson',
    email: 'bob@tech.com',
    company: 'Tech Solutions',
    stage: 'contacted',
    score: 7.8,
    lastContact: '3 hours ago',
    source: 'referral'
  }
]

/**
 * Mock API responses
 */
export const mockApiResponses = {
  health: {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    services: {
      'ai-assistant': { available: true, status: 'healthy' },
      'crm': { available: true, status: 'healthy' },
      'email-parser': { available: true, status: 'healthy' },
      'ml-scoring': { available: false, status: 'inactive' }
    }
  },
  
  services: mockServices,
  metrics: mockMetrics,
  activity: mockActivity,
  leads: mockLeads
}

/**
 * Simulate API delay for realistic testing
 */
export const simulateApiDelay = (ms: number = 500) => 
  new Promise(resolve => setTimeout(resolve, ms))

/**
 * Mock API client for local testing
 */
export class MockApiClient {
  async get(endpoint: string) {
    await simulateApiDelay()
    
    switch (endpoint) {
      case '/api/health':
        return { data: mockApiResponses.health }
      case '/api/services':
        return { data: mockApiResponses.services }
      case '/api/metrics':
        return { data: mockApiResponses.metrics }
      case '/api/activity':
        return { data: mockApiResponses.activity }
      case '/api/leads':
        return { data: mockApiResponses.leads }
      default:
        throw new Error(`Mock API: Endpoint ${endpoint} not found`)
    }
  }
  
  async post(endpoint: string, data?: any) {
    await simulateApiDelay()
    
    switch (endpoint) {
      case '/api/auth/login':
        return { data: { token: 'mock-jwt-token', user: { email: data?.email } } }
      case '/api/test/ai-assistant':
        return { data: { success: true, response: 'Mock AI response generated' } }
      case '/api/test/crm':
        return { data: { success: true, message: 'Mock CRM test completed' } }
      default:
        return { data: { success: true, message: 'Mock operation completed' } }
    }
  }
}
