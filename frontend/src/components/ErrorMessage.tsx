import React from 'react'
import { AlertCircle, CheckCircle, Info, X } from 'lucide-react'

export type ErrorType = 'error' | 'warning' | 'info' | 'success'

interface ErrorMessageProps {
  type: ErrorType
  title: string
  message: string
  steps?: string[]
  onDismiss?: () => void
  className?: string
}

const errorConfig = {
  error: {
    icon: AlertCircle,
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    textColor: 'text-red-800',
    iconColor: 'text-red-600'
  },
  warning: {
    icon: AlertCircle,
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200',
    textColor: 'text-yellow-800',
    iconColor: 'text-yellow-600'
  },
  info: {
    icon: Info,
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    textColor: 'text-blue-800',
    iconColor: 'text-blue-600'
  },
  success: {
    icon: CheckCircle,
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    textColor: 'text-green-800',
    iconColor: 'text-green-600'
  }
}

export const ErrorMessage: React.FC<ErrorMessageProps> = ({
  type,
  title,
  message,
  steps,
  onDismiss,
  className = ''
}) => {
  const config = errorConfig[type]
  const Icon = config.icon

  return (
    <div className={`rounded-lg border p-4 ${config.bgColor} ${config.borderColor} ${className}`}>
      <div className="flex items-start">
        <Icon className={`h-5 w-5 ${config.iconColor} mt-0.5 mr-3 flex-shrink-0`} />
        <div className="flex-1">
          <h3 className={`text-sm font-medium ${config.textColor}`}>
            {title}
          </h3>
          <p className={`text-sm ${config.textColor} mt-1`}>
            {message}
          </p>
          {steps && steps.length > 0 && (
            <ol className={`text-sm ${config.textColor} mt-3 ml-4 list-decimal space-y-1`}>
              {steps.map((step, index) => (
                <li key={index}>{step}</li>
              ))}
            </ol>
          )}
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className={`ml-3 flex-shrink-0 ${config.textColor} hover:opacity-75`}
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  )
}

// Helper function to get user-friendly error messages (now uses centralized errorMessages.ts)
export const getUserFriendlyError = (error: any): { type: ErrorType; title: string; message: string; steps?: string[] } => {
  const { getFriendlyError } = require('../utils/errorMessages')
  const friendly = getFriendlyError(error)
  return {
    type: friendly.type,
    title: friendly.title,
    message: friendly.message,
    steps: friendly.steps
  }
}
