import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Mail, Users, Brain, Bot, UserPlus, Zap, AlertTriangle, CheckCircle2, XCircle, AlertCircle, DollarSign, TrendingUp } from 'lucide-react'
import { ServiceCard } from '../components/ServiceCard'
import { MetricCard } from '../components/MetricCard'
import { MiniTrend } from '../components/MiniTrend'
import { DashboardCharts } from '../components/DashboardCharts'
import { MetricCardSkeleton, ServiceCardSkeleton, ChartSkeleton, ActivitySkeleton } from '../components/Skeleton'
import { useToast } from '../components/Toast'
import { useWebSocket } from '../hooks/useWebSocket'
import { useDashboardTimeseries } from '../hooks/useDashboardTimeseries'
import { config, getFeatureConfig } from '../config'
import { apiClient } from '../services/apiClient'
import { mockServices, mockMetrics, mockActivity } from '../mockData'
import { EnhancedDashboard } from './EnhancedDashboard'
import { CompactDashboard } from './CompactDashboard'

export const Dashboard: React.FC = () => {
  const navigate = useNavigate()
  const features = getFeatureConfig()
  const { addToast } = useToast()
  const { isConnected, data, requestMetricsUpdate, requestServicesUpdate } = useWebSocket()
  const { data: timeseriesData, summary, loading: timeseriesLoading } = useDashboardTimeseries()
  
  // Dashboard view options
  const [dashboardView, setDashboardView] = useState<'enhanced' | 'compact' | 'original'>('enhanced')
  
  // Render different dashboard views
  if (dashboardView === 'enhanced') {
    console.log('Rendering EnhancedDashboard')
    try {
      return <EnhancedDashboard />
    } catch (error) {
      console.error('EnhancedDashboard failed:', error)
      // Fall through to original dashboard
    }
  }
  
  if (dashboardView === 'compact') {
    console.log('Rendering CompactDashboard')
    return <CompactDashboard />
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

  const chartData = generateChartData()

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
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Dashboard
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Welcome back! Here's what's happening with your business.
          </p>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Leads</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">1,234</p>
              </div>
              <Users className="h-8 w-8 text-blue-500" />
            </div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Emails Processed</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">5,678</p>
              </div>
              <Mail className="h-8 w-8 text-green-500" />
            </div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">AI Responses</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">2,345</p>
              </div>
              <Brain className="h-8 w-8 text-purple-500" />
            </div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Revenue</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">$12,345</p>
              </div>
              <DollarSign className="h-8 w-8 text-yellow-500" />
            </div>
          </div>
        </div>

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Email Trends Chart */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
              <div className="w-3 h-3 bg-blue-500 rounded-full mr-2"></div>
              Email Trends
            </h3>
            <div className="h-64">
              <DashboardCharts data={chartData} />
            </div>
          </div>

          {/* Service Performance Chart */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
              <div className="w-3 h-3 bg-green-500 rounded-full mr-2"></div>
              Service Performance
            </h3>
            <div className="h-64">
              <DashboardCharts data={chartData} />
            </div>
          </div>
        </div>

        {/* Service Distribution Chart */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-8">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
            <div className="w-3 h-3 bg-purple-500 rounded-full mr-2"></div>
            Service Distribution
          </h3>
          <div className="h-64">
            <DashboardCharts data={chartData} />
          </div>
        </div>

        {/* Services and Activity Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Active Services */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
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
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
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
                      <p className="text-sm font-medium">{item.message}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{item.timestamp}</p>
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