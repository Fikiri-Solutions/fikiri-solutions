import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Mail, Users, Zap, TrendingUp, CheckCircle, AlertCircle, 
  ArrowRight, Clock, Target, BarChart3, Sparkles, Rocket
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/Button'
import { Badge } from './ui/badge'
import { apiClient } from '../services/apiClient'
import { useAuth } from '../contexts/AuthContext'

interface HealthCheckResult {
  category: string
  score: number
  status: 'excellent' | 'good' | 'needs_improvement' | 'critical'
  issues: string[]
  recommendations: string[]
  priority: 'high' | 'medium' | 'low'
}

export const GettingStartedWizard: React.FC<{ onComplete?: () => void }> = ({ onComplete }) => {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [step, setStep] = useState(1)
  const [healthCheck, setHealthCheck] = useState<HealthCheckResult[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [gmailConnected, setGmailConnected] = useState(false)
  const [leadsCount, setLeadsCount] = useState(0)
  const [emailsProcessed, setEmailsProcessed] = useState(0)
  const [showDebugData, setShowDebugData] = useState(false)
  const [debugData, setDebugData] = useState<any>(null)

  useEffect(() => {
    loadBusinessHealth()
  }, [])

  const loadBusinessHealth = async () => {
    setIsLoading(true)
    let gmailStatus = { connected: false }
    let leadsData: any[] = []
    let totalEmails = 0
    let automationsActive = 0
    const debugInfo: any = {
      timestamp: new Date().toISOString(),
      gmail: { raw: null, error: null },
      leads: { raw: null, error: null },
      emails: { raw: null, error: null },
      automations: { raw: null, error: null }
    }

    try {
      // Check Gmail connection
      try {
        gmailStatus = await apiClient.getGmailConnectionStatus()
        debugInfo.gmail.raw = gmailStatus
        setGmailConnected(gmailStatus?.connected || false)
      } catch (error: any) {
        debugInfo.gmail.error = error?.message || 'Unknown error'
        setGmailConnected(false)
      }

      // Get leads count
      try {
        const leads = await apiClient.getLeads()
        leadsData = Array.isArray(leads) ? leads : (leads as { data?: unknown[] })?.data ?? []
        debugInfo.leads.raw = leads
        setLeadsCount(Array.isArray(leadsData) ? leadsData.length : 0)
      } catch (error: any) {
        debugInfo.leads.error = error?.message || 'Unknown error'
        setLeadsCount(0)
      }

      // Get dashboard data for email count
      try {
        const userId = user?.id || 1
        const dashboardData = await apiClient.getDashboardTimeseries(userId)
        debugInfo.emails.raw = dashboardData
        const timeseries = dashboardData?.data?.timeseries || dashboardData?.timeseries || []
        totalEmails = Array.isArray(timeseries) 
          ? timeseries.reduce((sum: number, day: any) => sum + (day.emails || 0), 0) 
          : 0
        setEmailsProcessed(totalEmails)
      } catch (error: any) {
        debugInfo.emails.error = error?.message || 'Unknown error'
        setEmailsProcessed(0)
      }

      // Get automations count
      try {
        const automations = await apiClient.getAutomationRules()
        const activeAutomations = Array.isArray(automations) 
          ? automations.filter((rule: any) => rule.status === 'active' || rule.enabled === true).length
          : 0
        automationsActive = activeAutomations
        debugInfo.automations.raw = automations
      } catch (error: any) {
        debugInfo.automations.error = error?.message || 'Unknown error'
        automationsActive = 0
      }
      
      // Store debug data
      debugInfo.calculated = {
        gmailConnected: gmailStatus?.connected || false,
        leadsCount: Array.isArray(leadsData) ? leadsData.length : 0,
        emailsProcessed: totalEmails,
        automationsActive: automationsActive
      }
      setDebugData(debugInfo)

      // Perform health check with collected data
      const healthResults = performHealthCheck({
        gmailConnected: gmailStatus?.connected || false,
        leadsCount: Array.isArray(leadsData) ? leadsData.length : 0,
        emailsProcessed: totalEmails,
        automationsActive: automationsActive,
        responseTime: null // TODO: Calculate from data
      })
      setHealthCheck(healthResults)
    } catch (error) {
      console.error('Error loading business health:', error)
      // Set default health check if everything fails
      setHealthCheck([{
        category: 'System Status',
        score: 0,
        status: 'critical',
        issues: ['Unable to load business health data'],
        recommendations: ['Please refresh the page or contact support'],
        priority: 'high'
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const performHealthCheck = (data: {
    gmailConnected: boolean
    leadsCount: number
    emailsProcessed: number
    automationsActive: number
    responseTime: number | null
  }): HealthCheckResult[] => {
    const results: HealthCheckResult[] = []

    // Email Connection Health
    if (!data.gmailConnected) {
      results.push({
        category: 'Email Integration',
        score: 0,
        status: 'critical',
        issues: ['No email account connected', 'Missing automation foundation'],
        recommendations: [
          'Connect your Gmail, iCloud, or Outlook account',
          'This is the first step to automating your business'
        ],
        priority: 'high'
      })
    } else {
      results.push({
        category: 'Email Integration',
        score: 100,
        status: 'excellent',
        issues: [],
        recommendations: ['Keep your email connected for continuous automation'],
        priority: 'low'
      })
    }

    // Lead Management Health
    if (data.leadsCount === 0) {
      results.push({
        category: 'Lead Management',
        score: 0,
        status: 'critical',
        issues: ['No leads in your CRM', 'Missing growth pipeline'],
        recommendations: [
          'Connect your email to automatically capture leads',
          'Or manually add your first lead to get started',
          'Review your CRM dashboard to track progress'
        ],
        priority: 'high'
      })
    } else if (data.leadsCount < 10) {
      results.push({
        category: 'Lead Management',
        score: 50,
        status: 'needs_improvement',
        issues: ['Low lead count', 'Limited pipeline'],
        recommendations: [
          'Focus on lead generation strategies',
          'Review your email automation to capture more leads',
          'Set up lead scoring to prioritize opportunities'
        ],
        priority: 'medium'
      })
    } else {
      results.push({
        category: 'Lead Management',
        score: 100,
        status: 'excellent',
        issues: [],
        recommendations: ['Continue nurturing your leads', 'Focus on conversion optimization'],
        priority: 'low'
      })
    }

    // Email Processing Health
    if (data.emailsProcessed === 0) {
      results.push({
        category: 'Email Automation',
        score: 0,
        status: 'critical',
        issues: ['No emails processed yet', 'Automation not active'],
        recommendations: [
          'Wait for emails to sync (usually takes a few minutes)',
          'Check your email connection status',
          'Review automation settings'
        ],
        priority: 'high'
      })
    } else if (data.emailsProcessed < 10) {
      results.push({
        category: 'Email Automation',
        score: 40,
        status: 'needs_improvement',
        issues: ['Low email volume', 'Limited automation activity'],
        recommendations: [
          'Give it time - emails sync automatically',
          'Check your email filters and settings',
          'Review automation logs for issues'
        ],
        priority: 'medium'
      })
    } else {
      results.push({
        category: 'Email Automation',
        score: 100,
        status: 'excellent',
        issues: [],
        recommendations: ['Your email automation is working well!', 'Consider setting up more advanced automations'],
        priority: 'low'
      })
    }

    // Automation Health
    if (data.automationsActive === 0) {
      results.push({
        category: 'Workflow Automation',
        score: 0,
        status: 'critical',
        issues: ['No automations active', 'Missing time-saving workflows'],
        recommendations: [
          'Visit the Automations page to set up your first workflow',
          'Start with "Gmail to CRM Sync" to automatically capture leads',
          'Enable "Lead Scoring" to prioritize opportunities'
        ],
        priority: 'high'
      })
    } else {
      results.push({
        category: 'Workflow Automation',
        score: 80,
        status: 'good',
        issues: [],
        recommendations: ['Consider adding more automations', 'Review automation performance'],
        priority: 'low'
      })
    }

    return results
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'excellent': return 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300'
      case 'good': return 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300'
      case 'needs_improvement': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300'
      case 'critical': return 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-300'
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'excellent': return <CheckCircle className="h-5 w-5 text-green-600" />
      case 'good': return <CheckCircle className="h-5 w-5 text-blue-600" />
      case 'needs_improvement': return <AlertCircle className="h-5 w-5 text-yellow-600" />
      case 'critical': return <AlertCircle className="h-5 w-5 text-red-600" />
      default: return <AlertCircle className="h-5 w-5 text-gray-600 dark:text-gray-400" />
    }
  }

  const getPriorityActions = () => {
    return healthCheck
      .filter(result => result.priority === 'high' && result.status !== 'excellent')
      .sort((a, b) => {
        const statusOrder = { critical: 0, needs_improvement: 1, good: 2, excellent: 3 }
        return statusOrder[a.status] - statusOrder[b.status]
      })
  }

  if (step === 1) {
    return (
      <Card className="max-w-4xl mx-auto">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="p-3 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
              <Rocket className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <CardTitle className="text-2xl">Welcome to Fikiri Solutions!</CardTitle>
              <p className="text-gray-600 dark:text-gray-400 mt-1">
                Let's get your business set up for success
              </p>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-6 border border-blue-200 dark:border-blue-800">
            <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-3 flex items-center gap-2">
              <Target className="h-5 w-5" />
              Your Journey Starts Here
            </h3>
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold">1</div>
                <div>
                  <h4 className="font-medium text-blue-900 dark:text-blue-100">Connect Your Email</h4>
                  <p className="text-sm text-blue-800 dark:text-blue-200 mt-1">
                    Connect Gmail, iCloud, or Outlook to start automating your email workflow
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold">2</div>
                <div>
                  <h4 className="font-medium text-blue-900 dark:text-blue-100">Review Your Business Health</h4>
                  <p className="text-sm text-blue-800 dark:text-blue-200 mt-1">
                    We'll analyze your current setup and identify areas for improvement
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold">3</div>
                <div>
                  <h4 className="font-medium text-blue-900 dark:text-blue-100">Take Action</h4>
                  <p className="text-sm text-blue-800 dark:text-blue-200 mt-1">
                    Follow our recommendations to level up your business
                  </p>
                </div>
              </div>
            </div>
          </div>

          <Button 
            onClick={() => setStep(2)} 
            className="w-full"
            size="lg"
          >
            Start Your Business Health Check
            <ArrowRight className="ml-2 h-5 w-5" />
          </Button>
        </CardContent>
      </Card>
    )
  }

  if (step === 2) {
    const priorityActions = getPriorityActions()

    return (
      <Card className="max-w-4xl mx-auto">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-purple-100 dark:bg-purple-900/20 rounded-lg">
                <BarChart3 className="h-6 w-6 text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <CardTitle className="text-2xl">Your Business Health Check</CardTitle>
                <p className="text-gray-600 dark:text-gray-400 mt-1">
                  Here's where your business stands and what to focus on
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" onClick={() => loadBusinessHealth()}>
                <Clock className="h-4 w-4 mr-2" />
                Refresh Data
              </Button>
              <Button variant="outline" onClick={() => setShowDebugData(!showDebugData)}>
                {showDebugData ? 'Hide' : 'Show'} Debug Info
              </Button>
              <Button variant="outline" onClick={() => setStep(1)}>
                Back
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {showDebugData && debugData && (
            <div className="bg-gray-100 dark:bg-gray-800 rounded-lg p-4 space-y-3">
              <div className="font-bold mb-2 text-sm">Data Sources & Values:</div>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <div className="font-semibold text-gray-700 dark:text-gray-300">Gmail Connection:</div>
                  <div className="text-gray-600 dark:text-gray-400">
                    {debugData.gmail.error ? (
                      <span className="text-red-600">Error: {debugData.gmail.error}</span>
                    ) : (
                      <span className={debugData.calculated.gmailConnected ? 'text-green-600' : 'text-red-600'}>
                        {debugData.calculated.gmailConnected ? '✅ Connected' : '❌ Not Connected'}
                      </span>
                    )}
                  </div>
                  {debugData.gmail.raw && (
                    <div className="text-gray-500 dark:text-gray-500 mt-1">
                      API: {JSON.stringify(debugData.gmail.raw).substring(0, 100)}...
                    </div>
                  )}
                </div>
                <div>
                  <div className="font-semibold text-gray-700 dark:text-gray-300">Leads Count:</div>
                  <div className="text-gray-600 dark:text-gray-400">
                    {debugData.leads.error ? (
                      <span className="text-red-600">Error: {debugData.leads.error}</span>
                    ) : (
                      <span>{debugData.calculated.leadsCount} leads found</span>
                    )}
                  </div>
                  {debugData.leads.raw && (
                    <div className="text-gray-500 dark:text-gray-500 mt-1">
                      API: {Array.isArray(debugData.leads.raw) ? `${debugData.leads.raw.length} items` : 'Object'}
                    </div>
                  )}
                </div>
                <div>
                  <div className="font-semibold text-gray-700 dark:text-gray-300">Emails Processed:</div>
                  <div className="text-gray-600 dark:text-gray-400">
                    {debugData.emails.error ? (
                      <span className="text-red-600">Error: {debugData.emails.error}</span>
                    ) : (
                      <span>{debugData.calculated.emailsProcessed} emails</span>
                    )}
                  </div>
                  {debugData.emails.raw && (
                    <div className="text-gray-500 dark:text-gray-500 mt-1">
                      API: {JSON.stringify(debugData.emails.raw).substring(0, 100)}...
                    </div>
                  )}
                </div>
                <div>
                  <div className="font-semibold text-gray-700 dark:text-gray-300">Automations:</div>
                  <div className="text-gray-600 dark:text-gray-400">
                    {debugData.calculated.automationsActive} active (TODO: fetch from API)
                  </div>
                </div>
              </div>
              <details className="mt-3">
                <summary className="cursor-pointer text-xs font-semibold text-gray-600 dark:text-gray-400">
                  View Full Raw Data (JSON)
                </summary>
                <pre className="mt-2 text-xs font-mono overflow-auto max-h-64 bg-gray-200 dark:bg-gray-900 p-2 rounded">
                  {JSON.stringify(debugData, null, 2)}
                </pre>
              </details>
              <div className="text-xs text-gray-500 dark:text-gray-500 mt-2">
                <strong>Data Sources:</strong> Gmail status from <code>/api/auth/gmail/status</code>, 
                Leads from <code>/api/crm/leads</code>, 
                Emails from <code>/api/dashboard/timeseries</code>,
                Automations from <code>/api/automation/rules</code>
              </div>
            </div>
          )}
          {isLoading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-600 dark:text-gray-400">Analyzing your business...</p>
            </div>
          ) : (
            <>
              {/* Priority Actions */}
              {priorityActions.length > 0 && (
                <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-6 border border-red-200 dark:border-red-800">
                  <h3 className="font-semibold text-red-900 dark:text-red-100 mb-4 flex items-center gap-2">
                    <AlertCircle className="h-5 w-5" />
                    Start Here: Priority Actions
                  </h3>
                  <div className="space-y-4">
                    {priorityActions.map((result, idx) => (
                      <div key={idx} className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-red-200 dark:border-red-800">
                        <div className="flex items-start justify-between mb-3">
                          <h4 className="font-semibold text-red-900 dark:text-red-100">{result.category}</h4>
                          <Badge className={getStatusColor(result.status)}>
                            {result.status.replace('_', ' ')}
                          </Badge>
                        </div>
                        {result.issues.length > 0 && (
                          <div className="mb-3">
                            <p className="text-sm font-medium text-red-800 dark:text-red-200 mb-2">Issues:</p>
                            <ul className="list-disc list-inside text-sm text-red-700 dark:text-red-300 space-y-1">
                              {result.issues.map((issue, i) => (
                                <li key={i}>{issue}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        <div>
                          <p className="text-sm font-medium text-red-800 dark:text-red-200 mb-2">What to do:</p>
                          <ul className="list-disc list-inside text-sm text-red-700 dark:text-red-300 space-y-1">
                            {result.recommendations.map((rec, i) => (
                              <li key={i}>{rec}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* All Health Checks */}
              <div>
                <h3 className="font-semibold text-gray-900 dark:text-white mb-4">Complete Health Overview</h3>
                <div className="grid gap-4">
                  {healthCheck.map((result, idx) => (
                    <div key={idx} className="border rounded-lg p-4 bg-white dark:bg-gray-800">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-3">
                          {getStatusIcon(result.status)}
                          <div>
                            <h4 className="font-semibold text-gray-900 dark:text-white">{result.category}</h4>
                            <p className="text-sm text-gray-600 dark:text-gray-400">
                              Score: {result.score}/100
                            </p>
                          </div>
                        </div>
                        <Badge className={getStatusColor(result.status)}>
                          {result.status.replace('_', ' ')}
                        </Badge>
                      </div>
                      
                      {result.issues.length > 0 && (
                        <div className="mb-3">
                          <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Issues Found:</p>
                          <ul className="list-disc list-inside text-xs text-gray-600 dark:text-gray-400 space-y-1">
                            {result.issues.map((issue, i) => (
                              <li key={i}>{issue}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {result.recommendations.length > 0 && (
                        <div>
                          <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Recommendations:</p>
                          <ul className="list-disc list-inside text-xs text-gray-600 dark:text-gray-400 space-y-1">
                            {result.recommendations.map((rec, i) => (
                              <li key={i}>{rec}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Next Steps */}
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-lg p-6 border border-blue-200 dark:border-blue-800">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-purple-600" />
                  Your Next Steps
                </h3>
                <div className="space-y-3">
                  {!gmailConnected && (
                    <Button 
                      onClick={() => navigate('/integrations/gmail')}
                      className="w-full justify-start"
                      variant="outline"
                    >
                      <Mail className="mr-2 h-4 w-4" />
                      Connect Your Email Account
                    </Button>
                  )}
                  {gmailConnected && leadsCount === 0 && (
                    <Button 
                      onClick={() => navigate('/crm')}
                      className="w-full justify-start"
                      variant="outline"
                    >
                      <Users className="mr-2 h-4 w-4" />
                      View Your CRM and Add Leads
                    </Button>
                  )}
                  <Button 
                    onClick={() => navigate('/automations')}
                    className="w-full justify-start"
                    variant="outline"
                  >
                    <Zap className="mr-2 h-4 w-4" />
                    Set Up Your First Automation
                  </Button>
                  <Button 
                    onClick={() => {
                      navigate('/dashboard')
                      onComplete?.()
                    }}
                    className="w-full justify-start"
                  >
                    <TrendingUp className="mr-2 h-4 w-4" />
                    Go to Dashboard
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    )
  }

  return null
}

