import React, { useState } from 'react'
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  BarChart, Bar, PieChart, Pie, Cell, AreaChart, Area
} from 'recharts'
import type { TooltipProps } from 'recharts'
import type { ValueType, NameType } from 'recharts/types/component/DefaultTooltipContent'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/Button"
import { 
  TrendingUp, BarChart3, PieChart as PieChartIcon, 
  Maximize2, Minimize2, RotateCcw
} from 'lucide-react'
import { cn } from "@/lib/utils"

export type ChartDatum = Record<string, string | number>

export interface ChartWidgetProps {
  title: string
  data: ChartDatum[]
  type: 'line' | 'bar' | 'pie' | 'area'
  dataKey: string
  color?: string
  className?: string
  compact?: boolean
  showControls?: boolean
}

const COLORS = {
  primary: '#3B82F6',
  secondary: '#8B5CF6', 
  success: '#22C55E',
  warning: '#F59E0B',
  error: '#EF4444',
  info: '#06B6D4'
}

export const ChartWidget: React.FC<ChartWidgetProps> = ({
  title,
  data,
  type,
  dataKey,
  color = COLORS.primary,
  className = "",
  compact = false,
  showControls = true
}) => {
  const [isExpanded, setIsExpanded] = useState(false)

  const CustomTooltip: React.FC<TooltipProps<ValueType, NameType>> = (props) => {
    const active = props.active
    const payload = (props as { payload?: Array<{ color?: string; dataKey?: string; value?: unknown }>; label?: string }).payload
    const label = (props as { label?: string }).label
    if (active && payload && payload.length) {
      return (
        <div className="bg-white dark:bg-gray-800 p-3 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg">
          <p className="font-semibold text-gray-900 dark:text-gray-100 mb-1">{label ?? ''}</p>
          {payload.map((entry, index) => (
            <div key={index} className="flex items-center gap-2">
              <div 
                className="w-2 h-2 rounded-full" 
                style={{ backgroundColor: entry?.color }}
              />
              <span className="text-sm text-gray-600 dark:text-gray-300">
                {entry?.dataKey}: <span className="font-semibold">{String(entry?.value ?? '')}</span>
              </span>
            </div>
          ))}
        </div>
      )
    }
    return null
  }

  const renderChart = () => {
    const height = compact ? (isExpanded ? 300 : 150) : 200
    const margin = compact ? { top: 5, right: 5, left: 5, bottom: 5 } : { top: 20, right: 30, left: 20, bottom: 20 }

    switch (type) {
      case 'line':
        return (
          <ResponsiveContainer width="100%" height={height}>
            <LineChart data={data} margin={margin}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" opacity={0.3} />
              <XAxis 
                dataKey="name" 
                tick={{ fontSize: compact ? 10 : 12, fill: '#6B7280' }}
                tickLine={{ stroke: '#E5E7EB' }}
                axisLine={{ stroke: '#E5E7EB' }}
              />
              <YAxis 
                tick={{ fontSize: compact ? 10 : 12, fill: '#6B7280' }}
                tickLine={{ stroke: '#E5E7EB' }}
                axisLine={{ stroke: '#E5E7EB' }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Line 
                type="monotone" 
                dataKey={dataKey} 
                stroke={color}
                strokeWidth={compact ? 2 : 3}
                dot={{ fill: color, strokeWidth: 2, r: compact ? 3 : 4 }}
                activeDot={{ r: compact ? 4 : 6, stroke: color, strokeWidth: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        )

      case 'bar':
        return (
          <ResponsiveContainer width="100%" height={height}>
            <BarChart data={data} margin={margin}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" opacity={0.3} />
              <XAxis 
                dataKey="name" 
                tick={{ fontSize: compact ? 10 : 12, fill: '#6B7280' }}
                tickLine={{ stroke: '#E5E7EB' }}
                axisLine={{ stroke: '#E5E7EB' }}
              />
              <YAxis 
                tick={{ fontSize: compact ? 10 : 12, fill: '#6B7280' }}
                tickLine={{ stroke: '#E5E7EB' }}
                axisLine={{ stroke: '#E5E7EB' }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar 
                dataKey={dataKey} 
                fill={`url(#${dataKey}Gradient)`}
                radius={[4, 4, 0, 0]}
              />
              <defs>
                <linearGradient id={`${dataKey}Gradient`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} />
                  <stop offset="100%" stopColor={color} stopOpacity={0.7} />
                </linearGradient>
              </defs>
            </BarChart>
          </ResponsiveContainer>
        )

      case 'area':
        return (
          <ResponsiveContainer width="100%" height={height}>
            <AreaChart data={data} margin={margin}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" opacity={0.3} />
              <XAxis 
                dataKey="name" 
                tick={{ fontSize: compact ? 10 : 12, fill: '#6B7280' }}
                tickLine={{ stroke: '#E5E7EB' }}
                axisLine={{ stroke: '#E5E7EB' }}
              />
              <YAxis 
                tick={{ fontSize: compact ? 10 : 12, fill: '#6B7280' }}
                tickLine={{ stroke: '#E5E7EB' }}
                axisLine={{ stroke: '#E5E7EB' }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area 
                type="monotone" 
                dataKey={dataKey} 
                stroke={color}
                fill={`url(#${dataKey}AreaGradient)`}
              />
              <defs>
                <linearGradient id={`${dataKey}AreaGradient`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={color} stopOpacity={0.8} />
                  <stop offset="95%" stopColor={color} stopOpacity={0.1} />
                </linearGradient>
              </defs>
            </AreaChart>
          </ResponsiveContainer>
        )

      case 'pie':
        return (
          <ResponsiveContainer width="100%" height={height}>
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }: { name?: string; percent?: number }) => compact ? `${((percent ?? 0) * 100).toFixed(0)}%` : `${name ?? ''} ${((percent ?? 0) * 100).toFixed(0)}%`}
                outerRadius={compact ? 60 : 80}
                innerRadius={compact ? 20 : 40}
                fill="#8884d8"
                dataKey={dataKey}
                animationDuration={500}
              >
                {data.map((_, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={color}
                    stroke="#fff"
                    strokeWidth={2}
                  />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        )

      default:
        return null
    }
  }

  const totalValue = data.reduce((sum, item) => sum + (Number(item[dataKey]) || 0), 0)
  const averageValue = data.length > 0 ? totalValue / data.length : 0

  return (
    <Card className={cn("transition-all duration-300 hover:shadow-lg", className)}>
      <CardHeader className={cn("pb-3", compact && "pb-2")}>
        <div className="flex items-center justify-between">
          <CardTitle className={cn("flex items-center gap-2", compact && "text-sm")}>
            {type === 'line' && <TrendingUp className="h-4 w-4" />}
            {type === 'bar' && <BarChart3 className="h-4 w-4" />}
            {type === 'pie' && <PieChartIcon className="h-4 w-4" />}
            {type === 'area' && <TrendingUp className="h-4 w-4" />}
            {title}
          </CardTitle>
          {showControls && (
            <div className="flex items-center gap-1">
              {compact && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsExpanded(!isExpanded)}
                >
                  {isExpanded ? <Minimize2 className="h-3 w-3" /> : <Maximize2 className="h-3 w-3" />}
                </Button>
              )}
              <Button variant="ghost" size="sm">
                <RotateCcw className="h-3 w-3" />
              </Button>
            </div>
          )}
        </div>
        {!compact && (
          <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
            <span>Total: <span className="font-semibold">{totalValue}</span></span>
            <span>Avg: <span className="font-semibold">{averageValue.toFixed(1)}</span></span>
          </div>
        )}
      </CardHeader>
      <CardContent className={cn("pt-0", compact && "pt-0")}>
        {renderChart()}
        {compact && (
          <div className="mt-2 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
            <span>Total: {totalValue}</span>
            <span>Avg: {averageValue.toFixed(1)}</span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// Compact Chart Grid Component
interface CompactChartGridProps {
  charts: Array<{
    title: string
    data: ChartDatum[]
    type: 'line' | 'bar' | 'pie' | 'area'
    dataKey: string
    color?: string
  }>
  className?: string
}

export const CompactChartGrid: React.FC<CompactChartGridProps> = ({ charts, className = "" }) => {
  return (
    <div className={cn("grid gap-4", 
      charts.length === 1 ? "grid-cols-1" :
      charts.length === 2 ? "grid-cols-1 md:grid-cols-2" :
      charts.length === 3 ? "grid-cols-1 md:grid-cols-2 lg:grid-cols-3" :
      "grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4",
      className
    )}>
      {charts.map((chart, index) => (
        <ChartWidget
          key={index}
          {...chart}
          compact={true}
          showControls={true}
        />
      ))}
    </div>
  )
}
