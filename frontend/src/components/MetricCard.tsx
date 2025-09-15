import React from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'

interface MetricCardProps {
  title: string
  value: string | number
  icon: React.ComponentType<{ className?: string }>
  change?: string
  changeType?: 'positive' | 'negative'
  onClick?: () => void
}

export const MetricCard: React.FC<MetricCardProps> = ({ 
  title, 
  value, 
  icon: Icon, 
  change, 
  changeType = 'positive',
  onClick
}) => {
  return (
    <div className="card cursor-pointer hover:shadow-md transition-shadow duration-200" onClick={onClick}>
      <div className="flex items-center">
        <div className="flex-shrink-0">
          <Icon className="h-6 w-6 text-gray-400" />
        </div>
        <div className="ml-4 w-0 flex-1">
          <dl>
            <dt className="text-sm font-medium text-gray-500 truncate">{title}</dt>
            <dd className="flex items-baseline">
              <div className="text-2xl font-semibold text-gray-900">{value}</div>
              {change && (
                <div className={`ml-2 flex items-baseline text-sm font-semibold ${
                  changeType === 'positive' ? 'text-green-600' : 'text-red-600'
                }`}>
                  {changeType === 'positive' ? (
                    <TrendingUp className="h-4 w-4 flex-shrink-0 self-center" />
                  ) : (
                    <TrendingDown className="h-4 w-4 flex-shrink-0 self-center" />
                  )}
                  <span className="sr-only">{changeType === 'positive' ? 'Increased' : 'Decreased'} by</span>
                  {change}
                </div>
              )}
            </dd>
          </dl>
        </div>
      </div>
    </div>
  )
}

