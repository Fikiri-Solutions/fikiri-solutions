import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../services/apiClient'
import { useAuth } from '../contexts/AuthContext'
import { 
  BarChart3, 
  Mail, 
  Brain, 
  Users, 
  Zap, 
  TrendingUp, 
  TrendingDown,
  Calendar,
  Clock,
  Activity,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Lightbulb,
  ArrowRight
} from 'lucide-react'

interface MetricCardProps {
  title: string
  value: string | number
  change?: number
  icon: React.ReactNode
  subtitle?: string
}

const MetricCard: React.FC<MetricCardProps> = ({ title, value, change, icon, subtitle }) => {
  const isPositive = change !== undefined && change >= 0
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between mb-4">
        <div className="p-2 bg-brand-primary/10 dark:bg-brand-primary/20 rounded-lg">
          {icon}
        </div>
        {change !== undefined && (
          <div className={`flex items-center gap-1 text-sm ${isPositive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
            {isPositive ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
            <span>{Math.abs(change)}%</span>
          </div>
        )}
      </div>
      <h3 className="text-sm font-medium text-brand-text/70 dark:text-gray-400 mb-1">{title}</h3>
      <p className="text-2xl font-bold text-brand-text dark:text-white">{value}</p>
      {subtitle && (
        <p className="text-xs text-brand-text/60 dark:text-gray-500 mt-1">{subtitle}</p>
      )}
    </div>
  )
}

export const UsageAnalytics: React.FC = () => {
  const { user } = useAuth()
  const [period, setPeriod] = useState<'day' | 'week' | 'month'>('week')

  // Fetch dashboard metrics
  const { data: dashboardMetrics, isLoading: loadingMetrics } = useQuery({
    queryKey: ['dashboard-metrics', user?.id],
    queryFn: () => apiClient.getDashboardMetrics(user?.id || 1),
    enabled: !!user,
    staleTime: 2 * 60 * 1000, // 2 minutes
  })

  // Fetch email metrics
  const { data: emailMetrics, isLoading: loadingEmail } = useQuery({
    queryKey: ['email-metrics', period],
    queryFn: () => apiClient.getEmailMetrics(period),
    enabled: !!user,
    staleTime: 2 * 60 * 1000,
  })

  // Fetch AI metrics
  const { data: aiMetrics, isLoading: loadingAI } = useQuery({
    queryKey: ['ai-metrics'],
    queryFn: () => apiClient.getAIMetrics(),
    enabled: !!user,
    staleTime: 2 * 60 * 1000,
  })

  const isLoading = loadingMetrics || loadingEmail || loadingAI

  const metrics = dashboardMetrics?.data || dashboardMetrics || {}
  const emailData = emailMetrics?.data || emailMetrics || {}
  const aiData = aiMetrics?.data || aiMetrics || {}

  // Calculate derived metrics
  const totalEmails = emailData.total_emails || metrics.email?.total_emails || 0
  const unreadEmails = emailData.unread_emails || metrics.email?.unread_emails || 0
  const aiResponses = aiData.total_responses || aiData.responses || 0
  const totalLeads = metrics.leads?.total || 0
  const activeAutomations = metrics.automation?.active_automations || 0

  if (!user) {
    return (
      <div className="flex items-center justify-center h-full min-h-[60vh]">
        <div className="max-w-md p-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 text-center">
          <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h2 className="text-2xl font-semibold text-brand-text dark:text-white mb-2">Sign in to view analytics</h2>
          <p className="text-brand-text/70 dark:text-gray-400">
            Connect your account to see detailed usage analytics and insights.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-brand-text dark:text-white mb-2">Usage Analytics</h1>
          <p className="text-brand-text/70 dark:text-gray-400">
            Track your platform usage and performance metrics
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value as 'day' | 'week' | 'month')}
            className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm text-brand-text dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-primary"
          >
            <option value="day">Last 24 Hours</option>
            <option value="week">Last 7 Days</option>
            <option value="month">Last 30 Days</option>
          </select>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-brand-primary" />
        </div>
      ) : (
        <>
          {/* Key Metrics Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <MetricCard
              title="Total Emails"
              value={totalEmails.toLocaleString()}
              change={emailData.growth_rate}
              icon={<Mail className="h-5 w-5 text-brand-primary" />}
              subtitle={`${unreadEmails} unread`}
            />
            <MetricCard
              title="AI Responses"
              value={aiResponses.toLocaleString()}
              change={aiData.growth_rate}
              icon={<Brain className="h-5 w-5 text-brand-primary" />}
              subtitle={aiData.avg_response_time ? `${aiData.avg_response_time}s avg` : undefined}
            />
            <MetricCard
              title="Total Leads"
              value={totalLeads.toLocaleString()}
              change={metrics.leads?.growth_rate}
              icon={<Users className="h-5 w-5 text-brand-primary" />}
              subtitle={metrics.leads?.recent ? `${metrics.leads.recent} recent` : undefined}
            />
            <MetricCard
              title="Active Automations"
              value={activeAutomations.toLocaleString()}
              change={metrics.automation?.growth_rate}
              icon={<Zap className="h-5 w-5 text-brand-primary" />}
              subtitle={metrics.automation?.automations_executed_today ? `${metrics.automation.automations_executed_today} today` : undefined}
            />
          </div>

          {/* Detailed Sections */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Email Activity */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2 mb-4">
                <Mail className="h-5 w-5 text-brand-primary" />
                <h2 className="text-xl font-semibold text-brand-text dark:text-white">Email Activity</h2>
              </div>
              <div className="space-y-4">
                <div className="flex items-center justify-between py-2 border-b border-gray-200 dark:border-gray-700">
                  <span className="text-sm text-brand-text/70 dark:text-gray-400">Total Emails</span>
                  <span className="font-semibold text-brand-text dark:text-white">{totalEmails.toLocaleString()}</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-gray-200 dark:border-gray-700">
                  <span className="text-sm text-brand-text/70 dark:text-gray-400">Unread</span>
                  <span className="font-semibold text-brand-text dark:text-white">{unreadEmails.toLocaleString()}</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-gray-200 dark:border-gray-700">
                  <span className="text-sm text-brand-text/70 dark:text-gray-400">Emails Today</span>
                  <span className="font-semibold text-brand-text dark:text-white">
                    {emailData.emails_today || metrics.email?.emails_today || 0}
                  </span>
                </div>
                {emailData.last_email || metrics.email?.last_email ? (
                  <div className="flex items-center justify-between py-2">
                    <span className="text-sm text-brand-text/70 dark:text-gray-400">Last Email</span>
                    <span className="text-xs text-brand-text/60 dark:text-gray-500">
                      {new Date(emailData.last_email || metrics.email?.last_email).toLocaleDateString()}
                    </span>
                  </div>
                ) : null}
              </div>
            </div>

            {/* AI Usage */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2 mb-4">
                <Brain className="h-5 w-5 text-brand-primary" />
                <h2 className="text-xl font-semibold text-brand-text dark:text-white">AI Usage</h2>
              </div>
              <div className="space-y-4">
                <div className="flex items-center justify-between py-2 border-b border-gray-200 dark:border-gray-700">
                  <span className="text-sm text-brand-text/70 dark:text-gray-400">Total Responses</span>
                  <span className="font-semibold text-brand-text dark:text-white">{aiResponses.toLocaleString()}</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-gray-200 dark:border-gray-700">
                  <span className="text-sm text-brand-text/70 dark:text-gray-400">Avg Response Time</span>
                  <span className="font-semibold text-brand-text dark:text-white">
                    {aiData.avg_response_time ? `${aiData.avg_response_time}s` : 'N/A'}
                  </span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-gray-200 dark:border-gray-700">
                  <span className="text-sm text-brand-text/70 dark:text-gray-400">Success Rate</span>
                  <span className="font-semibold text-brand-text dark:text-white">
                    {aiData.success_rate ? `${aiData.success_rate}%` : 'N/A'}
                  </span>
                </div>
                {aiData.last_used ? (
                  <div className="flex items-center justify-between py-2">
                    <span className="text-sm text-brand-text/70 dark:text-gray-400">Last Used</span>
                    <span className="text-xs text-brand-text/60 dark:text-gray-500">
                      {new Date(aiData.last_used).toLocaleDateString()}
                    </span>
                  </div>
                ) : null}
              </div>
            </div>
          </div>

          {/* Insights & Recommendations */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* What's Working Well */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2 mb-4">
                <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
                <h2 className="text-xl font-semibold text-brand-text dark:text-white">What's Working Well</h2>
              </div>
              <div className="space-y-3">
                {aiResponses > 0 && (
                  <div className="flex items-start gap-3 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                    <Brain className="h-4 w-4 text-green-600 dark:text-green-400 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-brand-text dark:text-white">
                        AI is helping with {aiResponses} responses
                      </p>
                      <p className="text-xs text-brand-text/60 dark:text-gray-400 mt-0.5">
                        Your AI assistant is actively generating replies and analyzing emails
                      </p>
                    </div>
                  </div>
                )}
                {activeAutomations > 0 && (
                  <div className="flex items-start gap-3 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                    <Zap className="h-4 w-4 text-green-600 dark:text-green-400 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-brand-text dark:text-white">
                        {activeAutomations} automations are running
                      </p>
                      <p className="text-xs text-brand-text/60 dark:text-gray-400 mt-0.5">
                        Automated workflows are saving you time
                      </p>
                    </div>
                  </div>
                )}
                {totalLeads > 0 && (
                  <div className="flex items-start gap-3 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                    <Users className="h-4 w-4 text-green-600 dark:text-green-400 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-brand-text dark:text-white">
                        {totalLeads} leads in your pipeline
                      </p>
                      <p className="text-xs text-brand-text/60 dark:text-gray-400 mt-0.5">
                        Your CRM is tracking potential customers
                      </p>
                    </div>
                  </div>
                )}
                {metrics.integrations?.gmail_connected && (
                  <div className="flex items-start gap-3 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                    <Mail className="h-4 w-4 text-green-600 dark:text-green-400 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-brand-text dark:text-white">
                        Gmail is connected
                      </p>
                      <p className="text-xs text-brand-text/60 dark:text-gray-400 mt-0.5">
                        Your email integration is active and syncing
                      </p>
                    </div>
                  </div>
                )}
                {aiResponses === 0 && activeAutomations === 0 && totalLeads === 0 && !metrics.integrations?.gmail_connected && (
                  <p className="text-sm text-brand-text/60 dark:text-gray-400 italic">
                    Start using features to see what's working well
                  </p>
                )}
              </div>
            </div>

            {/* Areas Needing Attention */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2 mb-4">
                <AlertCircle className="h-5 w-5 text-orange-600 dark:text-orange-400" />
                <h2 className="text-xl font-semibold text-brand-text dark:text-white">Areas Needing Attention</h2>
              </div>
              <div className="space-y-3">
                {!metrics.integrations?.gmail_connected && (
                  <div className="flex items-start gap-3 p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                    <Mail className="h-4 w-4 text-orange-600 dark:text-orange-400 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-brand-text dark:text-white">
                        Connect Gmail to get started
                      </p>
                      <p className="text-xs text-brand-text/60 dark:text-gray-400 mt-0.5">
                        Link your email account to enable email automation
                      </p>
                      <a 
                        href="/integrations/gmail" 
                        className="text-xs text-brand-primary hover:underline mt-1 inline-flex items-center gap-1"
                      >
                        Connect now <ArrowRight className="h-3 w-3" />
                      </a>
                    </div>
                  </div>
                )}
                {unreadEmails > 10 && (
                  <div className="flex items-start gap-3 p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                    <Mail className="h-4 w-4 text-orange-600 dark:text-orange-400 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-brand-text dark:text-white">
                        {unreadEmails} unread emails
                      </p>
                      <p className="text-xs text-brand-text/60 dark:text-gray-400 mt-0.5">
                        Consider using AI to help prioritize and respond
                      </p>
                      <a 
                        href="/inbox" 
                        className="text-xs text-brand-primary hover:underline mt-1 inline-flex items-center gap-1"
                      >
                        Review inbox <ArrowRight className="h-3 w-3" />
                      </a>
                    </div>
                  </div>
                )}
                {activeAutomations === 0 && metrics.integrations?.gmail_connected && (
                  <div className="flex items-start gap-3 p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                    <Zap className="h-4 w-4 text-orange-600 dark:text-orange-400 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-brand-text dark:text-white">
                        No automations set up
                      </p>
                      <p className="text-xs text-brand-text/60 dark:text-gray-400 mt-0.5">
                        Create automations to save time on repetitive tasks
                      </p>
                      <a 
                        href="/automations" 
                        className="text-xs text-brand-primary hover:underline mt-1 inline-flex items-center gap-1"
                      >
                        Set up automations <ArrowRight className="h-3 w-3" />
                      </a>
                    </div>
                  </div>
                )}
                {aiResponses === 0 && metrics.integrations?.gmail_connected && (
                  <div className="flex items-start gap-3 p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                    <Brain className="h-4 w-4 text-orange-600 dark:text-orange-400 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-brand-text dark:text-white">
                        AI assistant not used yet
                      </p>
                      <p className="text-xs text-brand-text/60 dark:text-gray-400 mt-0.5">
                        Try analyzing emails or generating replies to see AI in action
                      </p>
                      <a 
                        href="/inbox" 
                        className="text-xs text-brand-primary hover:underline mt-1 inline-flex items-center gap-1"
                      >
                        Try AI features <ArrowRight className="h-3 w-3" />
                      </a>
                    </div>
                  </div>
                )}
                {totalLeads === 0 && metrics.integrations?.gmail_connected && (
                  <div className="flex items-start gap-3 p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                    <Users className="h-4 w-4 text-orange-600 dark:text-orange-400 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-brand-text dark:text-white">
                        No leads tracked yet
                      </p>
                      <p className="text-xs text-brand-text/60 dark:text-gray-400 mt-0.5">
                        Start tracking potential customers in your CRM
                      </p>
                      <a 
                        href="/crm" 
                        className="text-xs text-brand-primary hover:underline mt-1 inline-flex items-center gap-1"
                      >
                        View CRM <ArrowRight className="h-3 w-3" />
                      </a>
                    </div>
                  </div>
                )}
                {metrics.integrations?.gmail_connected && unreadEmails <= 10 && activeAutomations > 0 && aiResponses > 0 && totalLeads > 0 && (
                  <div className="flex items-start gap-3 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                    <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-brand-text dark:text-white">
                        Everything looks great!
                      </p>
                      <p className="text-xs text-brand-text/60 dark:text-gray-400 mt-0.5">
                        You're making good use of all features
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Quick Insights */}
          <div className="bg-gradient-to-r from-brand-primary/10 to-brand-secondary/10 dark:from-brand-primary/20 dark:to-brand-secondary/20 rounded-lg shadow-md p-6 border border-brand-primary/20 dark:border-brand-primary/30">
            <div className="flex items-start gap-3">
              <Lightbulb className="h-5 w-5 text-brand-primary mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-2">Quick Insights</h3>
                <div className="space-y-2 text-sm text-brand-text/80 dark:text-gray-300">
                  {totalEmails > 0 && (
                    <p>
                      • You've received <strong>{totalEmails}</strong> emails total
                      {unreadEmails > 0 && `, with ${unreadEmails} still unread`}
                    </p>
                  )}
                  {aiResponses > 0 && (
                    <p>
                      • AI has generated <strong>{aiResponses}</strong> responses, saving you time on email management
                    </p>
                  )}
                  {activeAutomations > 0 && (
                    <p>
                      • <strong>{activeAutomations}</strong> automations are running, handling repetitive tasks automatically
                    </p>
                  )}
                  {totalLeads > 0 && (
                    <p>
                      • You're tracking <strong>{totalLeads}</strong> leads in your CRM pipeline
                    </p>
                  )}
                  {totalEmails === 0 && aiResponses === 0 && activeAutomations === 0 && totalLeads === 0 && (
                    <p>
                      • Connect your Gmail account and start using features to see insights here
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* System Status */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-2 mb-4">
              <Activity className="h-5 w-5 text-brand-primary" />
              <h2 className="text-xl font-semibold text-brand-text dark:text-white">System Status</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="flex items-center gap-3 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <div className={`p-2 rounded-lg ${metrics.integrations?.gmail_connected ? 'bg-green-100 dark:bg-green-900/30' : 'bg-gray-100 dark:bg-gray-600'}`}>
                  <Mail className={`h-4 w-4 ${metrics.integrations?.gmail_connected ? 'text-green-600 dark:text-green-400' : 'text-gray-400'}`} />
                </div>
                <div>
                  <p className="text-xs text-brand-text/60 dark:text-gray-400">Gmail</p>
                  <p className="text-sm font-semibold text-brand-text dark:text-white">
                    {metrics.integrations?.gmail_connected ? 'Connected' : 'Not Connected'}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <div className={`p-2 rounded-lg ${metrics.performance?.uptime ? 'bg-green-100 dark:bg-green-900/30' : 'bg-gray-100 dark:bg-gray-600'}`}>
                  <Activity className={`h-4 w-4 ${metrics.performance?.uptime ? 'text-green-600 dark:text-green-400' : 'text-gray-400'}`} />
                </div>
                <div>
                  <p className="text-xs text-brand-text/60 dark:text-gray-400">Uptime</p>
                  <p className="text-sm font-semibold text-brand-text dark:text-white">
                    {metrics.performance?.uptime || 'N/A'}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30">
                  <Clock className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <p className="text-xs text-brand-text/60 dark:text-gray-400">Response Time</p>
                  <p className="text-sm font-semibold text-brand-text dark:text-white">
                    {metrics.performance?.response_time || 'N/A'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

