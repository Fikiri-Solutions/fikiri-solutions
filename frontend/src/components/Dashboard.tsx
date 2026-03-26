import React, { useState, useEffect } from 'react'
import { Mail, Users, Zap, ArrowRight, AlertCircle } from 'lucide-react'
import { apiClient } from '../services/apiClient'

interface DashboardData {
  leads_count: number
  activities_count: number
  sync_records_count: number
  recent_leads: Array<{
    id: number
    name: string
    email: string
    company: string
    stage: string
    created_at: string
  }>
  unread_emails: number
  automations_executed: number
  gmail_connected: boolean
  last_sync: string
}

interface DashboardProps {
  userId: number
}

export const Dashboard: React.FC<DashboardProps> = ({ userId }) => {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [aiResponse, setAiResponse] = useState<string | null>(null)
  const [isAiLoading, setIsAiLoading] = useState(false)

  useEffect(() => {
    loadDashboardData()
    // Poll for updates every 30 seconds
    const interval = setInterval(loadDashboardData, 30000)
    return () => clearInterval(interval)
  }, [userId])

  const loadDashboardData = async () => {
    try {
      const [crmData, analyticsData, gmailData] = await Promise.all([
        apiClient.request<{ success?: boolean; data?: { total_count?: number; leads?: any[] } }>('GET', '/crm/leads', { params: { user_id: userId } }),
        apiClient.request<{ success?: boolean; data?: { activities_count?: number; sync_records_count?: number; privacy_settings?: { updated_at?: string } } }>('GET', '/privacy/data-summary', { params: { user_id: userId } }),
        apiClient.request<{ success?: boolean; data?: { connected?: boolean } }>('GET', '/auth/gmail/status', { params: { user_id: userId } })
      ])

      if (crmData?.success && analyticsData?.success) {
        setDashboardData({
          leads_count: crmData.data?.total_count ?? 0,
          activities_count: analyticsData.data?.activities_count ?? 0,
          sync_records_count: analyticsData.data?.sync_records_count ?? 0,
          recent_leads: (crmData.data?.leads ?? []).slice(0, 5),
          unread_emails: 0,
          automations_executed: 0,
          gmail_connected: Boolean(gmailData?.success && gmailData?.data?.connected),
          last_sync: analyticsData.data?.privacy_settings?.updated_at || 'Never'
        })
      }
    } catch (error) {
      setError('Failed to load dashboard data')
    } finally {
      setIsLoading(false)
    }
  }

  const askAI = async (question: string) => {
    setIsAiLoading(true)
    try {
      const result = await apiClient.sendChatMessage(question, { user_id: userId })

      if (result?.response) {
        setAiResponse(result.response)
      } else {
        setAiResponse('I apologize, but I encountered an issue processing your request.')
      }
    } catch (error) {
      setAiResponse('I apologize, but I encountered an issue processing your request.')
    } finally {
      setIsAiLoading(false)
    }
  }

  const getGreeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return 'Good morning'
    if (hour < 18) return 'Good afternoon'
    return 'Good evening'
  }

  const getNextBestAction = () => {
    if (!dashboardData) return null

    if (!dashboardData.gmail_connected) {
      return {
        title: 'Connect Gmail',
        description: 'Connect your Gmail account to start automating your emails',
        action: 'Connect Gmail',
        href: '/onboarding'
      }
    }

    if (dashboardData.leads_count === 0) {
      return {
        title: 'Add Your First Lead',
        description: 'Start by adding a lead manually or wait for emails to be processed',
        action: 'Add Lead',
        href: '/crm'
      }
    }

    if (dashboardData.automations_executed === 0) {
      return {
        title: 'Set Up Your First Automation',
        description: 'Automate responses to new leads and save time',
        action: 'Create Automation',
        href: '/automation'
      }
    }

    return {
      title: 'Review Recent Leads',
      description: 'Check out your latest leads and follow up',
      action: 'View Leads',
      href: '/crm'
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        {/* Loading Skeletons */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
              <div className="animate-pulse">
                <div className="h-4 bg-gray-200 dark:bg-gray-600 rounded w-1/2 mb-2"></div>
                <div className="h-8 bg-gray-200 dark:bg-gray-600 rounded w-1/3"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg p-6">
        <div className="flex items-center">
          <AlertCircle className="h-5 w-5 text-red-400 dark:text-red-300 mr-3 shrink-0" />
          <p className="text-red-800 dark:text-red-200">{error}</p>
        </div>
      </div>
    )
  }

  const nextBestAction = getNextBestAction()

  return (
    <div className="space-y-6">
      {/* Welcome Header */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg p-6 text-white">
        <h1 className="text-2xl font-bold mb-2">
          {getGreeting()}, {localStorage.getItem('fikiri-user') ? JSON.parse(localStorage.getItem('fikiri-user')!).name : 'there'}!
        </h1>
        <p className="text-blue-100">
          {dashboardData?.gmail_connected ? (
            <>Connected to Gmail ✅ — {dashboardData.leads_count} leads detected. Try asking: "Who emailed me last?"</>
          ) : (
            'Welcome to Fikiri Solutions! Connect your Gmail to get started.'
          )}
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">New Leads This Week</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white">{dashboardData?.leads_count || 0}</p>
            </div>
            <div className="bg-blue-100 dark:bg-blue-900/40 rounded-full p-3">
              <Users className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
          </div>
          <div className="mt-4">
            <button
              onClick={() => window.location.href = '/crm'}
              className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 text-sm font-medium flex items-center"
            >
              View all leads
              <ArrowRight className="h-4 w-4 ml-1" />
            </button>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Unread Important Emails</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white">{dashboardData?.unread_emails || 0}</p>
            </div>
            <div className="bg-green-100 dark:bg-green-900/40 rounded-full p-3">
              <Mail className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
          </div>
          <div className="mt-4">
            <button
              onClick={() => askAI('Show me my recent emails')}
              className="text-green-600 dark:text-green-400 hover:text-green-700 dark:hover:text-green-300 text-sm font-medium flex items-center"
            >
              Check emails
              <ArrowRight className="h-4 w-4 ml-1" />
            </button>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Automations Executed Today</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white">{dashboardData?.automations_executed || 0}</p>
            </div>
            <div className="bg-purple-100 dark:bg-purple-900/40 rounded-full p-3">
              <Zap className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
          </div>
          <div className="mt-4">
            <button
              onClick={() => window.location.href = '/automation'}
              className="text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 text-sm font-medium flex items-center"
            >
              Manage automations
              <ArrowRight className="h-4 w-4 ml-1" />
            </button>
          </div>
        </div>
      </div>

      {/* Next Best Action */}
      {nextBestAction && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">{nextBestAction.title}</h3>
              <p className="text-gray-600 dark:text-gray-300">{nextBestAction.description}</p>
            </div>
            <button
              onClick={() => window.location.href = nextBestAction.href}
              className="bg-blue-600 dark:bg-blue-500 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 dark:hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:focus:ring-offset-gray-800 flex items-center"
            >
              {nextBestAction.action}
              <ArrowRight className="h-4 w-4 ml-2" />
            </button>
          </div>
        </div>
      )}

      {/* AI Assistant */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">AI Assistant</h3>
        
        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <button
            onClick={() => askAI('Who emailed me last?')}
            disabled={isAiLoading}
            className="p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 text-left disabled:opacity-50"
          >
            <Mail className="h-5 w-5 text-blue-600 dark:text-blue-400 mb-2" />
            <p className="font-medium text-gray-900 dark:text-white">Who emailed me last?</p>
            <p className="text-sm text-gray-600 dark:text-gray-400">Get recent email activity</p>
          </button>

          <button
            onClick={() => askAI('How many leads do I have?')}
            disabled={isAiLoading}
            className="p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 text-left disabled:opacity-50"
          >
            <Users className="h-5 w-5 text-green-600 dark:text-green-400 mb-2" />
            <p className="font-medium text-gray-900 dark:text-white">How many leads do I have?</p>
            <p className="text-sm text-gray-600 dark:text-gray-400">Check your lead count</p>
          </button>

          <button
            onClick={() => askAI('Set up an auto-reply rule')}
            disabled={isAiLoading}
            className="p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 text-left disabled:opacity-50"
          >
            <Zap className="h-5 w-5 text-purple-600 dark:text-purple-400 mb-2" />
            <p className="font-medium text-gray-900 dark:text-white">Set up an auto-reply rule</p>
            <p className="text-sm text-gray-600 dark:text-gray-400">Create automation</p>
          </button>
        </div>

        {/* AI Response */}
        {aiResponse && (
          <div className="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <div className="flex items-start">
              <div className="bg-blue-100 dark:bg-blue-800/50 rounded-full p-2 mr-3 shrink-0">
                <Zap className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-1">AI Assistant</h4>
                <p className="text-blue-800 dark:text-blue-200">{aiResponse}</p>
              </div>
            </div>
          </div>
        )}

        {isAiLoading && (
          <div className="bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg p-4">
            <div className="flex items-center">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 dark:border-blue-400 mr-3"></div>
              <p className="text-gray-600 dark:text-gray-300">AI Assistant is thinking...</p>
            </div>
          </div>
        )}
      </div>

      {/* Recent Leads */}
      {dashboardData?.recent_leads && dashboardData.recent_leads.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Recent Leads</h3>
            <button
              onClick={() => window.location.href = '/crm'}
              className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 text-sm font-medium flex items-center"
            >
              View all
              <ArrowRight className="h-4 w-4 ml-1" />
            </button>
          </div>
          
          <div className="space-y-3">
            {dashboardData.recent_leads.map((lead) => (
              <div key={lead.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">{lead.name}</p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">{lead.email}</p>
                  {lead.company && (
                    <p className="text-xs text-gray-500 dark:text-gray-400">{lead.company}</p>
                  )}
                </div>
                <div className="text-right">
                  <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                    lead.stage === 'new' ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-200' :
                    lead.stage === 'contacted' ? 'bg-yellow-100 dark:bg-yellow-900/40 text-yellow-800 dark:text-yellow-200' :
                    lead.stage === 'replied' ? 'bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-200' :
                    'bg-gray-100 dark:bg-gray-600 text-gray-800 dark:text-gray-200'
                  }`}>
                    {lead.stage}
                  </span>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {new Date(lead.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {dashboardData?.leads_count === 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 text-center">
          <Users className="h-12 w-12 text-gray-400 dark:text-gray-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">No leads yet</h3>
          <p className="text-gray-600 dark:text-gray-300 mb-4">
            Connect Gmail to automatically detect leads from your emails, or add your first lead manually.
          </p>
          <div className="flex justify-center space-x-4">
            <button
              onClick={() => window.location.href = '/onboarding'}
              className="bg-blue-600 dark:bg-blue-500 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 dark:hover:bg-blue-600"
            >
              Connect Gmail
            </button>
            <button
              onClick={() => window.location.href = '/crm'}
              className="bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 px-6 py-3 rounded-lg font-medium hover:bg-gray-200 dark:hover:bg-gray-600"
            >
              Add Lead Manually
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
