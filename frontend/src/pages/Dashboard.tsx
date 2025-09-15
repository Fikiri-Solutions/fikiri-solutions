import React, { useState, useEffect } from 'react'
import { Mail, Users, Brain, TrendingUp, Clock, CheckCircle } from 'lucide-react'
import { ServiceCard } from '../components/ServiceCard'
import { MetricCard } from '../components/MetricCard'
import { config, getFeatureConfig } from '../config'
import { mockServices, mockMetrics, mockActivity, MockApiClient } from '../mockData'

export const Dashboard: React.FC = () => {
  const features = getFeatureConfig()
  const [services, setServices] = useState(mockServices)
  const [metrics, setMetrics] = useState(mockMetrics)
  const [activity, setActivity] = useState(mockActivity)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setIsLoading(true)
    try {
      if (features.useMockData) {
        // Use mock data for local testing
        await new Promise(resolve => setTimeout(resolve, 500)) // Simulate API delay
        setServices(mockServices)
        setMetrics(mockMetrics)
        setActivity(mockActivity)
      } else {
        // Use real API
        const apiClient = new MockApiClient() // Replace with real API client
        const [servicesRes, metricsRes, activityRes] = await Promise.all([
          apiClient.get('/api/services'),
          apiClient.get('/api/metrics'),
          apiClient.get('/api/activity')
        ])
        setServices(servicesRes.data)
        setMetrics(metricsRes.data)
        setActivity(activityRes.data)
      }
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
      // Fallback to mock data on error
      setServices(mockServices)
      setMetrics(mockMetrics)
      setActivity(mockActivity)
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
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Total Emails"
          value={metrics.totalEmails}
          icon={Mail}
          change="+12%"
          changeType="positive"
        />
        <MetricCard
          title="Active Leads"
          value={metrics.activeLeads}
          icon={Users}
          change="+8%"
          changeType="positive"
        />
        <MetricCard
          title="AI Responses"
          value={metrics.aiResponses}
          icon={Brain}
          change="+23%"
          changeType="positive"
        />
        <MetricCard
          title="Avg Response Time"
          value={`${metrics.avgResponseTime}h`}
          icon={Clock}
          change="-15%"
          changeType="positive"
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
              {features.useMockData ? 'Mock Data' : 'Live Data'}
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
                <CheckCircle className={`h-5 w-5 ${
                  item.status === 'success' ? 'text-green-500' : 
                  item.status === 'warning' ? 'text-yellow-500' : 'text-red-500'
                }`} />
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
