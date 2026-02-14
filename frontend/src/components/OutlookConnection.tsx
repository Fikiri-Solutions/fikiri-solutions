import React, { useState, useEffect, useCallback } from 'react'
import { CheckCircle, AlertCircle, Mail, Eye, Loader2, Info } from 'lucide-react'
import { useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from './Toast'
import { apiClient } from '../services/apiClient'

interface OutlookConnectionProps {
  userId: number
  onConnected: () => void
}

interface OutlookStatus {
  connected: boolean
  status?: string
  expires_at?: string
  scopes?: string[]
  error?: string
}

export const OutlookConnection: React.FC<OutlookConnectionProps> = ({ userId, onConnected }) => {
  const location = useLocation()
  const { user } = useAuth()
  const [isConnecting, setIsConnecting] = useState(false)
  const [outlookStatus, setOutlookStatus] = useState<OutlookStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showDetails, setShowDetails] = useState(false)
  const { addToast } = useToast()
  
  const getRedirectParam = () => {
    const urlParams = new URLSearchParams(location.search)
    const redirectParam = urlParams.get('redirect')
    if (redirectParam && redirectParam.startsWith('/') && !redirectParam.startsWith('//')) {
      return redirectParam
    }
    return null
  }
  
  const getOAuthRedirectUrl = () => {
    const redirectParam = getRedirectParam()
    if (redirectParam) {
      return redirectParam
    }
    
    if (location.pathname.startsWith('/onboarding-flow') || location.pathname.startsWith('/onboarding')) {
      const redirectPath = getRedirectParam()
      const redirectQuery = redirectPath ? `?redirect=${encodeURIComponent(redirectPath)}` : ''
      return `/onboarding-flow/2${redirectQuery}`
    }
    
    if (user?.onboarding_completed) {
      if (location.pathname === '/integrations/outlook') {
        return '/integrations/outlook'
      }
      return '/integrations/outlook'
    }
    
    return '/onboarding-flow/2'
  }

  const checkOutlookStatus = useCallback(async () => {
    if (!userId || userId <= 0) {
      setError('Invalid user ID')
      return
    }

    try {
      const data = await apiClient.getOutlookStatus(userId)
      const status = (data && 'data' in data ? data.data : data) as OutlookStatus | undefined
      
      setOutlookStatus({
        connected: status?.connected === true,
        status: status?.status,
        expires_at: status?.expires_at,
        scopes: status?.scopes,
        error: status?.error
      })
      
      if (status?.connected) {
        setError(null)
        onConnected()
      }
    } catch (err: any) {
      setError(err.message || 'Failed to check Outlook status')
      setOutlookStatus({ connected: false, error: err.message })
    }
  }, [userId, onConnected])

  useEffect(() => {
    checkOutlookStatus()
    
    // Check for OAuth success in URL
    const urlParams = new URLSearchParams(location.search)
    if (urlParams.get('oauth_success') === 'true') {
      addToast({
        type: 'success',
        title: 'Outlook Connected',
        message: 'Your Outlook account has been connected successfully!'
      })
      checkOutlookStatus()
    }
    
    if (urlParams.get('oauth_error')) {
      const errorMsg = urlParams.get('oauth_error') || 'Outlook connection failed'
      setError(errorMsg)
      addToast({
        type: 'error',
        title: 'Connection Failed',
        message: errorMsg
      })
    }
  }, [location.search, checkOutlookStatus, addToast])

  const connectOutlook = async () => {
    setIsConnecting(true)
    setError(null)
    
    const redirectUrl = getOAuthRedirectUrl()
    try {
      const data = await apiClient.startOutlookOAuth(redirectUrl)
      if (data.url) {
        addToast({
          type: 'info',
          title: 'Redirecting to Microsoft',
          message: 'Please sign in to connect your Outlook account'
        })
        window.location.href = data.url
      } else {
        setError(data.error || 'Failed to start Outlook connection')
        setIsConnecting(false)
      }
    } catch (err: any) {
      setError(err.message || 'Failed to connect Outlook')
      setIsConnecting(false)
    }
  }

  const disconnectOutlook = async () => {
    if (!confirm('Are you sure you want to disconnect your Outlook account? This will stop syncing your emails.')) {
      return
    }

    try {
      const data = await apiClient.disconnectOutlook(userId)
      if (data.success || (data as any).data?.success) {
        setOutlookStatus({ connected: false })
        setError(null)
        // Refresh status to confirm disconnect
        await checkOutlookStatus()
        addToast({ 
          type: 'success', 
          title: 'Outlook Disconnected', 
          message: 'Your Outlook account has been disconnected successfully.' 
        })
        onConnected() // Notify parent to refresh
      } else {
        throw new Error(data.error || 'Failed to disconnect Outlook')
      }
    } catch (error: any) {
      console.error('Error disconnecting Outlook:', error)
      const errorMessage = error.message || 'Failed to disconnect Outlook. Please try again.'
      setError(errorMessage)
      addToast({ 
        type: 'error', 
        title: 'Disconnect Failed', 
        message: errorMessage 
      })
    }
  }

  if (outlookStatus?.connected) {
    return (
      <div className="space-y-4">
        <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
              <div>
                <h3 className="font-semibold text-green-900 dark:text-green-100">Outlook Connected</h3>
                <p className="text-sm text-green-700 dark:text-green-300">
                  Your Outlook account is connected and ready to use
                </p>
              </div>
            </div>
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="text-green-600 dark:text-green-400 hover:text-green-700 dark:hover:text-green-300"
            >
              <Eye className="h-5 w-5" />
            </button>
          </div>
          
          {showDetails && (
            <div className="mt-4 pt-4 border-t border-green-200 dark:border-green-800 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-green-700 dark:text-green-300">Status:</span>
                <span className="text-green-900 dark:text-green-100 font-medium">{outlookStatus.status || 'active'}</span>
              </div>
              {outlookStatus.expires_at && (
                <div className="flex justify-between">
                  <span className="text-green-700 dark:text-green-300">Expires:</span>
                  <span className="text-green-900 dark:text-green-100">
                    {new Date(parseInt(outlookStatus.expires_at) * 1000).toLocaleDateString()}
                  </span>
                </div>
              )}
            </div>
          )}
          
          <div className="mt-4 pt-4 border-t border-green-200 dark:border-green-800">
            <button
              onClick={disconnectOutlook}
              className="w-full px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 border border-red-300 dark:border-red-700 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
            >
              Disconnect Outlook
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="p-6 border-2 border-gray-200 dark:border-gray-700 rounded-xl">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white text-lg mb-2">
              Microsoft Outlook / Office 365
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Connect your Outlook account to enable email automation, lead capture, and AI-powered responses.
            </p>
          </div>
          <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/20 rounded-lg flex items-center justify-center flex-shrink-0">
            <Mail className="w-6 h-6 text-blue-600 dark:text-blue-400" />
          </div>
        </div>
        
        {error && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
              <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
            </div>
          </div>
        )}
        
        <button
          onClick={connectOutlook}
          disabled={isConnecting}
          className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {isConnecting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Connecting...
            </>
          ) : (
            <>
              <Mail className="h-4 w-4" />
              Connect Outlook
            </>
          )}
        </button>
        
        <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <div className="flex items-start gap-2">
            <Info className="h-4 w-4 text-gray-500 dark:text-gray-400 mt-0.5 flex-shrink-0" />
            <div className="text-xs text-gray-600 dark:text-gray-400">
              <p className="font-medium mb-1">What you'll grant access to:</p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>Read and send emails</li>
                <li>Manage your calendar</li>
                <li>Access your profile information</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

