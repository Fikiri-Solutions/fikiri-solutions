import React from 'react'
import { Info, TrendingUp, AlertCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import { cn } from '../lib/utils'

interface BusinessImpactCardProps {
  title: string
  value: string | number
  description: string
  businessImpact: {
    label: string
    value: string | number
    positive?: boolean
  }
  insight?: string
  icon?: React.ReactNode
  color?: 'blue' | 'green' | 'purple' | 'orange'
  onClick?: () => void
}

export const BusinessImpactCard: React.FC<BusinessImpactCardProps> = ({
  title,
  value,
  description,
  businessImpact,
  insight,
  icon,
  color = 'blue',
  onClick
}) => {
  const colorClasses = {
    blue: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800',
    green: 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800',
    purple: 'bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800',
    orange: 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800'
  }

  const iconColorClasses = {
    blue: 'text-blue-600 dark:text-blue-400',
    green: 'text-green-600 dark:text-green-400',
    purple: 'text-purple-600 dark:text-purple-400',
    orange: 'text-orange-600 dark:text-orange-400'
  }

  return (
    <Card 
      className={cn(
        "group cursor-pointer transition-all duration-300 hover:shadow-lg hover:scale-[1.02]",
        colorClasses[color],
        "border-2"
      )}
      onClick={onClick}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3 flex-1">
            {icon && (
              <div className={cn("rounded-lg p-2", colorClasses[color])}>
                <div className={cn("h-5 w-5", iconColorClasses[color])}>
                  {icon}
                </div>
              </div>
            )}
            <div className="flex-1">
              <CardTitle className="text-lg font-bold text-gray-900 dark:text-white mb-1">
                {title}
              </CardTitle>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {description}
              </p>
            </div>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Main Value */}
        <div className="text-3xl font-bold text-gray-900 dark:text-white">
          {typeof value === 'number' ? value.toLocaleString() : value}
        </div>

        {/* Business Impact */}
        <div className={cn(
          "p-3 rounded-lg border",
          businessImpact.positive !== false 
            ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800"
            : "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800"
        )}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {businessImpact.positive !== false ? (
                <TrendingUp className="h-4 w-4 text-green-600 dark:text-green-400" />
              ) : (
                <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
              )}
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {businessImpact.label}
              </span>
            </div>
            <Badge 
              variant={businessImpact.positive !== false ? "default" : "destructive"}
              className={cn(
                "font-semibold",
                businessImpact.positive !== false
                  ? "bg-green-600 text-white"
                  : "bg-red-600 text-white"
              )}
            >
              {typeof businessImpact.value === 'number' 
                ? businessImpact.value.toLocaleString() 
                : businessImpact.value}
            </Badge>
          </div>
        </div>

        {/* Insight */}
        {insight && (
          <div className="flex items-start gap-2 p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
            <Info className="h-4 w-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-blue-800 dark:text-blue-200">
              {insight}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

