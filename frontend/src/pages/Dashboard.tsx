import React, { useState, useEffect } from 'react'
import { Mail, Users, Brain, TrendingUp, Clock, CheckCircle } from 'lucide-react'
import { ServiceCard } from '../components/ServiceCard'
import { MetricCard } from '../components/MetricCard'

export const Dashboard: React.FC = () => {
  const [services, setServices] = useState([
    { id: 'ai-assistant', name: 'AI Email Assistant', status: 'active', description: 'Automated email responses and lead management' },
    { id: 'crm', name: 'CRM Service', status: 'active', description: 'Lead tracking and customer relationship management' },
    { id: 'email-parser', name: 'Email Parser', status: 'active', description: 'Intelligent email content analysis' },
    { id: 'ml-scoring', name: 'ML Lead Scoring', status: 'active', description: 'AI-powered lead prioritization' },
  ])

  const [metrics, setMetrics] = useState({
    totalEmails: 0,
    activeLeads: 0,
    aiResponses: 0,
    avgResponseTime: 0
  })

  useEffect(() => {
    // Fetch real data from API
    fetchMetrics()
  }, [])

  const fetchMetrics = async () => {
    try {
      const response = await fetch('/api/health')
      const data = await response.json()
      
      // Mock metrics for now - replace with real API calls
      setMetrics({
        totalEmails: 156,
        activeLeads: 23,
        aiResponses: 89,
        avgResponseTime: 2.3
      })
    } catch (error) {
      console.error('Failed to fetch metrics:', error)
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
        <h3 className="text-lg font-medium text-gray-900 mb-4">Recent Activity</h3>
        <div className="space-y-3">
          <div className="flex items-center space-x-3">
            <CheckCircle className="h-5 w-5 text-green-500" />
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">AI Assistant responded to inquiry from john@acme.com</p>
              <p className="text-xs text-gray-500">2 minutes ago</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <CheckCircle className="h-5 w-5 text-green-500" />
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">New lead added: Jane Smith from Startup Inc</p>
              <p className="text-xs text-gray-500">15 minutes ago</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <CheckCircle className="h-5 w-5 text-green-500" />
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">Email automation triggered for urgent inquiry</p>
              <p className="text-xs text-gray-500">1 hour ago</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
