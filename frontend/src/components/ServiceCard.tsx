import React from 'react'
import { StatusIcon, getStatusColor, getStatusText, StatusType } from './StatusIcon'

interface Service {
  id: string
  name: string
  status: StatusType
  description: string
}

interface ServiceCardProps {
  service: Service
}

export const ServiceCard: React.FC<ServiceCardProps> = ({ service }) => {

  return (
    <div className="card hover:shadow-md transition-shadow duration-200">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h3 className="text-sm font-medium text-gray-900">{service.name}</h3>
          <p className="mt-1 text-xs text-gray-600">{service.description}</p>
        </div>
        <StatusIcon status={service.status} />
      </div>
      <div className="mt-4">
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(service.status)}`}>
          {getStatusText(service.status)}
        </span>
      </div>
    </div>
  )
}

