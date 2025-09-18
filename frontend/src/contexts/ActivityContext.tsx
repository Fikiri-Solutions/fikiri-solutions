import React, { createContext, useContext, useEffect, useState } from 'react'

export interface ActivityItem {
  id: string
  type: 'user_login' | 'user_logout' | 'onboarding_started' | 'onboarding_completed' | 'profile_updated' | 'service_configured' | 'ai_response' | 'lead_added' | 'email_processed' | 'service_error' | 'system_update'
  message: string
  timestamp: string
  status: 'success' | 'warning' | 'error' | 'info'
  userId?: string
  metadata?: Record<string, any>
}

interface ActivityContextType {
  activities: ActivityItem[]
  addActivity: (activity: Omit<ActivityItem, 'id' | 'timestamp'>) => void
  clearActivities: () => void
  getRecentActivities: (limit?: number) => ActivityItem[]
}

const ActivityContext = createContext<ActivityContextType | undefined>(undefined)

export const useActivity = () => {
  const context = useContext(ActivityContext)
  if (!context) {
    throw new Error('useActivity must be used within an ActivityProvider')
  }
  return context
}

interface ActivityProviderProps {
  children: React.ReactNode
}

export const ActivityProvider: React.FC<ActivityProviderProps> = ({ children }) => {
  const [activities, setActivities] = useState<ActivityItem[]>([])

  // Load activities from localStorage on mount
  useEffect(() => {
    const savedActivities = localStorage.getItem('fikiri-activities')
    if (savedActivities) {
      try {
        const parsed = JSON.parse(savedActivities)
        setActivities(parsed)
      } catch (error) {
        console.error('Failed to parse saved activities:', error)
      }
    }
  }, [])

  // Save activities to localStorage whenever activities change
  useEffect(() => {
    localStorage.setItem('fikiri-activities', JSON.stringify(activities))
  }, [activities])

  const addActivity = (activity: Omit<ActivityItem, 'id' | 'timestamp'>) => {
    const newActivity: ActivityItem = {
      ...activity,
      id: `activity_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toLocaleString()
    }

    setActivities(prev => [newActivity, ...prev.slice(0, 49)]) // Keep last 50 activities
  }

  const clearActivities = () => {
    setActivities([])
    localStorage.removeItem('fikiri-activities')
  }

  const getRecentActivities = (limit: number = 10) => {
    return activities.slice(0, limit)
  }

  return (
    <ActivityContext.Provider value={{
      activities,
      addActivity,
      clearActivities,
      getRecentActivities
    }}>
      {children}
    </ActivityContext.Provider>
  )
}

// Activity tracking hooks for specific user actions
export const useUserActivityTracking = () => {
  const { addActivity } = useActivity()

  const trackLogin = (userId?: string, method?: string) => {
    addActivity({
      type: 'user_login',
      message: `User logged in${method ? ` via ${method}` : ''}`,
      status: 'success',
      userId,
      metadata: { method }
    })
  }

  const trackLogout = (userId?: string) => {
    addActivity({
      type: 'user_logout',
      message: 'User logged out',
      status: 'info',
      userId
    })
  }

  const trackOnboardingStart = (userId?: string, step?: string) => {
    addActivity({
      type: 'onboarding_started',
      message: `Onboarding started${step ? ` - ${step}` : ''}`,
      status: 'info',
      userId,
      metadata: { step }
    })
  }

  const trackOnboardingComplete = (userId?: string, stepsCompleted?: number) => {
    addActivity({
      type: 'onboarding_completed',
      message: `Onboarding completed${stepsCompleted ? ` (${stepsCompleted} steps)` : ''}`,
      status: 'success',
      userId,
      metadata: { stepsCompleted }
    })
  }

  const trackProfileUpdate = (userId?: string, fields?: string[]) => {
    addActivity({
      type: 'profile_updated',
      message: `Profile updated${fields ? ` - ${fields.join(', ')}` : ''}`,
      status: 'success',
      userId,
      metadata: { fields }
    })
  }

  const trackServiceConfiguration = (userId?: string, serviceName?: string) => {
    addActivity({
      type: 'service_configured',
      message: `Service configured${serviceName ? ` - ${serviceName}` : ''}`,
      status: 'success',
      userId,
      metadata: { serviceName }
    })
  }

  const trackAIResponse = (userId?: string, inquiryType?: string) => {
    addActivity({
      type: 'ai_response',
      message: `AI Assistant responded${inquiryType ? ` to ${inquiryType}` : ''}`,
      status: 'success',
      userId,
      metadata: { inquiryType }
    })
  }

  const trackLeadAdded = (userId?: string, leadName?: string) => {
    addActivity({
      type: 'lead_added',
      message: `New lead added${leadName ? ` - ${leadName}` : ''}`,
      status: 'success',
      userId,
      metadata: { leadName }
    })
  }

  const trackEmailProcessed = (userId?: string, emailType?: string) => {
    addActivity({
      type: 'email_processed',
      message: `Email processed${emailType ? ` - ${emailType}` : ''}`,
      status: 'success',
      userId,
      metadata: { emailType }
    })
  }

  const trackServiceError = (userId?: string, serviceName?: string, error?: string) => {
    addActivity({
      type: 'service_error',
      message: `Service error${serviceName ? ` - ${serviceName}` : ''}${error ? `: ${error}` : ''}`,
      status: 'error',
      userId,
      metadata: { serviceName, error }
    })
  }

  const trackSystemUpdate = (updateType?: string) => {
    addActivity({
      type: 'system_update',
      message: `System update${updateType ? ` - ${updateType}` : ''}`,
      status: 'info',
      metadata: { updateType }
    })
  }

  return {
    trackLogin,
    trackLogout,
    trackOnboardingStart,
    trackOnboardingComplete,
    trackProfileUpdate,
    trackServiceConfiguration,
    trackAIResponse,
    trackLeadAdded,
    trackEmailProcessed,
    trackServiceError,
    trackSystemUpdate
  }
}

// Utility function to format timestamps
export const formatActivityTimestamp = (timestamp: string): string => {
  const now = new Date()
  const activityTime = new Date(timestamp)
  const diffMs = now.getTime() - activityTime.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
  return activityTime.toLocaleDateString()
}
