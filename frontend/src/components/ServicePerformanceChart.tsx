import React from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { chartTickStyle } from '../lib/brandTypography'

interface ChartData {
  name: string
  value?: number
  emails?: number
  leads?: number
  responses?: number
}

interface ServicePerformanceChartProps {
  data: ChartData[]
}

export const ServicePerformanceChart: React.FC<ServicePerformanceChartProps> = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        No data available
      </div>
    )
  }
  
  return (
    <ResponsiveContainer width="100%" height="100%" minHeight={256} className="fikiri-chart">
      <BarChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" opacity={0.3} />
        <XAxis 
          dataKey="name" 
          tick={chartTickStyle()}
          tickLine={{ stroke: '#E5E7EB' }}
        />
        <YAxis 
          tick={chartTickStyle()}
          tickLine={{ stroke: '#E5E7EB' }}
        />
        <Tooltip 
          contentStyle={{
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
            fontFamily: '"Source Serif 4", Georgia, "Times New Roman", serif',
          }}
        />
        <defs>
          <linearGradient id="servicePerformanceGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3B82F6" />
            <stop offset="100%" stopColor="#1D4ED8" />
          </linearGradient>
        </defs>
        <Bar 
          dataKey="value" 
          fill="url(#servicePerformanceGradient)"
          radius={[4, 4, 0, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  )
}

