import React from 'react'
import { CheckCircle, AlertCircle, Clock, XCircle, Loader } from 'lucide-react'

export type StatusType = 'active' | 'inactive' | 'error' | 'loading' | 'warning'

interface StatusIconProps {
  status: StatusType
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const sizeClasses = {
  sm: 'h-4 w-4',
  md: 'h-5 w-5',
  lg: 'h-6 w-6'
}

export const StatusIcon: React.FC<StatusIconProps> = ({ 
  status, 
  size = 'md', 
  className = '' 
}) => {
  const baseClasses = `${sizeClasses[size]} ${className}`
  
  switch (status) {
    case 'active':
      return <CheckCircle className={`${baseClasses} text-green-500`} />
    case 'error':
      return <XCircle className={`${baseClasses} text-red-500`} />
    case 'warning':
      return <AlertCircle className={`${baseClasses} text-yellow-500`} />
    case 'loading':
      return <Loader className={`${baseClasses} text-blue-500 animate-spin`} />
    case 'inactive':
    default:
      return <Clock className={`${baseClasses} text-gray-400`} />
  }
}

export const getStatusColor = (status: StatusType): string => {
  switch (status) {
    case 'active':
      return 'bg-green-100 text-green-800'
    case 'error':
      return 'bg-red-100 text-red-800'
    case 'warning':
      return 'bg-yellow-100 text-yellow-800'
    case 'loading':
      return 'bg-blue-100 text-blue-800'
    case 'inactive':
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

export const getStatusText = (status: StatusType): string => {
  switch (status) {
    case 'active':
      return 'Active'
    case 'error':
      return 'Error'
    case 'warning':
      return 'Warning'
    case 'loading':
      return 'Loading'
    case 'inactive':
    default:
      return 'Inactive'
  }
}
