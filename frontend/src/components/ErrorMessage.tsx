import React from 'react'
import { AlertCircle, CheckCircle, Info, X } from 'lucide-react'

export type ErrorType = 'error' | 'warning' | 'info' | 'success'

interface ErrorMessageProps {
  type: ErrorType
  title: string
  message: string
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

// Helper function to get user-friendly error messages
export const getUserFriendlyError = (error: any): { type: ErrorType; title: string; message: string } => {
  // Network errors
  if (error.code === 'NETWORK_ERROR' || error.message?.includes('fetch')) {
    return {
      type: 'error',
      title: 'Connection Error',
      message: 'Unable to connect to our servers. Please check your internet connection and try again.'
    }
  }

  // API errors
  if (error.status === 503 || error.message?.includes('503')) {
    return {
      type: 'warning',
      title: 'Service Temporarily Unavailable',
      message: 'This feature is currently being updated. Please try again in a few minutes.'
    }
  }

  if (error.status === 401 || error.message?.includes('401')) {
    return {
      type: 'warning',
      title: 'Authentication Required',
      message: 'Please sign in to access this feature.'
    }
  }

  if (error.status === 403 || error.message?.includes('403')) {
    return {
      type: 'error',
      title: 'Access Denied',
      message: 'You don\'t have permission to perform this action.'
    }
  }

  // Feature-specific errors
  if (error.message?.includes('API key') || error.message?.includes('OPENAI')) {
    return {
      type: 'warning',
      title: 'AI Assistant Configuration',
      message: 'The AI Assistant is being configured. This feature will be available shortly.'
    }
  }

  if (error.message?.includes('Gmail') || error.message?.includes('OAuth')) {
    return {
      type: 'info',
      title: 'Email Integration Setup',
      message: 'Please complete the Gmail integration setup to use email features.'
    }
  }

  // Generic errors
  if (error.message?.includes('validation') || error.message?.includes('required')) {
    return {
      type: 'warning',
      title: 'Invalid Input',
      message: 'Please check your input and try again.'
    }
  }

  // Default fallback
  return {
    type: 'error',
    title: 'Something went wrong',
    message: 'We encountered an unexpected error. Please try again or contact support if the problem persists.'
  }
}
