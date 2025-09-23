import React, { useState } from 'react'
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  BarChart, Bar, PieChart, Pie, Cell, AreaChart, Area, Legend,
  ReferenceLine, Brush
} from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/Button"
import { 
  TrendingUp, TrendingDown, BarChart3, PieChart as PieChartIcon, 
  Calendar, Filter, Download, Maximize2, RefreshCw, Eye, EyeOff
} from 'lucide-react'
import { cn } from "@/lib/utils"

interface ChartData {
  name: string
  value: number
  emails?: number
  leads?: number
  responses?: number
  revenue?: number
  timestamp?: string
}

interface DashboardChartsProps {
  data: ChartData[]
  pieData?: Array<{
    name: string;
    value: number;
    color: string;
  }>;
}

const COLORS = {
  primary: '#3B82F6',
  secondary: '#8B5CF6', 
  success: '#22C55E',
  warning: '#F59E0B',
  error: '#EF4444',
  info: '#06B6D4'
}

const GRADIENT_COLORS = [
  { start: '#3B82F6', end: '#1D4ED8' },
  { start: '#22C55E', end: '#16A34A' },
  { start: '#F59E0B', end: '#D97706' },
  { start: '#EF4444', end: '#DC2626' },
  { start: '#8B5CF6', end: '#7C3AED' }
]

export const EnhancedDashboardCharts: React.FC<DashboardChartsProps> = ({ data, pieData = [] }) => {
  const [activeChart, setActiveChart] = useState<'line' | 'bar' | 'area'>('line')
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('7d')
  const [showLegend, setShowLegend] = useState(true)
  const [isFullscreen, setIsFullscreen] = useState(false)

  // Filter data based on time range
  const getFilteredData = (data: any[], range: '7d' | '30d' | '90d') => {
    if (!data || data.length === 0) return data
    
    const now = new Date()
    const daysBack = range === '7d' ? 7 : range === '30d' ? 30 : 90
    const cutoffDate = new Date(now.getTime() - (daysBack * 24 * 60 * 60 * 1000))
    
    return data.filter(item => {
      if (item.day) {
        return new Date(item.day) >= cutoffDate
      }
      // For data without day field, return all data
      return true
    })
  }

  const filteredData = getFilteredData(data, timeRange)

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white dark:bg-gray-800 p-4 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg">
          <p className="font-semibold text-gray-900 dark:text-gray-100 mb-2">{label}</p>
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex items-center gap-2 mb-1">
              <div 
                className="w-3 h-3 rounded-full" 
                style={{ backgroundColor: entry.color }}
              />
              <span className="text-sm text-gray-600 dark:text-gray-300">
                {entry.dataKey}: <span className="font-semibold">{entry.value}</span>
              </span>
            </div>
          ))}
        </div>
      )
    }
    return null
  }

  const CustomPieTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0]
      return (
        <div className="bg-white dark:bg-gray-800 p-3 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg">
          <p className="font-semibold text-gray-900 dark:text-gray-100">{data.name}</p>
          <p className="text-sm text-gray-600 dark:text-gray-300">
            Value: <span className="font-semibold">{data.value}</span>
          </p>
          <p className="text-sm text-gray-600 dark:text-gray-300">
            Percentage: <span className="font-semibold">{((data.payload.percent || 0) * 100).toFixed(1)}%</span>
          </p>
        </div>
      )
    }
    return null
  }

  const calculateTrend = (data: ChartData[], key: string) => {
    if (data.length < 2) return { direction: 'neutral', percentage: 0 }
    const first = data[0][key as keyof ChartData] as number || 0
    const last = data[data.length - 1][key as keyof ChartData] as number || 0
    const percentage = first > 0 ? ((last - first) / first) * 100 : 0
    return {
      direction: percentage > 0 ? 'up' : percentage < 0 ? 'down' : 'neutral',
      percentage: Math.abs(percentage)
    }
  }

  const emailTrend = calculateTrend(data, 'emails')
  const leadTrend = calculateTrend(data, 'leads')
  const responseTrend = calculateTrend(data, 'responses')

  return (
    <div className="space-y-6">
      {/* Interactive Chart Controls */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-brand-primary" />
                Analytics Dashboard
              </CardTitle>
              <CardDescription>
                Interactive charts with real-time data visualization
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowLegend(!showLegend)}
              >
                {showLegend ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsFullscreen(!isFullscreen)}
              >
                <Maximize2 className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="sm">
                <Download className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4 mb-6">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-gray-500" />
              <span className="text-sm font-medium">Time Range:</span>
              <div className="flex gap-1">
                {(['7d', '30d', '90d'] as const).map((range) => (
                  <Button
                    key={range}
                    variant={timeRange === range ? "default" : "outline"}
                    size="sm"
                    onClick={() => setTimeRange(range)}
                  >
                    {range}
                  </Button>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Chart Type:</span>
              <div className="flex gap-1">
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
                  >
                    <Icon className="h-4 w-4 mr-1" />
                    {label}
                  </Button>
                ))}
              </div>
            </div>
          </div>

          {/* Trend Indicators */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="flex items-center justify-between p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <div>
                <p className="text-sm font-medium text-blue-900 dark:text-blue-100">Email Trends</p>
                <div className="flex items-center gap-1">
                  {emailTrend.direction === 'up' ? (
                    <TrendingUp className="h-4 w-4 text-green-500" />
                  ) : emailTrend.direction === 'down' ? (
                    <TrendingDown className="h-4 w-4 text-red-500" />
                  ) : (
                    <div className="h-4 w-4 bg-gray-400 rounded-full" />
                  )}
                  <span className="text-sm font-semibold text-blue-900 dark:text-blue-100">
                    {emailTrend.percentage.toFixed(1)}%
                  </span>
                </div>
              </div>
              <Badge variant="secondary" className="bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100">
                {data.reduce((sum, d) => sum + (d.emails || 0), 0)}
              </Badge>
            </div>

            <div className="flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
              <div>
                <p className="text-sm font-medium text-green-900 dark:text-green-100">Lead Trends</p>
                <div className="flex items-center gap-1">
                  {leadTrend.direction === 'up' ? (
                    <TrendingUp className="h-4 w-4 text-green-500" />
                  ) : leadTrend.direction === 'down' ? (
                    <TrendingDown className="h-4 w-4 text-red-500" />
                  ) : (
                    <div className="h-4 w-4 bg-gray-400 rounded-full" />
                  )}
                  <span className="text-sm font-semibold text-green-900 dark:text-green-100">
                    {leadTrend.percentage.toFixed(1)}%
                  </span>
                </div>
              </div>
              <Badge variant="secondary" className="bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100">
                {data.reduce((sum, d) => sum + (d.leads || 0), 0)}
              </Badge>
            </div>

            <div className="flex items-center justify-between p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
              <div>
                <p className="text-sm font-medium text-orange-900 dark:text-orange-100">Response Trends</p>
                <div className="flex items-center gap-1">
                  {responseTrend.direction === 'up' ? (
                    <TrendingUp className="h-4 w-4 text-green-500" />
                  ) : responseTrend.direction === 'down' ? (
                    <TrendingDown className="h-4 w-4 text-red-500" />
                  ) : (
                    <div className="h-4 w-4 bg-gray-400 rounded-full" />
                  )}
                  <span className="text-sm font-semibold text-orange-900 dark:text-orange-100">
                    {responseTrend.percentage.toFixed(1)}%
                  </span>
                </div>
              </div>
              <Badge variant="secondary" className="bg-orange-100 text-orange-800 dark:bg-orange-800 dark:text-orange-100">
                {data.reduce((sum, d) => sum + (d.responses || 0), 0)}
              </Badge>
            </div>
          </div>

          {/* Main Interactive Chart */}
          <Card className="border-2 border-dashed border-gray-200 dark:border-gray-700">
            <CardContent className="p-6">
              <div className="h-96">
                <ResponsiveContainer width="100%" height="100%">
                  {activeChart === 'line' ? (
                    <LineChart data={filteredData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" opacity={0.3} />
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
                      {showLegend && <Legend />}
                      <Line 
                        type="monotone" 
                        dataKey="emails" 
                        stroke={COLORS.primary}
                        strokeWidth={3}
                        dot={{ fill: COLORS.primary, strokeWidth: 2, r: 4 }}
                        activeDot={{ r: 6, stroke: COLORS.primary, strokeWidth: 2 }}
                        name="Emails"
                      />
                      <Line 
                        type="monotone" 
                        dataKey="leads" 
                        stroke={COLORS.success}
                        strokeWidth={3}
                        dot={{ fill: COLORS.success, strokeWidth: 2, r: 4 }}
                        activeDot={{ r: 6, stroke: COLORS.success, strokeWidth: 2 }}
                        name="Leads"
                      />
                      <Line 
                        type="monotone" 
                        dataKey="responses" 
                        stroke={COLORS.warning}
                        strokeWidth={3}
                        dot={{ fill: COLORS.warning, strokeWidth: 2, r: 4 }}
                        activeDot={{ r: 6, stroke: COLORS.warning, strokeWidth: 2 }}
                        name="Responses"
                      />
                      <Brush dataKey="name" height={30} stroke="#8884d8" />
                    </LineChart>
                  ) : activeChart === 'bar' ? (
                    <BarChart data={filteredData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" opacity={0.3} />
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
                      {showLegend && <Legend />}
                      <Bar 
                        dataKey="emails" 
                        fill="url(#emailGradient)"
                        radius={[4, 4, 0, 0]}
                        name="Emails"
                      />
                      <Bar 
                        dataKey="leads" 
                        fill="url(#leadGradient)"
                        radius={[4, 4, 0, 0]}
                        name="Leads"
                      />
                      <Bar 
                        dataKey="responses" 
                        fill="url(#responseGradient)"
                        radius={[4, 4, 0, 0]}
                        name="Responses"
                      />
                      <defs>
                        <linearGradient id="emailGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor={COLORS.primary} />
                          <stop offset="100%" stopColor="#1D4ED8" />
                        </linearGradient>
                        <linearGradient id="leadGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor={COLORS.success} />
                          <stop offset="100%" stopColor="#16A34A" />
                        </linearGradient>
                        <linearGradient id="responseGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor={COLORS.warning} />
                          <stop offset="100%" stopColor="#D97706" />
                        </linearGradient>
                      </defs>
                    </BarChart>
                  ) : (
                    <AreaChart data={filteredData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" opacity={0.3} />
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
                      {showLegend && <Legend />}
                      <Area 
                        type="monotone" 
                        dataKey="emails" 
                        stackId="1"
                        stroke={COLORS.primary}
                        fill="url(#emailAreaGradient)"
                        name="Emails"
                      />
                      <Area 
                        type="monotone" 
                        dataKey="leads" 
                        stackId="1"
                        stroke={COLORS.success}
                        fill="url(#leadAreaGradient)"
                        name="Leads"
                      />
                      <Area 
                        type="monotone" 
                        dataKey="responses" 
                        stackId="1"
                        stroke={COLORS.warning}
                        fill="url(#responseAreaGradient)"
                        name="Responses"
                      />
                      <defs>
                        <linearGradient id="emailAreaGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={COLORS.primary} stopOpacity={0.8} />
                          <stop offset="95%" stopColor={COLORS.primary} stopOpacity={0.1} />
                        </linearGradient>
                        <linearGradient id="leadAreaGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={COLORS.success} stopOpacity={0.8} />
                          <stop offset="95%" stopColor={COLORS.success} stopOpacity={0.1} />
                        </linearGradient>
                        <linearGradient id="responseAreaGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={COLORS.warning} stopOpacity={0.8} />
                          <stop offset="95%" stopColor={COLORS.warning} stopOpacity={0.1} />
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

      {/* Service Performance Overview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PieChartIcon className="h-5 w-5 text-brand-secondary" />
            Service Performance Overview
          </CardTitle>
          <CardDescription>
            Performance metrics across different service categories
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={[
                      { name: 'Email Automation', value: 45, color: '#3b82f6' },
                      { name: 'Lead Management', value: 30, color: '#22c55e' },
                      { name: 'AI Responses', value: 25, color: '#f97316' }
                    ]}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }: any) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={100}
                    innerRadius={40}
                    fill="#8884d8"
                    dataKey="value"
                    animationDuration={500}
                    animationBegin={0}
                  >
                    {[
                      { name: 'Email Automation', value: 45, color: '#3b82f6' },
                      { name: 'Lead Management', value: 30, color: '#22c55e' },
                      { name: 'AI Responses', value: 25, color: '#f97316' }
                    ].map((entry, index) => (
                      <Cell 
                        key={`cell-${index}`} 
                        fill={entry.color}
                        stroke="#fff"
                        strokeWidth={2}
                      />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomPieTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-4">
              <div className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-3">
                Performance Metrics (Last 30 Days)
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="w-4 h-4 rounded-full bg-blue-500" />
                    <span className="font-medium text-gray-900 dark:text-gray-100">Email Automation</span>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold text-gray-900 dark:text-gray-100">1,247</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">emails processed</div>
                  </div>
                </div>
                <div className="flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="w-4 h-4 rounded-full bg-green-500" />
                    <span className="font-medium text-gray-900 dark:text-gray-100">Lead Management</span>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold text-gray-900 dark:text-gray-100">89</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">new leads</div>
                  </div>
                </div>
                <div className="flex items-center justify-between p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="w-4 h-4 rounded-full bg-orange-500" />
                    <span className="font-medium text-gray-900 dark:text-gray-100">AI Responses</span>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold text-gray-900 dark:text-gray-100">94.2%</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">accuracy rate</div>
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
