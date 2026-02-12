import React from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface ChartData {
  name: string
  emails?: number
  leads?: number
  responses?: number
}

interface EmailTrendsChartProps {
  data: ChartData[]
}

export const EmailTrendsChart: React.FC<EmailTrendsChartProps> = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        No data available
      </div>
    )
  }
  
  return (
    <ResponsiveContainer width="100%" height="100%" minHeight={256}>
      <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" opacity={0.3} />
        <XAxis 
          dataKey="name" 
          tick={{ fontSize: 12, fill: '#6B7280' }}
          tickLine={{ stroke: '#E5E7EB' }}
        />
        <YAxis 
          tick={{ fontSize: 12, fill: '#6B7280' }}
          tickLine={{ stroke: '#E5E7EB' }}
        />
        <Tooltip 
          contentStyle={{
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
          }}
        />
        <Line 
          type="monotone" 
          dataKey="emails" 
          stroke="#3B82F6" 
          strokeWidth={3}
          dot={{ fill: '#3B82F6', strokeWidth: 2, r: 4 }}
          activeDot={{ r: 6, stroke: '#3B82F6', strokeWidth: 2 }}
          name="Emails"
        />
        <Line 
          type="monotone" 
          dataKey="leads" 
          stroke="#10B981" 
          strokeWidth={3}
          dot={{ fill: '#10B981', strokeWidth: 2, r: 4 }}
          activeDot={{ r: 6, stroke: '#10B981', strokeWidth: 2 }}
          name="Leads"
        />
        <Line 
          type="monotone" 
          dataKey="responses" 
          stroke="#F59E0B" 
          strokeWidth={3}
          dot={{ fill: '#F59E0B', strokeWidth: 2, r: 4 }}
          activeDot={{ r: 6, stroke: '#F59E0B', strokeWidth: 2 }}
          name="AI Responses"
        />
      </LineChart>
    </ResponsiveContainer>
  )
}





