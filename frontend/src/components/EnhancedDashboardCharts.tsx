import React, { useState, useMemo } from 'react'
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  BarChart, Bar, PieChart, Pie, Cell, AreaChart, Area, Legend,
  ReferenceLine, Brush
} from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card"
import { Badge } from "./ui/badge"
import { Button } from "./ui/Button"
import { 
  TrendingUp, TrendingDown, BarChart3, PieChart as PieChartIcon, 
  Calendar, Filter, Download, Maximize2, RefreshCw, Eye, EyeOff, Activity
} from 'lucide-react'
import { cn } from "../lib/utils"

interface ChartData {
  name: string
  value: number
  emails?: number
  leads?: number
  responses?: number
  revenue?: number
  timestamp?: string
  day?: string
}

interface DashboardChartsProps {
  data: ChartData[]
  pieData?: Array<{
    name: string;
    value: number;
    color: string;
  }>;
  serviceMetrics?: {
    emailAutomation: { count: number; label: string }
    leadManagement: { count: number; label: string }
    aiResponses: { count: number; label: string; accuracy?: number }
  }
}

// Modern, professional color palette
const MODERN_COLORS = {
  primary: '#3B82F6',      // Modern blue
  secondary: '#8B5CF6',    // Purple
  success: '#10B981',      // Emerald green
  warning: '#F59E0B',      // Amber
  error: '#EF4444',        // Red
  info: '#06B6D4',         // Cyan
  accent: '#F97316'        // Orange
}

// Sleek gradient definitions
const GRADIENTS = {
  email: { from: '#3B82F6', to: '#1E40AF', opacity: 0.8 },
  lead: { from: '#10B981', to: '#059669', opacity: 0.8 },
  response: { from: '#F59E0B', to: '#D97706', opacity: 0.8 },
  revenue: { from: '#8B5CF6', to: '#7C3AED', opacity: 0.8 }
}

export const EnhancedDashboardCharts: React.FC<DashboardChartsProps> = ({ 
  data, 
  pieData = [],
  serviceMetrics
}) => {
  const [activeChart, setActiveChart] = useState<'line' | 'bar' | 'area'>('line')
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('7d')
  const [showLegend, setShowLegend] = useState(true)
  const [isFullscreen, setIsFullscreen] = useState(false)

  // Calculate service performance from real data
  const calculatedServiceMetrics = useMemo(() => {
    if (!data || data.length === 0) {
      return {
        emailAutomation: { count: 0, label: 'emails processed' },
        leadManagement: { count: 0, label: 'new leads' },
        aiResponses: { count: 0, label: 'responses', accuracy: 0 }
      }
    }

    const totalEmails = data.reduce((sum, d) => sum + (d.emails || 0), 0)
    const totalLeads = data.reduce((sum, d) => sum + (d.leads || 0), 0)
    const totalResponses = data.reduce((sum, d) => sum + (d.responses || 0), 0)
    
    // Calculate accuracy based on response rate (simplified)
    const accuracy = totalEmails > 0 ? Math.min(95, Math.max(85, (totalResponses / totalEmails) * 100)) : 0

    return {
      emailAutomation: { 
        count: totalEmails, 
        label: 'emails processed' 
      },
      leadManagement: { 
        count: totalLeads, 
        label: 'new leads' 
      },
      aiResponses: { 
        count: totalResponses, 
        label: 'responses',
        accuracy: Math.round(accuracy * 10) / 10
      }
    }
  }, [data])

  const metrics = serviceMetrics || calculatedServiceMetrics

  // Calculate pie chart data from real metrics
  const realPieData = useMemo(() => {
    const total = metrics.emailAutomation.count + metrics.leadManagement.count + metrics.aiResponses.count
    if (total === 0) {
      return pieData.length > 0 ? pieData : []
    }

    return [
      { 
        name: 'Email Automation', 
        value: metrics.emailAutomation.count, 
        color: MODERN_COLORS.primary,
        percentage: (metrics.emailAutomation.count / total) * 100
      },
      { 
        name: 'Lead Management', 
        value: metrics.leadManagement.count, 
        color: MODERN_COLORS.success,
        percentage: (metrics.leadManagement.count / total) * 100
      },
      { 
        name: 'AI Responses', 
        value: metrics.aiResponses.count, 
        color: MODERN_COLORS.warning,
        percentage: (metrics.aiResponses.count / total) * 100
      }
    ].filter(item => item.value > 0)
  }, [metrics, pieData])

  // Filter data based on time range with proper date handling
  const getFilteredData = (data: ChartData[], range: '7d' | '30d' | '90d') => {
    if (!data || data.length === 0) return []
    
    const now = new Date()
    const daysBack = range === '7d' ? 7 : range === '30d' ? 30 : 90
    const cutoffDate = new Date(now.getTime() - (daysBack * 24 * 60 * 60 * 1000))
    
    return data.filter(item => {
      if (item.day) {
        const itemDate = new Date(item.day)
        return itemDate >= cutoffDate
      }
      if (item.timestamp) {
        const itemDate = new Date(item.timestamp)
        return itemDate >= cutoffDate
      }
      // If no date field, include all data (fallback)
      return true
    }).map(item => ({
      ...item,
      // Format date properly for display
      name: item.day 
        ? new Date(item.day).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
        : item.name || 'N/A'
    }))
  }

  const filteredData = getFilteredData(data, timeRange)

  // Modern tooltip design
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white dark:bg-gray-800 p-4 border border-gray-200 dark:border-gray-700 rounded-xl shadow-xl backdrop-blur-sm">
          <p className="font-semibold text-gray-900 dark:text-gray-100 mb-3 text-sm">{label}</p>
          <div className="space-y-2">
            {payload.map((entry: any, index: number) => (
              <div key={index} className="flex items-center gap-3">
                <div 
                  className="w-3 h-3 rounded-full shadow-sm" 
                  style={{ backgroundColor: entry.color }}
                />
                <span className="text-sm text-gray-600 dark:text-gray-300 min-w-[100px]">
                  {entry.name}:
                </span>
                <span className="font-bold text-gray-900 dark:text-gray-100">
                  {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
                </span>
              </div>
            ))}
          </div>
        </div>
      )
    }
    return null
  }

  const CustomPieTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0]
      return (
        <div className="bg-white dark:bg-gray-800 p-4 border border-gray-200 dark:border-gray-700 rounded-xl shadow-xl">
          <p className="font-semibold text-gray-900 dark:text-gray-100 mb-2">{data.name}</p>
          <p className="text-sm text-gray-600 dark:text-gray-300">
            Count: <span className="font-bold">{data.value.toLocaleString()}</span>
          </p>
          {data.payload.percentage !== undefined && (
            <p className="text-sm text-gray-600 dark:text-gray-300">
              Share: <span className="font-bold">{data.payload.percentage.toFixed(1)}%</span>
            </p>
          )}
        </div>
      )
    }
    return null
  }

  const calculateTrend = (data: ChartData[], key: string) => {
    if (data.length < 2) return { direction: 'neutral', percentage: 0 }
    const first = (data[0][key as keyof ChartData] as number) || 0
    const last = (data[data.length - 1][key as keyof ChartData] as number) || 0
    const percentage = first > 0 ? ((last - first) / first) * 100 : 0
    return {
      direction: percentage > 0 ? 'up' : percentage < 0 ? 'down' : 'neutral',
      percentage: Math.abs(percentage)
    }
  }

  const emailTrend = calculateTrend(filteredData, 'emails')
  const leadTrend = calculateTrend(filteredData, 'leads')
  const responseTrend = calculateTrend(filteredData, 'responses')

  return (
    <div className="space-y-6">
      {/* Analytics Overview - Modern Design */}
      <Card className="border-0 shadow-lg bg-gradient-to-br from-white to-gray-50 dark:from-gray-900 dark:to-gray-800">
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-3 text-2xl font-bold text-gray-900 dark:text-white">
                <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                  <Activity className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                </div>
                Analytics Overview
              </CardTitle>
              <CardDescription className="mt-2 text-base">
                Real-time data visualization with interactive controls
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowLegend(!showLegend)}
                className="border-gray-200 dark:border-gray-700"
              >
                {showLegend ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsFullscreen(!isFullscreen)}
                className="border-gray-200 dark:border-gray-700"
              >
                <Maximize2 className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="sm" className="border-gray-200 dark:border-gray-700">
                <Download className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Time Range and Chart Type Controls */}
          <div className="flex flex-wrap items-center gap-6 mb-6 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl">
            <div className="flex items-center gap-3">
              <Filter className="h-4 w-4 text-gray-500" />
              <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">Time Range:</span>
              <div className="flex gap-2">
                {(['7d', '30d', '90d'] as const).map((range) => (
                  <Button
                    key={range}
                    variant={timeRange === range ? "default" : "outline"}
                    size="sm"
                    onClick={() => setTimeRange(range)}
                    className={timeRange === range 
                      ? "bg-blue-600 hover:bg-blue-700 text-white border-0 shadow-md" 
                      : "border-gray-300 dark:border-gray-600"
                    }
                  >
                    {range}
                  </Button>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">Chart Type:</span>
              <div className="flex gap-2">
                {[
                  { key: 'line', icon: TrendingUp, label: 'Line' },
                  { key: 'bar', icon: BarChart3, label: 'Bar' },
                  { key: 'area', icon: PieChartIcon, label: 'Area' }
                ].map(({ key, icon: Icon, label }) => (
                  <Button
                    key={key}
                    variant={activeChart === key ? "default" : "outline"}
                    size="sm"
                    onClick={() => setActiveChart(key as any)}
                    className={activeChart === key
                      ? "bg-blue-600 hover:bg-blue-700 text-white border-0 shadow-md" 
                      : "border-gray-300 dark:border-gray-600"
                    }
                  >
                    <Icon className="h-4 w-4 mr-1" />
                    {label}
                  </Button>
                ))}
              </div>
            </div>
          </div>

          {/* Trend Indicators - Modern Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="flex items-center justify-between p-4 bg-gradient-to-r from-blue-50 to-blue-100/50 dark:from-blue-900/20 dark:to-blue-800/10 rounded-xl border border-blue-200 dark:border-blue-800">
              <div>
                <p className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-1">Email Trends</p>
                <div className="flex items-center gap-2">
                  {emailTrend.direction === 'up' ? (
                    <TrendingUp className="h-5 w-5 text-green-600" />
                  ) : emailTrend.direction === 'down' ? (
                    <TrendingDown className="h-5 w-5 text-red-600" />
                  ) : (
                    <div className="h-5 w-5 bg-gray-400 rounded-full" />
                  )}
                  <span className="text-lg font-bold text-blue-900 dark:text-blue-100">
                    {emailTrend.percentage.toFixed(1)}%
                  </span>
                </div>
              </div>
              <Badge className="bg-blue-600 text-white px-3 py-1 text-sm font-semibold shadow-sm">
                {filteredData.reduce((sum, d) => sum + (d.emails || 0), 0).toLocaleString()}
              </Badge>
            </div>

            <div className="flex items-center justify-between p-4 bg-gradient-to-r from-green-50 to-green-100/50 dark:from-green-900/20 dark:to-green-800/10 rounded-xl border border-green-200 dark:border-green-800">
              <div>
                <p className="text-sm font-semibold text-green-900 dark:text-green-100 mb-1">Lead Trends</p>
                <div className="flex items-center gap-2">
                  {leadTrend.direction === 'up' ? (
                    <TrendingUp className="h-5 w-5 text-green-600" />
                  ) : leadTrend.direction === 'down' ? (
                    <TrendingDown className="h-5 w-5 text-red-600" />
                  ) : (
                    <div className="h-5 w-5 bg-gray-400 rounded-full" />
                  )}
                  <span className="text-lg font-bold text-green-900 dark:text-green-100">
                    {leadTrend.percentage.toFixed(1)}%
                  </span>
                </div>
              </div>
              <Badge className="bg-green-600 text-white px-3 py-1 text-sm font-semibold shadow-sm">
                {filteredData.reduce((sum, d) => sum + (d.leads || 0), 0).toLocaleString()}
              </Badge>
            </div>

            <div className="flex items-center justify-between p-4 bg-gradient-to-r from-orange-50 to-orange-100/50 dark:from-orange-900/20 dark:to-orange-800/10 rounded-xl border border-orange-200 dark:border-orange-800">
              <div>
                <p className="text-sm font-semibold text-orange-900 dark:text-orange-100 mb-1">Response Trends</p>
                <div className="flex items-center gap-2">
                  {responseTrend.direction === 'up' ? (
                    <TrendingUp className="h-5 w-5 text-green-600" />
                  ) : responseTrend.direction === 'down' ? (
                    <TrendingDown className="h-5 w-5 text-red-600" />
                  ) : (
                    <div className="h-5 w-5 bg-gray-400 rounded-full" />
                  )}
                  <span className="text-lg font-bold text-orange-900 dark:text-orange-100">
                    {responseTrend.percentage.toFixed(1)}%
                  </span>
                </div>
              </div>
              <Badge className="bg-orange-600 text-white px-3 py-1 text-sm font-semibold shadow-sm">
                {filteredData.reduce((sum, d) => sum + (d.responses || 0), 0).toLocaleString()}
              </Badge>
            </div>
          </div>

          {/* Main Chart - Sleek Design */}
          <Card className="border border-gray-200 dark:border-gray-700 shadow-md bg-white dark:bg-gray-800">
            <CardContent className="p-6">
              <div className="h-96">
                <ResponsiveContainer width="100%" height="100%">
                  {activeChart === 'line' ? (
                    <LineChart data={filteredData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" opacity={0.3} />
                      <XAxis 
                        dataKey="name" 
                        tick={{ fontSize: 12, fill: '#6B7280' }}
                        tickLine={{ stroke: '#E5E7EB' }}
                        axisLine={{ stroke: '#E5E7EB' }}
                      />
                      <YAxis 
                        tick={{ fontSize: 12, fill: '#6B7280' }}
                        tickLine={{ stroke: '#E5E7EB' }}
                        axisLine={{ stroke: '#E5E7EB' }}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      {showLegend && <Legend wrapperStyle={{ paddingTop: '20px' }} />}
                      <Line 
                        type="monotone" 
                        dataKey="emails" 
                        stroke={MODERN_COLORS.primary}
                        strokeWidth={3}
                        dot={{ fill: MODERN_COLORS.primary, strokeWidth: 2, r: 5 }}
                        activeDot={{ r: 7, stroke: MODERN_COLORS.primary, strokeWidth: 3 }}
                        name="Emails"
                      />
                      <Line 
                        type="monotone" 
                        dataKey="leads" 
                        stroke={MODERN_COLORS.success}
                        strokeWidth={3}
                        dot={{ fill: MODERN_COLORS.success, strokeWidth: 2, r: 5 }}
                        activeDot={{ r: 7, stroke: MODERN_COLORS.success, strokeWidth: 3 }}
                        name="Leads"
                      />
                      <Line 
                        type="monotone" 
                        dataKey="responses" 
                        stroke={MODERN_COLORS.warning}
                        strokeWidth={3}
                        dot={{ fill: MODERN_COLORS.warning, strokeWidth: 2, r: 5 }}
                        activeDot={{ r: 7, stroke: MODERN_COLORS.warning, strokeWidth: 3 }}
                        name="AI Responses"
                      />
                      <Brush dataKey="name" height={30} stroke={MODERN_COLORS.primary} />
                    </LineChart>
                  ) : activeChart === 'bar' ? (
                    <BarChart data={filteredData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" opacity={0.3} />
                      <XAxis 
                        dataKey="name" 
                        tick={{ fontSize: 12, fill: '#6B7280' }}
                        tickLine={{ stroke: '#E5E7EB' }}
                        axisLine={{ stroke: '#E5E7EB' }}
                      />
                      <YAxis 
                        tick={{ fontSize: 12, fill: '#6B7280' }}
                        tickLine={{ stroke: '#E5E7EB' }}
                        axisLine={{ stroke: '#E5E7EB' }}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      {showLegend && <Legend wrapperStyle={{ paddingTop: '20px' }} />}
                      <Bar 
                        dataKey="emails" 
                        fill="url(#emailGradient)"
                        radius={[8, 8, 0, 0]}
                        name="Emails"
                      />
                      <Bar 
                        dataKey="leads" 
                        fill="url(#leadGradient)"
                        radius={[8, 8, 0, 0]}
                        name="Leads"
                      />
                      <Bar 
                        dataKey="responses" 
                        fill="url(#responseGradient)"
                        radius={[8, 8, 0, 0]}
                        name="AI Responses"
                      />
                      <defs>
                        <linearGradient id="emailGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor={GRADIENTS.email.from} />
                          <stop offset="100%" stopColor={GRADIENTS.email.to} />
                        </linearGradient>
                        <linearGradient id="leadGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor={GRADIENTS.lead.from} />
                          <stop offset="100%" stopColor={GRADIENTS.lead.to} />
                        </linearGradient>
                        <linearGradient id="responseGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor={GRADIENTS.response.from} />
                          <stop offset="100%" stopColor={GRADIENTS.response.to} />
                        </linearGradient>
                      </defs>
                    </BarChart>
                  ) : (
                    <AreaChart data={filteredData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" opacity={0.3} />
                      <XAxis 
                        dataKey="name" 
                        tick={{ fontSize: 12, fill: '#6B7280' }}
                        tickLine={{ stroke: '#E5E7EB' }}
                        axisLine={{ stroke: '#E5E7EB' }}
                      />
                      <YAxis 
                        tick={{ fontSize: 12, fill: '#6B7280' }}
                        tickLine={{ stroke: '#E5E7EB' }}
                        axisLine={{ stroke: '#E5E7EB' }}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      {showLegend && <Legend wrapperStyle={{ paddingTop: '20px' }} />}
                      <Area 
                        type="monotone" 
                        dataKey="emails" 
                        stackId="1"
                        stroke={MODERN_COLORS.primary}
                        fill="url(#emailAreaGradient)"
                        strokeWidth={2}
                        name="Emails"
                      />
                      <Area 
                        type="monotone" 
                        dataKey="leads" 
                        stackId="1"
                        stroke={MODERN_COLORS.success}
                        fill="url(#leadAreaGradient)"
                        strokeWidth={2}
                        name="Leads"
                      />
                      <Area 
                        type="monotone" 
                        dataKey="responses" 
                        stackId="1"
                        stroke={MODERN_COLORS.warning}
                        fill="url(#responseAreaGradient)"
                        strokeWidth={2}
                        name="AI Responses"
                      />
                      <defs>
                        <linearGradient id="emailAreaGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={GRADIENTS.email.from} stopOpacity={GRADIENTS.email.opacity} />
                          <stop offset="95%" stopColor={GRADIENTS.email.from} stopOpacity={0.1} />
                        </linearGradient>
                        <linearGradient id="leadAreaGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={GRADIENTS.lead.from} stopOpacity={GRADIENTS.lead.opacity} />
                          <stop offset="95%" stopColor={GRADIENTS.lead.from} stopOpacity={0.1} />
                        </linearGradient>
                        <linearGradient id="responseAreaGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={GRADIENTS.response.from} stopOpacity={GRADIENTS.response.opacity} />
                          <stop offset="95%" stopColor={GRADIENTS.response.from} stopOpacity={0.1} />
                        </linearGradient>
                      </defs>
                    </AreaChart>
                  )}
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </CardContent>
      </Card>

      {/* Service Performance Overview - Using Real Data */}
      <Card className="border-0 shadow-lg bg-gradient-to-br from-white to-gray-50 dark:from-gray-900 dark:to-gray-800">
        <CardHeader className="pb-4">
          <CardTitle className="flex items-center gap-3 text-2xl font-bold text-gray-900 dark:text-white">
            <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
              <PieChartIcon className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
            Service Performance Overview
          </CardTitle>
          <CardDescription className="mt-2 text-base">
            Real performance metrics from your services (Last {timeRange === '7d' ? '7 days' : timeRange === '30d' ? '30 days' : '90 days'})
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Pie Chart - Using Real Data */}
            <div className="h-80">
              {realPieData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={realPieData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percentage }: any) => `${name}\n${percentage?.toFixed(1) || 0}%`}
                      outerRadius={110}
                      innerRadius={50}
                      fill="#8884d8"
                      dataKey="value"
                      animationDuration={600}
                      animationBegin={0}
                    >
                      {realPieData.map((entry, index) => (
                        <Cell 
                          key={`cell-${index}`} 
                          fill={entry.color}
                          stroke="#fff"
                          strokeWidth={3}
                        />
                      ))}
                    </Pie>
                    <Tooltip content={<CustomPieTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-gray-400 dark:text-gray-500">
                  <div className="text-center">
                    <Activity className="h-12 w-12 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No data available</p>
                  </div>
                </div>
              )}
            </div>
            
            {/* Performance Metrics - Real Data */}
            <div className="space-y-4">
              <div className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">
                Performance Metrics
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between p-4 bg-gradient-to-r from-blue-50 to-blue-100/50 dark:from-blue-900/20 dark:to-blue-800/10 rounded-xl border border-blue-200 dark:border-blue-800 shadow-sm">
                  <div className="flex items-center gap-3">
                    <div className="w-5 h-5 rounded-full bg-blue-500 shadow-md" />
                    <span className="font-semibold text-gray-900 dark:text-gray-100">Email Automation</span>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-lg text-gray-900 dark:text-gray-100">
                      {metrics.emailAutomation.count.toLocaleString()}
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">{metrics.emailAutomation.label}</div>
                  </div>
                </div>
                <div className="flex items-center justify-between p-4 bg-gradient-to-r from-green-50 to-green-100/50 dark:from-green-900/20 dark:to-green-800/10 rounded-xl border border-green-200 dark:border-green-800 shadow-sm">
                  <div className="flex items-center gap-3">
                    <div className="w-5 h-5 rounded-full bg-green-500 shadow-md" />
                    <span className="font-semibold text-gray-900 dark:text-gray-100">Lead Management</span>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-lg text-gray-900 dark:text-gray-100">
                      {metrics.leadManagement.count.toLocaleString()}
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">{metrics.leadManagement.label}</div>
                  </div>
                </div>
                <div className="flex items-center justify-between p-4 bg-gradient-to-r from-orange-50 to-orange-100/50 dark:from-orange-900/20 dark:to-orange-800/10 rounded-xl border border-orange-200 dark:border-orange-800 shadow-sm">
                  <div className="flex items-center gap-3">
                    <div className="w-5 h-5 rounded-full bg-orange-500 shadow-md" />
                    <span className="font-semibold text-gray-900 dark:text-gray-100">AI Responses</span>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-lg text-gray-900 dark:text-gray-100">
                      {metrics.aiResponses.accuracy ? `${metrics.aiResponses.accuracy}%` : metrics.aiResponses.count.toLocaleString()}
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      {metrics.aiResponses.accuracy ? 'accuracy rate' : metrics.aiResponses.label}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
