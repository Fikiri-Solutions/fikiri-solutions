import React from 'react'
import { CheckCircle, AlertCircle, Clock } from 'lucide-react'

interface Service {
  id: string
  name: string
  status: 'active' | 'inactive' | 'error'
  description: string
}

interface ServiceCardProps {
  service: Service
}

export const ServiceCard: React.FC<ServiceCardProps> = ({ service }) => {
  const getStatusIcon = () => {
    switch (service.status) {
      case 'active':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'error':
        return <AlertCircle className="h-5 w-5 text-red-500" />
      default:
        return <Clock className="h-5 w-5 text-gray-400" />
    }
  }

  const getStatusColor = () => {
    switch (service.status) {
      case 'active':
        return 'bg-green-100 text-green-800'
      case 'error':
        return 'bg-red-100 text-red-800'
      case 'inactive':
        return 'bg-yellow-100 text-yellow-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="card hover:shadow-md transition-shadow duration-200">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h3 className="text-sm font-medium text-gray-900">{service.name}</h3>
          <p className="mt-1 text-xs text-gray-600">{service.description}</p>
        </div>
        {getStatusIcon()}
      </div>
      <div className="mt-4">
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor()}`}>
          {service.status}
        </span>
      </div>
    </div>
  )
}

