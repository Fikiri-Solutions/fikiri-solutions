import React, { Suspense } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Mail, Users, Brain, UserPlus, Zap, AlertTriangle, AlertCircle, TrendingUp, CreditCard } from 'lucide-react'
import { ServiceCard } from '../components/ServiceCard'
import { EnhancedMetricCard } from '../components/EnhancedMetricCard'
import { MiniTrend } from '../components/MiniTrend'
import { MetricCardSkeleton, ServiceCardSkeleton, ChartSkeleton, ActivitySkeleton } from '../components/Skeleton'
import { GettingStartedWizard } from '../components/GettingStartedWizard'
import { useWebSocket } from '../hooks/useWebSocket'
import { useDashboardTimeseries } from '../hooks/useDashboardTimeseries'
import { getFeatureConfig } from '../config'
import { apiClient } from '../services/apiClient'
import { mockServices, mockMetrics, mockActivity } from '../mockData'

// Lazy load heavy dashboard components
const EmailTrendsChart = React.lazy(() => import('../components/EmailTrendsChart').then(module => ({ default: module.EmailTrendsChart })))
const ServicePerformanceChart = React.lazy(() => import('../components/ServicePerformanceChart').then(module => ({ default: module.ServicePerformanceChart })))
const ServiceDistributionChart = React.lazy(() => import('../components/ServiceDistributionChart').then(module => ({ default: module.ServiceDistributionChart })))

export const Dashboard: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const features = getFeatureConfig()
  const { data } = useWebSocket()
  const { data: timeseriesData, loading: timeseriesLoading } = useDashboardTimeseries()
  
  // Dashboard view selection removed - using default view only
  // Enhanced and Compact dashboard variants have been removed

  // Clear specific cache items to force fresh data
  React.useEffect(() => {
    localStorage.removeItem('hasSeenPerformanceToast')
    // Don't clear all localStorage - it breaks theme and other preferences
  }, [])

  // Handle Stripe checkout success redirect
  React.useEffect(() => {
    if (searchParams.get('success') === 'true') {
      // Show success message
      console.log('✅ Payment successful! Subscription activated.')
      // Note: Toast notifications would require importing useToast
      // For now, we'll just clean up the URL
      // Remove the success parameter from URL
      navigate('/dashboard', { replace: true })
    }
  }, [searchParams, navigate])

  // TanStack Query hooks for smart data fetching with caching and real-time updates
  const { data: servicesData = [], isLoading: servicesLoading } = useQuery({
    queryKey: ['services'],
    queryFn: () => features.useMockData ? Promise.resolve(mockServices) : apiClient.getServices(),
    staleTime: 2 * 60 * 1000, // 2 minutes - services don't change often
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchInterval: 5 * 60 * 1000, // Auto-refresh every 5 minutes
    enabled: true,
  })

  const { data: metricsData = mockMetrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['metrics'],
    queryFn: () => features.useMockData ? Promise.resolve(mockMetrics) : apiClient.getMetrics(),
    staleTime: 30 * 1000, // 30 seconds - metrics update more frequently
    gcTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 60 * 1000, // Auto-refresh every minute
    enabled: true,
  })

  const { data: activityData = mockActivity, isLoading: activityLoading } = useQuery({
    queryKey: ['activity'],
    queryFn: () => features.useMockData ? Promise.resolve(mockActivity) : apiClient.getActivity(),
    staleTime: 30 * 1000, // 30 seconds - activity updates frequently
    gcTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 60 * 1000, // Auto-refresh every minute
    enabled: true,
  })

  // Combine API data with real-time WebSocket updates
  const services = data.services?.services || servicesData
  // Use real metrics data, fallback to mock only if API fails
  const metrics = data.metrics || metricsData || mockMetrics
  const activity = data.activity ? [data.activity, ...activityData] : activityData

  // Use real timeseries data for charts, fallback to generated data if needed
  const generateChartData = () => {
    // If we have timeseries data, use it
    if (transformedTimeseriesData && transformedTimeseriesData.length > 0) {
      return transformedTimeseriesData
    }
    // Fallback: generate sample data
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    return days.map(day => ({
      name: day,
      emails: Math.floor(Math.random() * 40) + 20,
      leads: Math.floor(Math.random() * 30) + 15,
      responses: Math.floor(Math.random() * 20) + 10,
      value: Math.floor(Math.random() * 80) + 20
    }))
  }

  // Transform timeseries data for charts
  const transformTimeseriesData = (data: any[]) => {
    if (!data || data.length === 0) return []
    
    return data.map(item => ({
      name: item.day ? new Date(item.day).toLocaleDateString('en-US', { weekday: 'short' }) : item.name,
      day: item.day,
      leads: item.leads || 0,
      emails: item.emails || 0,
      responses: item.responses || item.aiResponses || 0, // Support both field names
      revenue: item.revenue || 0,
      value: (item.leads || 0) + (item.emails || 0) + (item.responses || item.aiResponses || 0) + (item.revenue || 0) / 100 // Combined value for pie charts
    }))
  }

  // Transform timeseries data for pie charts
  const transformForPieChart = (data: any[]) => {
    if (!data || data.length === 0) return []
    
    const totals = data.reduce((acc, item) => ({
      leads: acc.leads + (item.leads || 0),
      emails: acc.emails + (item.emails || 0),
      responses: acc.responses + (item.responses || item.aiResponses || 0),
      revenue: acc.revenue + (item.revenue || 0)
    }), { leads: 0, emails: 0, responses: 0, revenue: 0 })

    return [
      { name: 'Leads', value: totals.leads, color: '#3b82f6' },
      { name: 'Emails', value: totals.emails, color: '#22c55e' },
      { name: 'AI Responses', value: totals.responses, color: '#f97316' },
      { name: 'Revenue', value: totals.revenue, color: '#8b5cf6' }
    ].filter(item => item.value > 0)
  }

  const transformedTimeseriesData = transformTimeseriesData(timeseriesData || [])
  const pieChartData = transformForPieChart(timeseriesData || [])
  const chartData = transformedTimeseriesData.length > 0 ? transformedTimeseriesData : generateChartData()
  // Use fallback data for MiniTrend if timeseries data is empty
  const trendData = transformedTimeseriesData.length > 0 ? transformedTimeseriesData : generateChartData()

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'email':
        return <Mail className="h-4 w-4 text-blue-500" />
      case 'lead':
        return <UserPlus className="h-4 w-4 text-green-500" />
      case 'automation':
        return <Zap className="h-4 w-4 text-yellow-500" />
      case 'error':
        return <AlertTriangle className="h-4 w-4 text-red-500" />
      default:
        return <AlertCircle className="h-4 w-4 text-gray-500" />
    }
  }

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-brand-text dark:text-white mb-2">
              Dashboard
            </h1>
            <p className="text-brand-text/70 dark:text-gray-400">
              Welcome back! Here's what's happening with your business.
            </p>
          </div>
          <Link
            to="/billing"
            className="flex items-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors"
          >
            <CreditCard className="w-4 h-4" />
            Billing
          </Link>
        </div>

        {/* Getting Started Wizard / Health Check */}
        <div className="mb-8">
          <GettingStartedWizard />
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {metricsLoading ? (
            <>
              <MetricCardSkeleton />
              <MetricCardSkeleton />
              <MetricCardSkeleton />
              <MetricCardSkeleton />
            </>
          ) : (
            <>
              <EnhancedMetricCard
                title="Total Leads"
                value={metrics?.activeLeads || 0}
                icon={<Users className="h-5 w-5" />}
                onClick={() => navigate('/crm')}
                description="Total active leads in your CRM"
                businessImpact="More leads = More opportunities"
                color="blue"
              >
                <MiniTrend data={trendData} dataKey="leads" />
              </EnhancedMetricCard>
              
              <EnhancedMetricCard
                title="Emails Processed"
                value={metrics?.totalEmails || 0}
                icon={<Mail className="h-5 w-5" />}
                onClick={() => navigate('/inbox')}
                description="Total emails processed by the system"
                businessImpact="Automated email handling saves time"
                color="green"
              >
                <MiniTrend data={trendData} dataKey="emails" />
              </EnhancedMetricCard>
              
              <EnhancedMetricCard
                title="AI Responses"
                value={metrics?.aiResponses || 0}
                icon={<Brain className="h-5 w-5" />}
                onClick={() => navigate('/ai')}
                description="AI-generated email responses"
                businessImpact="Faster response times improve customer satisfaction"
                color="orange"
              >
                <MiniTrend data={trendData} dataKey="responses" />
              </EnhancedMetricCard>
              
              <EnhancedMetricCard
                title="Avg Response Time"
                value={`${metrics?.avgResponseTime?.toFixed(1) || 0}h`}
                icon={<TrendingUp className="h-5 w-5" />}
                onClick={() => navigate('/services')}
                description="Average time to respond to leads"
                businessImpact="Faster responses = Higher conversion rates"
                color="purple"
              >
                <MiniTrend data={trendData} dataKey="value" />
              </EnhancedMetricCard>
            </>
          )}
        </div>

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Email Trends Chart */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-4 flex items-center">
              <div className="w-3 h-3 bg-brand-primary rounded-full mr-2"></div>
              Email Trends
            </h3>
            <div className="h-64 min-h-[256px]">
              {timeseriesLoading ? (
                <ChartSkeleton />
              ) : (
                <Suspense fallback={<ChartSkeleton />}>
                  <EmailTrendsChart data={chartData} />
                </Suspense>
              )}
            </div>
          </div>

          {/* Service Performance Chart */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-4 flex items-center">
              <div className="w-3 h-3 bg-brand-secondary rounded-full mr-2"></div>
              Service Performance
            </h3>
            <div className="h-64 min-h-[256px]">
              {timeseriesLoading ? (
                <ChartSkeleton />
              ) : (
                <Suspense fallback={<ChartSkeleton />}>
                  <ServicePerformanceChart data={chartData} />
                </Suspense>
              )}
            </div>
          </div>
        </div>

        {/* Service Distribution Chart */}
        <div className="bg-brand-background dark:bg-gray-800 rounded-lg shadow-md p-6 mb-8 border border-brand-text/10">
          <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-4 flex items-center">
            <div className="w-3 h-3 bg-brand-accent rounded-full mr-2"></div>
            Service Distribution
          </h3>
          <div className="h-64 min-h-[256px]">
            {timeseriesLoading ? (
              <ChartSkeleton />
            ) : (
              <Suspense fallback={<ChartSkeleton />}>
                <ServiceDistributionChart data={pieChartData.length > 0 ? pieChartData : []} />
              </Suspense>
            )}
          </div>
        </div>

        {/* Services and Activity Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Active Services */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-4">
              Active Services
            </h3>
            {servicesLoading ? (
              <div className="space-y-3">
                <ServiceCardSkeleton />
                <ServiceCardSkeleton />
              </div>
            ) : (
              <div className="space-y-3">
                {services.slice(0, 3).map((service: any) => (
                  <ServiceCard key={service.id} service={service} />
                ))}
              </div>
            )}
          </div>

          {/* Recent Activity */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-4">
              Recent Activity
            </h3>
            {activityLoading ? (
              <ActivitySkeleton />
            ) : (
              <div className="space-y-3">
                {activity.slice(0, 5).map((item) => (
                  <div key={item.id} className="flex items-center space-x-3">
                    {getActivityIcon(item.type)}
                    <div className="flex-1">
                      <p className="text-sm font-medium text-brand-text dark:text-white">{item.message}</p>
                      <p className="text-xs text-brand-text/60 dark:text-gray-400">{item.timestamp}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Sentry Test Section removed - component deleted */}
      </div>
    </div>
  )
}