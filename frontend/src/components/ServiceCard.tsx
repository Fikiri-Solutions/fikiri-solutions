import React from 'react'
import { StatusIcon, getStatusColor, getStatusText, StatusType } from './StatusIcon'

interface Service {
  id: string
  name: string
  status: StatusType | string
  description: string
}

interface ServiceCardProps {
  service: Service
}

export const ServiceCard: React.FC<ServiceCardProps> = ({ service }) => {
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
    <div className="card hover:shadow-md transition-shadow duration-200">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h3 className="text-sm font-medium text-gray-900">{service.name}</h3>
          <p className="mt-1 text-xs text-gray-600">{service.description}</p>
        </div>
        <StatusIcon status={statusType} />
      </div>
      <div className="mt-4">
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(statusType)}`}>
          {getStatusText(statusType)}
        </span>
      </div>
    </div>
  )
}

