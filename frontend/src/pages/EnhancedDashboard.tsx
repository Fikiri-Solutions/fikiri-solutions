import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Mail, Users, Brain, Clock, Bot, UserPlus, Zap, AlertTriangle, CheckCircle2, XCircle, AlertCircle, DollarSign, TrendingUp } from 'lucide-react'
import { ServiceCard } from '../components/ServiceCard'
import { EnhancedMetricCard } from '../components/EnhancedMetricCard'
import { MiniTrend } from '../components/MiniTrend'
import { DashboardCharts } from '../components/DashboardCharts'
import { MetricCardSkeleton, ServiceCardSkeleton, ChartSkeleton, ActivitySkeleton } from '../components/Skeleton'
import { useToast } from '../components/Toast'
import { useWebSocket } from '../hooks/useWebSocket'
import { useDashboardTimeseries } from '../hooks/useDashboardTimeseries'
import { config, getFeatureConfig } from '../config'
import { apiClient } from '../services/apiClient'
import { mockServices, mockMetrics, mockActivity } from '../mockData'
import { DashboardSection, StatsGrid, DashboardCard } from '../components/DashboardLayout'

export const EnhancedDashboard: React.FC = () => {
  const navigate = useNavigate()
  const features = getFeatureConfig()
  const { addToast } = useToast()
  const { isConnected, data, requestMetricsUpdate, requestServicesUpdate } = useWebSocket()
  const { data: timeseriesData, summary, loading: timeseriesLoading, error: timeseriesError } = useDashboardTimeseries()

  // Clear specific cache items to force fresh data
  React.useEffect(() => {
    localStorage.removeItem('hasSeenPerformanceToast')
  }, [])

  // TanStack Query hooks for smart data fetching with real-time updates
  const { data: servicesData = [], isLoading: servicesLoading } = useQuery({
    queryKey: ['services'],
    queryFn: () => features.useMockData ? Promise.resolve(mockServices) : apiClient.getServices(),
    staleTime: 0,
    enabled: true,
  })

  const { data: metricsData, isLoading: metricsLoading } = useQuery({
    queryKey: ['metrics'],
    queryFn: () => features.useMockData ? Promise.resolve(mockMetrics) : apiClient.getMetrics(),
    staleTime: 0,
    enabled: true,
  })

  const { data: activityData = [], isLoading: activityLoading } = useQuery({
    queryKey: ['activity'],
    queryFn: () => features.useMockData ? Promise.resolve(mockActivity) : apiClient.getActivity(),
    staleTime: 0,
    enabled: true,
  })

  // Combine API data with real-time WebSocket updates
  const services = data.services?.services || servicesData
  const metrics = data.metrics || metricsData
  const apiActivity = data.activity ? [data.activity, ...activityData] : activityData
  const activity = apiActivity

  // Request real-time updates when WebSocket connects
  React.useEffect(() => {
    if (isConnected) {
      requestMetricsUpdate()
      requestServicesUpdate()
    }
  }, [isConnected, requestMetricsUpdate, requestServicesUpdate])

  // Generate dynamic chart data with realistic variations
  const generateChartData = () => {
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    const baseEmails = 40
    const baseLeads = 10
    const baseResponses = 35
    const baseValue = 85
    
    return days.map((day, index) => {
      const dayMultiplier = index < 5 ? 1.0 : 0.6
      const randomVariation = 0.8 + Math.random() * 0.4
      
      const emails = Math.floor(baseEmails * dayMultiplier * randomVariation)
      const leads = Math.floor(baseLeads * dayMultiplier * randomVariation)
      const responses = Math.floor(baseResponses * dayMultiplier * randomVariation)
      const value = Math.floor(baseValue * dayMultiplier * randomVariation)
      
      return {
        name: day,
        emails: Math.max(5, emails),
        leads: Math.max(2, leads),
        responses: Math.max(3, responses),
        value: Math.max(60, Math.min(100, value))
      }
    })
  }

  const [chartData, setChartData] = useState(generateChartData())

  // Update chart data periodically to simulate real-time changes
  useEffect(() => {
    const chartInterval = setInterval(() => {
      setChartData(generateChartData())
    }, 30000)

    return () => clearInterval(chartInterval)
  }, [])

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
        break
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
    <div className="space-y-8 p-6">
      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
            <p className="text-muted-foreground">
              Welcome back! Here's what's happening with your business automation.
            </p>
          </div>
          
          {/* Version and Connection Status */}
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 rounded-full bg-blue-500"></div>
              <span className="text-xs text-muted-foreground">
                Cache: {config.cacheVersion}
              </span>
            </div>
            
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
              <span className="text-xs text-muted-foreground">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Enhanced Metrics Grid */}
      <DashboardSection title="Key Metrics" description="Real-time performance indicators">
        <StatsGrid>
          {timeseriesLoading ? (
            <>
              <MetricCardSkeleton />
              <MetricCardSkeleton />
              <MetricCardSkeleton />
              <MetricCardSkeleton />
            </>
          ) : (
            <>
              <EnhancedMetricCard
                title="New Leads"
                value={timeseriesData?.reduce((sum, day) => sum + (day.leads || 0), 0) || 0}
                change={summary?.leads?.change_pct}
                positive={summary?.leads?.positive}
                icon={<Users className="h-5 w-5" />}
                onClick={() => handleMetricClick('leads')}
              >
                <MiniTrend data={timeseriesData || []} dataKey="leads" color="#22c55e" />
              </EnhancedMetricCard>

              <EnhancedMetricCard
                title="Emails Sent"
                value={timeseriesData?.reduce((sum, day) => sum + (day.emails || 0), 0) || 0}
                change={summary?.emails?.change_pct}
                positive={summary?.emails?.positive}
                icon={<Mail className="h-5 w-5" />}
                onClick={() => handleMetricClick('emails')}
              >
                <MiniTrend data={timeseriesData || []} dataKey="emails" color="#3b82f6" />
              </EnhancedMetricCard>

              <EnhancedMetricCard
                title="Revenue Impact"
                value={`$${((timeseriesData?.reduce((sum, day) => sum + (day.revenue || 0), 0) || 0) / 1000).toFixed(1)}k`}
                change={summary?.revenue?.change_pct}
                positive={summary?.revenue?.positive}
                icon={<DollarSign className="h-5 w-5" />}
                onClick={() => handleMetricClick('revenue')}
              >
                <MiniTrend data={timeseriesData || []} dataKey="revenue" color="#f97316" />
              </EnhancedMetricCard>

              <EnhancedMetricCard
                title="AI Performance"
                value={`${Math.round((metrics?.avgResponseTime || 0) * 100) / 100}h`}
                change={-15}
                positive={true}
                icon={<Brain className="h-5 w-5" />}
                onClick={() => handleMetricClick('responseTime')}
              >
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <TrendingUp className="h-4 w-4 text-brand-secondary" />
                  <span>Optimized</span>
                </div>
              </EnhancedMetricCard>
            </>
          )}
        </StatsGrid>
      </DashboardSection>

      {/* Charts Section */}
      <DashboardSection title="Analytics" description="Performance trends and insights">
        {chartData.length === 0 ? (
          <ChartSkeleton />
        ) : (
          <DashboardCharts data={chartData} />
        )}
      </DashboardSection>

      {/* Services and Activity Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Services */}
        <DashboardCard
          title="Active Services"
          description="Your automation services status"
          badge={{ text: `${services.length} Active`, variant: "default" }}
        >
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

        {/* Recent Activity */}
        <DashboardCard
          title="Recent Activity"
          description="Latest system events and updates"
          badge={{ text: "Live", variant: "secondary" }}
        >
          {activityLoading ? (
            <ActivitySkeleton />
          ) : (
            <div className="space-y-3">
              {activity.slice(0, 5).map((item) => (
                <div key={item.id} className="flex items-center space-x-3">
                  {getActivityIcon(item.type, item.status)}
                  <div className="flex-1">
                    <p className="text-sm font-medium">{item.message}</p>
                    <p className="text-xs text-muted-foreground">{item.timestamp}</p>
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
