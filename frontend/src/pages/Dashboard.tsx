import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Mail, Users, Brain, Clock, Bot, UserPlus, Zap, AlertTriangle, CheckCircle2, XCircle, AlertCircle } from 'lucide-react'
import { ServiceCard } from '../components/ServiceCard'
import { MetricCard } from '../components/MetricCard'
import { DashboardCharts } from '../components/DashboardCharts'
import { MetricCardSkeleton, ServiceCardSkeleton, ChartSkeleton, ActivitySkeleton } from '../components/Skeleton'
import { config, getFeatureConfig } from '../config'
import { apiClient, ServiceData, MetricData, ActivityItem } from '../services/apiClient'
import { mockServices, mockMetrics, mockActivity } from '../mockData'

export const Dashboard: React.FC = () => {
  const navigate = useNavigate()
  const features = getFeatureConfig()

  // TanStack Query hooks for smart data fetching
  const { data: services = [], isLoading: servicesLoading } = useQuery({
    queryKey: ['services'],
    queryFn: () => features.useMockData ? Promise.resolve(mockServices) : apiClient.getServices(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['metrics'],
    queryFn: () => features.useMockData ? Promise.resolve(mockMetrics) : apiClient.getMetrics(),
    staleTime: 2 * 60 * 1000, // 2 minutes
  })

  const { data: activity = [], isLoading: activityLoading } = useQuery({
    queryKey: ['activity'],
    queryFn: () => features.useMockData ? Promise.resolve(mockActivity) : apiClient.getActivity(),
    staleTime: 1 * 60 * 1000, // 1 minute
  })

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
        break
      case 'leads':
        navigate('/crm?filter=active')
        break
      case 'responses':
        navigate('/services')
        break
      case 'responseTime':
        navigate('/services')
        break
      default:
        console.log(`Clicked ${metricType}`)
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
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-600">
          Welcome back! Here's what's happening with your Fikiri Solutions.
        </p>
        {(servicesLoading || metricsLoading || activityLoading) && (
          <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-600">
              <strong>Loading:</strong> Fetching latest data...
            </p>
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
