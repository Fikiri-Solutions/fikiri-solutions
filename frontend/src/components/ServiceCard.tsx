import React from 'react'
import { StatusIcon, getStatusColor, getStatusText, StatusType } from './StatusIcon'
import { cn } from '@/lib/utils'

interface Service {
  id: string
  name: string
  status: StatusType | string
  description: string
}

interface ServiceCardProps {
  service: Service
  compact?: boolean
}

export const ServiceCard: React.FC<ServiceCardProps> = ({ service, compact = false }) => {
  // Convert string status to StatusType
  const getStatusType = (status: string | StatusType): StatusType => {
    if (typeof status === 'string') {
      switch (status.toLowerCase()) {
        case 'active':
        case 'healthy':
          return 'active'
        case 'inactive':
        case 'unhealthy':
          return 'inactive'
        case 'error':
          return 'error'
        case 'warning':
          return 'warning'
        case 'loading':
          return 'loading'
        default:
          return 'inactive'
      }
    }
    return status
  }

  const statusType = getStatusType(service.status)

  return (
    <div className={cn("card hover:shadow-md transition-shadow duration-200", compact && "p-2")}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h3 className={cn("font-medium text-gray-900 dark:text-white", compact ? "text-xs" : "text-sm")}>{service.name}</h3>
          {!compact && (
            <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">{service.description}</p>
          )}
        </div>
        <StatusIcon status={statusType} />
      </div>
      {!compact && (
        <div className="mt-4">
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(statusType)}`}>
            {getStatusText(statusType)}
          </span>
        </div>
      )}
    </div>
  )
}

