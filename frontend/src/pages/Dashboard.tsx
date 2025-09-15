import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Mail, Users, Brain, Clock, Bot, UserPlus, Zap, AlertTriangle, CheckCircle2, XCircle, AlertCircle } from 'lucide-react'
import { ServiceCard } from '../components/ServiceCard'
import { MetricCard } from '../components/MetricCard'
import { config, getFeatureConfig } from '../config'
import { apiClient, ServiceData, MetricData, ActivityItem } from '../services/apiClient'
import { mockServices, mockMetrics, mockActivity } from '../mockData'

export const Dashboard: React.FC = () => {
  const navigate = useNavigate()
  const features = getFeatureConfig()
  const [services, setServices] = useState<ServiceData[]>([])
  const [metrics, setMetrics] = useState<MetricData>({
    totalEmails: 0,
    activeLeads: 0,
    aiResponses: 0,
    avgResponseTime: 0
  })
  const [activity, setActivity] = useState<ActivityItem[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

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

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setIsLoading(true)
    setError(null)
    
    try {
      if (features.useMockData) {
        // Use mock data for local testing
        await new Promise(resolve => setTimeout(resolve, 500)) // Simulate API delay
        setServices(mockServices)
        setMetrics(mockMetrics)
        setActivity(mockActivity)
      } else {
        // Use real API
        console.log('🔄 Fetching data from backend API...')
        
        const [servicesData, metricsData, activityData] = await Promise.all([
          apiClient.getServices(),
          apiClient.getMetrics(),
          apiClient.getActivity()
        ])
        
        setServices(servicesData)
        setMetrics(metricsData)
        setActivity(activityData)
        
        console.log('✅ Data fetched successfully from backend')
      }
    } catch (error) {
      console.error('❌ Failed to fetch dashboard data:', error)
      setError(apiClient.handleError(error))
      
      // Fallback to mock data on error
      setServices(mockServices)
      setMetrics(mockMetrics)
      setActivity(mockActivity)
      console.log('🔄 Fallback to mock data due to API error')
    } finally {
      setIsLoading(false)
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
        {error && (
          <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-sm text-red-600">
              <strong>API Error:</strong> {error}
            </p>
            <button 
              onClick={fetchData}
              className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
            >
              Retry
            </button>
          </div>
        )}
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Total Emails"
          value={metrics.totalEmails}
          icon={Mail}
          change="+12%"
          changeType="positive"
          onClick={() => handleMetricClick('emails')}
        />
        <MetricCard
          title="Active Leads"
          value={metrics.activeLeads}
          icon={Users}
          change="+8%"
          changeType="positive"
          onClick={() => handleMetricClick('leads')}
        />
        <MetricCard
          title="AI Responses"
          value={metrics.aiResponses}
          icon={Brain}
          change="+23%"
          changeType="positive"
          onClick={() => handleMetricClick('responses')}
        />
        <MetricCard
          title="Avg Response Time"
          value={`${Math.round(metrics.avgResponseTime * 100) / 100}h`}
          icon={Clock}
          change="-15%"
          changeType="positive"
          onClick={() => handleMetricClick('responseTime')}
        />
      </div>

      {/* Services Status */}
      <div>
        <h2 className="text-lg font-medium text-gray-900 mb-4">Service Status</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {services.map((service) => (
            <ServiceCard key={service.id} service={service} />
          ))}
        </div>
      </div>

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
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
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
