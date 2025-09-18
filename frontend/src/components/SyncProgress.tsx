import React, { useState, useEffect } from 'react'
import { CheckCircle, Database, Users, Zap, Settings, Loader2, AlertCircle } from 'lucide-react'

interface SyncProgressProps {
  userId: number
  onComplete: () => void
}

interface SyncStatus {
  status: string
  current_step: string
  progress: number
  started_at: string
  completed_at?: string
  error_message?: string
}

export const SyncProgress: React.FC<SyncProgressProps> = ({ userId, onComplete }) => {
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    pollSyncStatus()
    const interval = setInterval(pollSyncStatus, 2000)
    return () => clearInterval(interval)
  }, [userId])

  const pollSyncStatus = async () => {
    try {
      const response = await fetch(`https://fikirisolutions.onrender.com/api/email/sync/status?user_id=${userId}`)
      const data = await response.json()
      
      if (data.success) {
        setSyncStatus(data.data)
        setIsLoading(false)
        
        if (data.data.status === 'completed') {
          onComplete()
        } else if (data.data.status === 'failed') {
          setError(data.data.error_message || 'Sync failed')
        }
      }
    } catch (error) {
      console.error('Error polling sync status:', error)
      setError('Failed to check sync status')
      setIsLoading(false)
    }
  }

  const getStepIcon = (step: string, completed: boolean) => {
    if (completed) {
      return <CheckCircle className="h-5 w-5 text-green-600" />
    }
    
    switch (step) {
      case 'gmail_sync':
        return <Database className="h-5 w-5 text-blue-600" />
      case 'lead_extraction':
        return <Users className="h-5 w-5 text-purple-600" />
      case 'starter_automations':
        return <Zap className="h-5 w-5 text-yellow-600" />
      case 'dashboard_seeding':
        return <Settings className="h-5 w-5 text-gray-600" />
      default:
        return <Loader2 className="h-5 w-5 text-gray-400 animate-spin" />
    }
  }

  const getStepTitle = (step: string) => {
    switch (step) {
      case 'gmail_sync':
        return 'Syncing Gmail emails'
      case 'lead_extraction':
        return 'Extracting leads and contacts'
      case 'starter_automations':
        return 'Creating starter automations'
      case 'dashboard_seeding':
        return 'Preparing your dashboard'
      default:
        return 'Processing...'
    }
  }

  const getStepDescription = (step: string) => {
    switch (step) {
      case 'gmail_sync':
        return 'Downloading your recent emails and organizing them'
      case 'lead_extraction':
        return 'Identifying potential customers and business contacts'
      case 'starter_automations':
        return 'Setting up helpful automation rules'
      case 'dashboard_seeding':
        return 'Creating your personalized dashboard'
      default:
        return 'Please wait while we set up your workspace'
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <div className="mx-auto w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
            <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Preparing your workspace</h2>
          <p className="text-gray-600">Please wait while we set everything up</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <div className="mx-auto w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
            <AlertCircle className="h-8 w-8 text-red-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Setup Failed</h2>
          <p className="text-gray-600">{error}</p>
        </div>
        
        <div className="text-center">
          <button
            onClick={() => window.location.reload()}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  if (!syncStatus) {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <div className="mx-auto w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
            <Database className="h-8 w-8 text-gray-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Ready to sync</h2>
          <p className="text-gray-600">Click below to start syncing your Gmail</p>
        </div>
        
        <div className="text-center">
          <button
            onClick={() => window.location.reload()}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Start Sync
          </button>
        </div>
      </div>
    )
  }

  const steps = [
    { key: 'gmail_sync', title: 'Syncing Gmail emails', description: 'Downloading your recent emails and organizing them' },
    { key: 'lead_extraction', title: 'Extracting leads and contacts', description: 'Identifying potential customers and business contacts' },
    { key: 'starter_automations', title: 'Creating starter automations', description: 'Setting up helpful automation rules' },
    { key: 'dashboard_seeding', title: 'Preparing your dashboard', description: 'Creating your personalized dashboard' }
  ]

  const currentStepIndex = steps.findIndex(step => step.key === syncStatus.current_step)
  const completedSteps = Math.floor((syncStatus.progress / 100) * steps.length)

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="mx-auto w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
          <Database className="h-8 w-8 text-blue-600" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Setting up your workspace</h2>
        <p className="text-gray-600">We're preparing your dashboard with your data</p>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-gray-200 rounded-full h-3">
        <div
          className="bg-blue-600 h-3 rounded-full transition-all duration-500"
          style={{ width: `${syncStatus.progress}%` }}
        />
      </div>
      
      <div className="text-center">
        <p className="text-sm text-gray-600">
          {syncStatus.progress}% complete - {getStepTitle(syncStatus.current_step)}
        </p>
      </div>

      {/* Step Indicators */}
      <div className="space-y-4">
        {steps.map((step, index) => {
          const isCompleted = index < completedSteps
          const isCurrent = index === currentStepIndex
          const isPending = index > currentStepIndex

          return (
            <div
              key={step.key}
              className={`flex items-center p-4 rounded-lg border transition-colors ${
                isCurrent
                  ? 'border-blue-200 bg-blue-50'
                  : isCompleted
                  ? 'border-green-200 bg-green-50'
                  : 'border-gray-200 bg-gray-50'
              }`}
            >
              <div className={`w-8 h-8 rounded-full flex items-center justify-center mr-4 ${
                isCompleted
                  ? 'bg-green-100'
                  : isCurrent
                  ? 'bg-blue-100'
                  : 'bg-gray-100'
              }`}>
                {getStepIcon(step.key, isCompleted)}
              </div>
              
              <div className="flex-1">
                <h3 className={`font-medium ${
                  isCompleted
                    ? 'text-green-900'
                    : isCurrent
                    ? 'text-blue-900'
                    : 'text-gray-700'
                }`}>
                  {step.title}
                </h3>
                <p className={`text-sm ${
                  isCompleted
                    ? 'text-green-700'
                    : isCurrent
                    ? 'text-blue-700'
                    : 'text-gray-600'
                }`}>
                  {step.description}
                </p>
              </div>
              
              {isCurrent && (
                <div className="ml-4">
                  <Loader2 className="h-5 w-5 text-blue-600 animate-spin" />
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Time Estimate */}
      <div className="text-center text-sm text-gray-500">
        <p>Estimated time remaining: {Math.max(1, Math.ceil((100 - syncStatus.progress) / 10))} minutes</p>
      </div>

      {/* What We're Not Doing */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <h4 className="font-medium text-yellow-900 mb-2">What we will not do:</h4>
        <ul className="text-sm text-yellow-800 space-y-1">
          <li>• Read your personal emails</li>
          <li>• Send emails without your permission</li>
          <li>• Share your data with third parties</li>
          <li>• Store your Gmail password</li>
        </ul>
      </div>

      {/* Support Link */}
      <div className="text-center">
        <a
          href="mailto:support@fikirisolutions.com"
          className="text-sm text-blue-600 hover:text-blue-700"
        >
          Need help? Contact Support
        </a>
      </div>
    </div>
  )
}