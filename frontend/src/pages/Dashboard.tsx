import React, { useState, Suspense } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Mail, Users, Brain, Bot, UserPlus, Zap, AlertTriangle, CheckCircle2, XCircle, AlertCircle, DollarSign, TrendingUp } from 'lucide-react'
import { ServiceCard } from '../components/ServiceCard'
import { MetricCard } from '../components/MetricCard'
import { MiniTrend } from '../components/MiniTrend'
import { MetricCardSkeleton, ServiceCardSkeleton, ChartSkeleton, ActivitySkeleton } from '../components/Skeleton'
import { useToast } from '../components/Toast'
import { useWebSocket } from '../hooks/useWebSocket'
import { useDashboardTimeseries } from '../hooks/useDashboardTimeseries'
import { useDashboardView } from '../hooks/useDashboardView'
import { config, getFeatureConfig } from '../config'
import { apiClient } from '../services/apiClient'
import { mockServices, mockMetrics, mockActivity } from '../mockData'

// Lazy load heavy dashboard components
const EnhancedDashboard = React.lazy(() => import('./EnhancedDashboard').then(module => ({ default: module.EnhancedDashboard })))
const CompactDashboard = React.lazy(() => import('./CompactDashboard').then(module => ({ default: module.CompactDashboard })))
const DashboardCharts = React.lazy(() => import('../components/DashboardCharts').then(module => ({ default: module.DashboardCharts })))

export const Dashboard: React.FC = () => {
  const navigate = useNavigate()
  const features = getFeatureConfig()
  const { addToast } = useToast()
  const { isConnected, data, requestMetricsUpdate, requestServicesUpdate } = useWebSocket()
  const { data: timeseriesData, summary, loading: timeseriesLoading } = useDashboardTimeseries()
  
  // Use dashboard view hook for persistence
  const { dashboardView, setDashboardView, isEnhanced, isCompact, isOriginal } = useDashboardView()
  
  // Render different dashboard views with Suspense
  if (dashboardView === 'enhanced') {
    console.log('Rendering EnhancedDashboard')
    return (
      <Suspense fallback={<ChartSkeleton />}>
        <EnhancedDashboard />
      </Suspense>
    )
  }
  
  if (dashboardView === 'compact') {
    console.log('Rendering CompactDashboard')
    return (
      <Suspense fallback={<ChartSkeleton />}>
        <CompactDashboard />
      </Suspense>
    )
  }
  
  console.log('Rendering original dashboard')

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

  const { data: metricsData = mockMetrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['metrics'],
    queryFn: () => features.useMockData ? Promise.resolve(mockMetrics) : apiClient.getMetrics(),
    staleTime: 0,
    enabled: true,
  })

  const { data: activityData = mockActivity, isLoading: activityLoading } = useQuery({
    queryKey: ['activity'],
    queryFn: () => features.useMockData ? Promise.resolve(mockActivity) : apiClient.getActivity(),
    staleTime: 0,
    enabled: true,
  })

  // Combine API data with real-time WebSocket updates
  const services = data.services?.services || servicesData
  const metrics = data.metrics || metricsData
  const activity = data.activity ? [data.activity, ...activityData] : activityData

  // Generate dynamic chart data
  const generateChartData = () => {
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
      revenue: item.revenue || 0,
      value: (item.leads || 0) + (item.emails || 0) + (item.revenue || 0) / 100 // Combined value for pie charts
    }))
  }

  // Transform timeseries data for pie charts
  const transformForPieChart = (data: any[]) => {
    if (!data || data.length === 0) return []
    
    const totals = data.reduce((acc, item) => ({
      leads: acc.leads + (item.leads || 0),
      emails: acc.emails + (item.emails || 0),
      revenue: acc.revenue + (item.revenue || 0)
    }), { leads: 0, emails: 0, revenue: 0 })

    return [
      { name: 'Leads', value: totals.leads, color: '#3b82f6' },
      { name: 'Emails', value: totals.emails, color: '#22c55e' },
      { name: 'Revenue', value: totals.revenue, color: '#f97316' }
    ].filter(item => item.value > 0)
  }

  const chartData = generateChartData()
  const transformedTimeseriesData = transformTimeseriesData(timeseriesData || [])
  const pieChartData = transformForPieChart(timeseriesData || [])

  const getActivityIcon = (type: string, status: string) => {
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
    <div className="min-h-screen bg-brand-background dark:bg-gray-900">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-brand-text dark:text-white mb-2">
            Dashboard
          </h1>
          <p className="text-brand-text/70 dark:text-gray-400">
            Welcome back! Here's what's happening with your business.
          </p>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div 
            className="bg-brand-background dark:bg-gray-800 rounded-lg shadow-md p-6 cursor-pointer hover:shadow-lg transition-all duration-200 hover:scale-105 border border-brand-text/10"
            onClick={() => navigate('/crm')}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-brand-text/70 dark:text-gray-400">Total Leads</p>
                <p className="text-2xl font-bold text-brand-text dark:text-white">1,234</p>
              </div>
              <Users className="h-8 w-8 text-brand-primary" />
            </div>
          </div>
          
          <div 
            className="bg-brand-background dark:bg-gray-800 rounded-lg shadow-md p-6 cursor-pointer hover:shadow-lg transition-all duration-200 hover:scale-105 border border-brand-text/10"
            onClick={() => navigate('/services')}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-brand-text/70 dark:text-gray-400">Emails Processed</p>
                <p className="text-2xl font-bold text-brand-text dark:text-white">5,678</p>
              </div>
              <Mail className="h-8 w-8 text-brand-secondary" />
            </div>
          </div>
          
          <div 
            className="bg-brand-background dark:bg-gray-800 rounded-lg shadow-md p-6 cursor-pointer hover:shadow-lg transition-all duration-200 hover:scale-105 border border-brand-text/10"
            onClick={() => navigate('/ai')}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-brand-text/70 dark:text-gray-400">AI Responses</p>
                <p className="text-2xl font-bold text-brand-text dark:text-white">2,345</p>
              </div>
              <Brain className="h-8 w-8 text-brand-accent" />
            </div>
          </div>
          
          <div 
            className="bg-brand-background dark:bg-gray-800 rounded-lg shadow-md p-6 cursor-pointer hover:shadow-lg transition-all duration-200 hover:scale-105 border border-brand-text/10"
            onClick={() => navigate('/industry')}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-brand-text/70 dark:text-gray-400">Revenue</p>
                <p className="text-2xl font-bold text-brand-text dark:text-white">$12,345</p>
              </div>
              <DollarSign className="h-8 w-8 text-brand-warning" />
            </div>
          </div>
        </div>

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Email Trends Chart */}
          <div className="bg-brand-background dark:bg-gray-800 rounded-lg shadow-md p-6 border border-brand-text/10">
            <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-4 flex items-center">
              <div className="w-3 h-3 bg-brand-primary rounded-full mr-2"></div>
              Email Trends
            </h3>
            <div className="h-64">
                    <Suspense fallback={<ChartSkeleton />}>
                      <DashboardCharts data={chartData} />
                    </Suspense>
            </div>
          </div>

          {/* Service Performance Chart */}
          <div className="bg-brand-background dark:bg-gray-800 rounded-lg shadow-md p-6 border border-brand-text/10">
            <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-4 flex items-center">
              <div className="w-3 h-3 bg-brand-secondary rounded-full mr-2"></div>
              Service Performance
            </h3>
            <div className="h-64">
                    <Suspense fallback={<ChartSkeleton />}>
                      <DashboardCharts data={chartData} />
                    </Suspense>
            </div>
          </div>
        </div>

        {/* Service Distribution Chart */}
        <div className="bg-brand-background dark:bg-gray-800 rounded-lg shadow-md p-6 mb-8 border border-brand-text/10">
          <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-4 flex items-center">
            <div className="w-3 h-3 bg-brand-accent rounded-full mr-2"></div>
            Service Distribution
          </h3>
          <div className="h-64">
                    <Suspense fallback={<ChartSkeleton />}>
                      <DashboardCharts data={transformedTimeseriesData} pieData={pieChartData} />
                    </Suspense>
          </div>
        </div>

        {/* Services and Activity Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Active Services */}
          <div className="bg-brand-background dark:bg-gray-800 rounded-lg shadow-md p-6 border border-brand-text/10">
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
                {services.slice(0, 3).map((service) => (
                  <ServiceCard key={service.id} service={service} />
                ))}
              </div>
            )}
          </div>

          {/* Recent Activity */}
          <div className="bg-brand-background dark:bg-gray-800 rounded-lg shadow-md p-6 border border-brand-text/10">
            <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-4">
              Recent Activity
            </h3>
            {activityLoading ? (
              <ActivitySkeleton />
            ) : (
              <div className="space-y-3">
                {activity.slice(0, 5).map((item) => (
                  <div key={item.id} className="flex items-center space-x-3">
                    {getActivityIcon(item.type, item.status)}
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
      </div>
    </div>
  )
}