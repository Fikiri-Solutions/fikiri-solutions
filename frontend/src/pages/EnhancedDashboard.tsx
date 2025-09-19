import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Mail, Users, Brain, Clock, Bot, UserPlus, Zap, AlertTriangle, CheckCircle2, XCircle, AlertCircle, DollarSign, TrendingUp } from 'lucide-react'
import { ServiceCard } from '../components/ServiceCard'
import { EnhancedMetricCard } from '../components/EnhancedMetricCard'
import { MiniTrend } from '../components/MiniTrend'
import { EnhancedDashboardCharts } from '../components/EnhancedDashboardCharts'
import { MetricCardSkeleton, ServiceCardSkeleton, ChartSkeleton, ActivitySkeleton } from '../components/Skeleton'
import { useToast } from '../components/Toast'
import { useWebSocket } from '../hooks/useWebSocket'
import { useDashboardTimeseries } from '../hooks/useDashboardTimeseries'
import { config, getFeatureConfig } from '../config'
import { apiClient } from '../services/apiClient'
import { mockServices, mockMetrics, mockActivity } from '../mockData'
import { useActivity } from '../contexts/ActivityContext'
import { DashboardSection, StatsGrid, DashboardCard } from '../components/DashboardLayout'

export const EnhancedDashboard: React.FC = () => {
  const navigate = useNavigate()
  const features = getFeatureConfig()
  const { addToast } = useToast()
  const { isConnected, data, requestMetricsUpdate, requestServicesUpdate } = useWebSocket()
  const { data: timeseriesData, summary, loading: timeseriesLoading, error: timeseriesError } = useDashboardTimeseries()
  const { getRecentActivities } = useActivity()

  // TanStack Query hooks for smart data fetching with real-time updates
  const { data: servicesData = [], isLoading: servicesLoading } = useQuery({
    queryKey: ['services'],
    queryFn: () => features.useMockData ? Promise.resolve(mockServices) : apiClient.getServices(),
    staleTime: 0,
    enabled: true,
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

  // Combine API data with real-time WebSocket updates and user activities
  const services = data.services?.services || servicesData
  const metrics = data.metrics || metricsData
  const apiActivity = data.activity ? [data.activity, ...activityData] : activityData
  const userActivities = getRecentActivities(5)
  const activity = userActivities.length > 0 ? userActivities : apiActivity

  return (
    <div className="space-y-8 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Enhanced Dashboard
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Advanced analytics and real-time insights
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-sm text-gray-600 dark:text-gray-400">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Enhanced Metrics Grid */}
      <StatsGrid>
        <EnhancedMetricCard
          title="Total Leads"
          value={1247}
          change={summary?.leads?.change_pct || 12.5}
          positive={summary?.leads?.positive || true}
          trend="up"
          icon={<Users className="h-5 w-5" />}
          color="blue"
        >
          <MiniTrend 
            data={timeseriesData || []} 
            dataKey="leads" 
            color="#3b82f6" 
          />
        </EnhancedMetricCard>

        <EnhancedMetricCard
          title="Emails Processed"
          value={5689}
          change={summary?.emails?.change_pct || 8.2}
          positive={summary?.emails?.positive || true}
          trend="up"
          icon={<Mail className="h-5 w-5" />}
          color="green"
        >
          <MiniTrend 
            data={timeseriesData || []} 
            dataKey="emails" 
            color="#22c55e" 
          />
        </EnhancedMetricCard>

        <EnhancedMetricCard
          title="AI Performance"
          value="94.2%"
          change={2.1}
          positive={true}
          trend="up"
          icon={<TrendingUp className="h-5 w-5" />}
          color="purple"
        >
          <MiniTrend 
            data={timeseriesData || []} 
            dataKey="revenue" 
            color="#8b5cf6" 
          />
        </EnhancedMetricCard>

        <EnhancedMetricCard
          title="Revenue"
          value={`$${12450}`}
          change={summary?.revenue?.change_pct || 15.3}
          positive={summary?.revenue?.positive || true}
          trend="up"
          icon={<DollarSign className="h-5 w-5" />}
          color="orange"
        >
          <MiniTrend 
            data={timeseriesData || []} 
            dataKey="revenue" 
            color="#f97316" 
          />
        </EnhancedMetricCard>
      </StatsGrid>

      {/* Enhanced Charts */}
      <DashboardSection title="Analytics Overview">
        <EnhancedDashboardCharts data={timeseriesData || []} />
      </DashboardSection>

      {/* Services and Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <DashboardCard title="Active Services">
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
        </DashboardCard>

        <DashboardCard title="Recent Activity">
          {activityLoading ? (
            <ActivitySkeleton />
          ) : (
            <div className="space-y-3">
              {activity.slice(0, 5).map((item) => (
                <div key={item.id} className="flex items-center space-x-3">
                  <div className="flex-shrink-0">
                    {item.type === 'email' && <Mail className="h-4 w-4 text-blue-500" />}
                    {item.type === 'lead' && <UserPlus className="h-4 w-4 text-green-500" />}
                    {item.type === 'automation' && <Zap className="h-4 w-4 text-yellow-500" />}
                    {item.type === 'error' && <AlertTriangle className="h-4 w-4 text-red-500" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {item.message}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {item.timestamp}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </DashboardCard>
      </div>
    </div>
  )
}