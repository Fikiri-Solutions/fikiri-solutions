import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Mail, Users, Brain, Clock, Bot, UserPlus, Zap, AlertTriangle, CheckCircle2, XCircle, AlertCircle } from 'lucide-react'
import { ServiceCard } from '../components/ServiceCard'
import { MetricCard } from '../components/MetricCard'
import { DashboardCharts } from '../components/DashboardCharts'
import { MetricCardSkeleton, ServiceCardSkeleton, ChartSkeleton, ActivitySkeleton } from '../components/Skeleton'
import { useToast } from '../components/Toast'
import { useWebSocket } from '../hooks/useWebSocket'
import { config, getFeatureConfig } from '../config'
import { apiClient, ServiceData, MetricData, ActivityItem } from '../services/apiClient'
import { mockServices, mockMetrics, mockActivity } from '../mockData'
import { useCacheInvalidation } from '../utils/cacheInvalidation'

export const Dashboard: React.FC = () => {
  const navigate = useNavigate()
  const features = getFeatureConfig()
  const { addToast } = useToast()
  const { isConnected, data, requestMetricsUpdate, requestServicesUpdate } = useWebSocket()
  const { getCacheHeaders } = useCacheInvalidation()

  // Clear specific cache items to force fresh data
  React.useEffect(() => {
    localStorage.removeItem('hasSeenPerformanceToast')
    // Don't clear all localStorage - it breaks theme and other preferences
  }, [])

  // TanStack Query hooks for smart data fetching with real-time updates
  const { data: servicesData = [], isLoading: servicesLoading } = useQuery({
    queryKey: ['services'],
    queryFn: () => features.useMockData ? Promise.resolve(mockServices) : apiClient.getServices(),
    staleTime: 0, // No stale time - always fetch fresh data
    enabled: true, // Always enabled for immediate loading
  })

  const { data: metricsData, isLoading: metricsLoading } = useQuery({
    queryKey: ['metrics'],
    queryFn: () => features.useMockData ? Promise.resolve(mockMetrics) : apiClient.getMetrics(),
    staleTime: 0, // No stale time - always fetch fresh data
    enabled: true, // Always enabled for immediate loading
  })

  const { data: activityData = [], isLoading: activityLoading } = useQuery({
    queryKey: ['activity'],
    queryFn: () => features.useMockData ? Promise.resolve(mockActivity) : apiClient.getActivity(),
    staleTime: 0, // No stale time - always fetch fresh data
    enabled: true, // Always enabled for immediate loading
  })

  // Combine API data with real-time WebSocket updates
  const services = data.services?.services || servicesData
  const metrics = data.metrics || metricsData
  const activity = data.activity ? [data.activity, ...activityData] : activityData

  // Request real-time updates when WebSocket connects
  React.useEffect(() => {
    if (isConnected) {
      requestMetricsUpdate()
      requestServicesUpdate()
    }
  }, [isConnected, requestMetricsUpdate, requestServicesUpdate])

  // Chart data
  const chartData = [
    { name: 'Mon', emails: 45, leads: 12, responses: 38, value: 95 },
    { name: 'Tue', emails: 52, leads: 15, responses: 42, value: 88 },
    { name: 'Wed', emails: 38, leads: 8, responses: 35, value: 92 },
    { name: 'Thu', emails: 61, leads: 18, responses: 48, value: 85 },
    { name: 'Fri', emails: 47, leads: 14, responses: 41, value: 90 },
    { name: 'Sat', emails: 23, leads: 6, responses: 22, value: 78 },
    { name: 'Sun', emails: 19, leads: 4, responses: 18, value: 82 },
  ]

  const handleMetricClick = (metricType: string) => {
    switch (metricType) {
      case 'emails':
        navigate('/crm?filter=emails')
        addToast({
          type: 'info',
          title: 'Navigating to CRM',
          message: 'Filtering by email activity'
        })
        break
      case 'leads':
        navigate('/crm?filter=active')
        addToast({
          type: 'success',
          title: 'Viewing Active Leads',
          message: 'Showing all active lead data'
        })
        break
      case 'responses':
        navigate('/services')
        addToast({
          type: 'info',
          title: 'Checking AI Responses',
          message: 'Viewing service performance'
        })
        break
      case 'responseTime':
        navigate('/services')
        addToast({
          type: 'warning',
          title: 'Response Time Analysis',
          message: 'Reviewing performance metrics'
        })
        break
      default:
        // Metric click handled
    }
  }

  const getActivityIcon = (type: string, status: string) => {
    const iconClass = `h-5 w-5 ${
      status === 'success' ? 'text-green-500' :
      status === 'warning' ? 'text-yellow-500' : 'text-red-500'
    }`

    switch (type) {
      case 'ai_response':
        return <Bot className={iconClass} />
      case 'lead_added':
        return <UserPlus className={iconClass} />
      case 'email_processed':
        return <Zap className={iconClass} />
      case 'service_error':
        return <AlertTriangle className={iconClass} />
      default:
        return status === 'success' ? <CheckCircle2 className={iconClass} /> : 
               status === 'warning' ? <AlertCircle className={iconClass} /> : 
               <XCircle className={iconClass} />
    }
  }


  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">🚀 ALL ISSUES FIXED - v1.0.6</h1>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              FIXED: Industry page working, navigation issues resolved, dark mode stable, AI Assistant with real-time capabilities. Build: 2025-09-18T01:15:00Z
            </p>
          </div>
          
          {/* Version and Connection Status */}
          <div className="flex items-center space-x-4">
            {/* Cache Version Display */}
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 rounded-full bg-blue-500"></div>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                Cache: {config.cacheVersion}
              </span>
            </div>
            
            {/* WebSocket Connection Status */}
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {isConnected ? 'Live Updates' : 'Offline'}
              </span>
            </div>
          </div>
        </div>
        
        {(servicesLoading || metricsLoading || activityLoading) && (
          <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-3">
            <div className="flex items-center space-x-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
              <p className="text-sm text-blue-600">
                <strong>Loading:</strong> Fetching latest data...
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {metricsLoading ? (
          <>
            <MetricCardSkeleton />
            <MetricCardSkeleton />
            <MetricCardSkeleton />
            <MetricCardSkeleton />
          </>
        ) : (
          <>
            <MetricCard
              title="Total Emails"
              value={metrics?.totalEmails?.toString() || '0'}
              icon={Mail}
              change="+12%"
              changeType="positive"
              onClick={() => handleMetricClick('emails')}
            />
            <MetricCard
              title="Active Leads"
              value={metrics?.activeLeads?.toString() || '0'}
              icon={Users}
              change="+8%"
              changeType="positive"
              onClick={() => handleMetricClick('leads')}
            />
            <MetricCard
              title="AI Responses"
              value={metrics?.aiResponses?.toString() || '0'}
              icon={Brain}
              change="+23%"
              changeType="positive"
              onClick={() => handleMetricClick('responses')}
            />
            <MetricCard
              title="Avg Response Time"
              value={`${Math.round((metrics?.avgResponseTime || 0) * 100) / 100}h`}
              icon={Clock}
              change="-15%"
              changeType="positive"
              onClick={() => handleMetricClick('responseTime')}
            />
          </>
        )}
      </div>

      {/* Services Status */}
      <div>
        <h2 className="text-lg font-medium text-gray-900 mb-4">Service Status</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {servicesLoading ? (
            <>
              <ServiceCardSkeleton />
              <ServiceCardSkeleton />
              <ServiceCardSkeleton />
              <ServiceCardSkeleton />
            </>
          ) : (
            services.map((service) => (
              <ServiceCard key={service.id} service={service} />
            ))
          )}
        </div>
      </div>

      {/* Professional Charts */}
      {metricsLoading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ChartSkeleton />
          <ChartSkeleton />
          <ChartSkeleton className="lg:col-span-2" />
        </div>
      ) : (
        <DashboardCharts data={chartData} />
      )}

      {/* Recent Activity */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900">Recent Activity</h3>
          {features.debugMode && (
            <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
              {features.useMockData ? 'Mock Data' : 'Live API Data'}
            </span>
          )}
        </div>
        {activityLoading ? (
          <ActivitySkeleton />
        ) : (
          <div className="space-y-3">
            {activity.map((item) => (
              <div key={item.id} className="flex items-center space-x-3">
                {getActivityIcon(item.type, item.status)}
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">{item.message}</p>
                  <p className="text-xs text-gray-500">{item.timestamp}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
