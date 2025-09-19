import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Mail, Users, Brain, Clock, Bot, UserPlus, Zap, AlertTriangle, CheckCircle2, XCircle, AlertCircle, DollarSign, TrendingUp, BarChart3, PieChart as PieChartIcon, Grid, Layout } from 'lucide-react'
import { ServiceCard } from '../components/ServiceCard'
import { EnhancedMetricCard } from '../components/EnhancedMetricCard'
import { MiniTrend } from '../components/MiniTrend'
import { ChartWidget, CompactChartGrid } from '../components/ChartWidget'
import { MetricCardSkeleton, ServiceCardSkeleton, ChartSkeleton, ActivitySkeleton } from '../components/Skeleton'
import { useToast } from '../components/Toast'
import { useWebSocket } from '../hooks/useWebSocket'
import { useDashboardTimeseries } from '../hooks/useDashboardTimeseries'
import { config, getFeatureConfig } from '../config'
import { apiClient } from '../services/apiClient'
import { mockServices, mockMetrics, mockActivity } from '../mockData'
import { DashboardSection, StatsGrid, DashboardCard } from '../components/DashboardLayout'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useActivity } from '../contexts/ActivityContext'

export const CompactDashboard: React.FC = () => {
  const navigate = useNavigate()
  const features = getFeatureConfig()
  const { addToast } = useToast()
  const { isConnected, data, requestMetricsUpdate, requestServicesUpdate } = useWebSocket()
  const { data: timeseriesData, summary, loading: timeseriesLoading, error: timeseriesError } = useDashboardTimeseries()
  const { getRecentActivities } = useActivity()

  const [viewMode, setViewMode] = useState<'grid' | 'compact'>('grid') // State for chart view mode

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

  const pieChartData = transformForPieChart(timeseriesData)

  return (
    <div className="space-y-6 p-4">
      {/* Compact Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Compact Dashboard
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Streamlined view for quick insights
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-xs text-gray-600 dark:text-gray-400">
            {isConnected ? 'Live' : 'Offline'}
          </span>
        </div>
      </div>

      {/* Compact Metrics */}
      <StatsGrid className="grid-cols-2 lg:grid-cols-4 gap-4">
        <EnhancedMetricCard
          title="Leads"
          value={1247}
          change={summary?.leads?.change_pct || 12.5}
          positive={summary?.leads?.positive || true}
          trend="up"
          icon={<Users className="h-4 w-4" />}
          color="blue"
          compact
        >
          <MiniTrend 
            data={timeseriesData || []} 
            dataKey="leads" 
            color="#3b82f6" 
            height={30}
          />
        </EnhancedMetricCard>

        <EnhancedMetricCard
          title="Emails"
          value={5689}
          change={summary?.emails?.change_pct || 8.2}
          positive={summary?.emails?.positive || true}
          trend="up"
          icon={<Mail className="h-4 w-4" />}
          color="green"
          compact
        >
          <MiniTrend 
            data={timeseriesData || []} 
            dataKey="emails" 
            color="#22c55e" 
            height={30}
          />
        </EnhancedMetricCard>

        <EnhancedMetricCard
          title="AI Score"
          value="94.2%"
          change={2.1}
          positive={true}
          trend="up"
          icon={<Brain className="h-4 w-4" />}
          color="purple"
          compact
        >
          <MiniTrend 
            data={timeseriesData || []} 
            dataKey="revenue" 
            color="#8b5cf6" 
            height={30}
          />
        </EnhancedMetricCard>

        <EnhancedMetricCard
          title="Revenue"
          value={`$${12450}`}
          change={summary?.revenue?.change_pct || 15.3}
          positive={summary?.revenue?.positive || true}
          trend="up"
          icon={<DollarSign className="h-4 w-4" />}
          color="orange"
          compact
        >
          <MiniTrend 
            data={timeseriesData || []} 
            dataKey="revenue" 
            color="#f97316" 
            height={30}
          />
        </EnhancedMetricCard>
      </StatsGrid>

      {/* Chart View Toggle */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Analytics
        </h2>
        <div className="flex items-center space-x-2">
          <Button
            variant={viewMode === 'grid' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setViewMode('grid')}
          >
            <Grid className="h-4 w-4 mr-1" />
            Grid
          </Button>
          <Button
            variant={viewMode === 'compact' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setViewMode('compact')}
          >
            <Layout className="h-4 w-4 mr-1" />
            Compact
          </Button>
        </div>
      </div>

      {/* Charts */}
      {viewMode === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <ChartWidget
            title="Email Trends"
            data={timeseriesData || []}
            type="line"
            dataKey="emails"
            color="#3b82f6"
          />
          <ChartWidget
            title="Lead Growth"
            data={timeseriesData || []}
            type="bar"
            dataKey="leads"
            color="#22c55e"
          />
          <ChartWidget
            title="Revenue"
            data={timeseriesData || []}
            type="area"
            dataKey="revenue"
            color="#f97316"
          />
        </div>
      ) : (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Quick Overview</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-48">
                <ChartWidget
                  title=""
                  data={timeseriesData || []}
                  type="line"
                  dataKey="emails"
                  color="#3b82f6"
                  compact
                />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Compact Services and Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <DashboardCard title="Services" compact>
          {servicesLoading ? (
            <div className="space-y-2">
              <ServiceCardSkeleton />
              <ServiceCardSkeleton />
            </div>
          ) : (
            <div className="space-y-2">
              {services.slice(0, 2).map((service) => (
                <ServiceCard key={service.id} service={service} compact />
              ))}
            </div>
          )}
        </DashboardCard>

        <DashboardCard title="Activity" compact>
          {activityLoading ? (
            <ActivitySkeleton />
          ) : (
            <div className="space-y-2">
              {activity.slice(0, 3).map((item) => (
                <div key={item.id} className="flex items-center space-x-2">
                  <div className="flex-shrink-0">
                    {item.type === 'email' && <Mail className="h-3 w-3 text-blue-500" />}
                    {item.type === 'lead' && <UserPlus className="h-3 w-3 text-green-500" />}
                    {item.type === 'automation' && <Zap className="h-3 w-3 text-yellow-500" />}
                    {item.type === 'error' && <AlertTriangle className="h-3 w-3 text-red-500" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-gray-900 dark:text-white truncate">
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