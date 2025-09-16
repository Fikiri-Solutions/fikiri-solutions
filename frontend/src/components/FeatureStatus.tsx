import React from 'react'
import { CheckCircle, Clock, AlertCircle, Loader } from 'lucide-react'

export type FeatureStatus = 'live' | 'beta' | 'coming-soon' | 'maintenance'

interface FeatureStatusProps {
  status: FeatureStatus
  className?: string
}

const statusConfig = {
  live: {
    icon: CheckCircle,
    text: 'Live',
    color: 'text-green-600',
    bgColor: 'bg-green-100',
    iconColor: 'text-green-600'
  },
  beta: {
    icon: Loader,
    text: 'Beta',
    color: 'text-blue-600',
    bgColor: 'bg-blue-100',
    iconColor: 'text-blue-600'
  },
  'coming-soon': {
    icon: Clock,
    text: 'Coming Soon',
    color: 'text-orange-600',
    bgColor: 'bg-orange-100',
    iconColor: 'text-orange-600'
  },
  maintenance: {
    icon: AlertCircle,
    text: 'Maintenance',
    color: 'text-red-600',
    bgColor: 'bg-red-100',
    iconColor: 'text-red-600'
  }
}

export const FeatureStatus: React.FC<FeatureStatusProps> = ({ status, className = '' }) => {
  const config = statusConfig[status]
  const Icon = config.icon

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${config.bgColor} ${config.color} ${className}`}>
      <Icon className={`h-3 w-3 ${config.iconColor}`} />
      {config.text}
    </span>
  )
}

// Feature status mapping based on current backend status
export const getFeatureStatus = (feature: string): FeatureStatus => {
  const statusMap: Record<string, FeatureStatus> = {
    'ai-assistant': 'beta', // Working but needs API key configuration
    'crm': 'beta', // Working but some endpoints may be unstable
    'email-parser': 'beta', // Working but needs Gmail authentication
    'automation': 'beta', // Working but needs full configuration
    'feature-flags': 'live', // Fully working
    'auth': 'beta', // Working but needs OAuth setup
    'analytics': 'coming-soon', // Not fully implemented
    'integrations': 'coming-soon' // Limited integrations available
  }
  
  return statusMap[feature] || 'beta'
}
