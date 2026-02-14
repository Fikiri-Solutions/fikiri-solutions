import React, { useState, useEffect, useCallback, useRef } from 'react'
import { CheckCircle, AlertCircle, Mail, Shield, Eye, Clock, Loader2 } from 'lucide-react'
import { useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from './Toast'
import { apiClient } from '../services/apiClient'

interface GmailConnectionProps {
  userId: number
  onConnected: () => void
}

interface GmailStatus {
  connected: boolean
  email?: string
  scopes?: string[]
  last_sync?: string
  error?: string
}

export const GmailConnection: React.FC<GmailConnectionProps> = ({ userId, onConnected }) => {
  const location = useLocation()
  const { user } = useAuth()
  const [isConnecting, setIsConnecting] = useState(false)
  const [gmailStatus, setGmailStatus] = useState<GmailStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showDetails, setShowDetails] = useState(false)
  const { addToast } = useToast()
  const hasShownOAuthToast = useRef(false) // Prevent duplicate toasts
  
  // Get redirect parameter from URL to preserve through OAuth
  const getRedirectParam = () => {
    const urlParams = new URLSearchParams(location.search)
    const redirectParam = urlParams.get('redirect')
    if (redirectParam && redirectParam.startsWith('/') && !redirectParam.startsWith('//')) {
      return redirectParam
    }
    return null
  }
  
  // Determine the appropriate redirect URL based on context
  const getOAuthRedirectUrl = () => {
    // If there's an explicit redirect parameter, use it
    const redirectParam = getRedirectParam()
    if (redirectParam) {
      return redirectParam
    }
    
    // If user is in onboarding (on onboarding-flow pages), redirect back to onboarding
    if (location.pathname.startsWith('/onboarding-flow') || location.pathname.startsWith('/onboarding')) {
      const redirectPath = getRedirectParam()
      const redirectQuery = redirectPath ? `?redirect=${encodeURIComponent(redirectPath)}` : ''
      return `/onboarding-flow/2${redirectQuery}`
    }
    
    // If user is already onboarded, redirect back to where they came from
    // This handles the case where they're connecting Gmail after account creation
    if (user?.onboarding_completed) {
      // If they're on the integrations page, stay there
      if (location.pathname === '/integrations/gmail') {
        return '/integrations/gmail'
      }
      // Otherwise, default to integrations page
      return '/integrations/gmail'
    }
    
    // Default: onboarding flow step 2 (for new users)
    return '/onboarding-flow/2'
  }

  const abortControllerRef = useRef<AbortController | null>(null)
  const isMountedRef = useRef(true)

  const checkGmailStatus = useCallback(async () => {
    if (!userId || userId <= 0) {
      setError('Invalid user ID')
      return
    }

    // Abort any previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }

    const controller = new AbortController()
    abortControllerRef.current = controller

    try {
      const timeoutId = setTimeout(() => controller.abort(), 10000) // 10 second timeout

      const data = await apiClient.getGmailStatus(userId)
      
      clearTimeout(timeoutId)
      
      // Check if component is still mounted before updating state
      if (!isMountedRef.current) return
      
      if (data.success) {
        const status = (data.data ?? {}) as GmailStatus
        setGmailStatus(status)
        setError(null)
        if (status.connected) {
          onConnected()
        }
      } else {
        throw new Error(data.error || 'Failed to check Gmail status')
      }
    } catch (error: any) {
      // Ignore AbortErrors - they're expected when component unmounts or request is cancelled
      if (error.name === 'AbortError') {
        // Only log in development, and only if it's not a cleanup abort
        if (process.env.NODE_ENV === 'development' && isMountedRef.current) {
          // This is a timeout, not a cleanup
          setError('Request timed out. Please check your connection.')
          addToast({ type: 'error', title: 'Connection Timeout', message: 'Please try again.' })
        }
        return
      }
      
      // Only update state if component is still mounted
      if (!isMountedRef.current) return
      
      console.error('Error checking Gmail status:', error)
      setError('Failed to check Gmail connection status')
      addToast({ type: 'error', title: 'Gmail Status', message: 'Unable to check. Please try again.' })
    } finally {
      // Clear the controller reference if this was the active request
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null
      }
    }
  }, [userId, onConnected, addToast])

  useEffect(() => {
    isMountedRef.current = true
    checkGmailStatus()
    
    // Cleanup: abort request and mark as unmounted
    return () => {
      isMountedRef.current = false
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
        abortControllerRef.current = null
      }
    }
  }, [checkGmailStatus])

  // Check if user just returned from OAuth (check URL params and refresh status)
  useEffect(() => {
    const urlParams = new URLSearchParams(location.search)
    const oauthSuccess = urlParams.get('oauth_success')
    const oauthError = urlParams.get('oauth_error')
    
    // If OAuth just completed, check status and show feedback
    if (oauthSuccess === 'true' && !hasShownOAuthToast.current) {
      hasShownOAuthToast.current = true
      // Clear the URL parameter immediately to prevent re-triggering
      window.history.replaceState({}, '', location.pathname)
      // Wait a moment for backend to process, then check status
      setTimeout(async () => {
        await checkGmailStatus()
        // Show toast after status is confirmed (only once)
        if (!hasShownOAuthToast.current) return
        addToast({ 
          type: 'success', 
          title: 'Gmail Connected Successfully!', 
          message: 'Your Gmail account is now connected. We\'ll start syncing your emails shortly.' 
        })
        // Reset after showing toast to allow future connections
        setTimeout(() => {
          hasShownOAuthToast.current = false
        }, 5000)
      }, 1000)
    } else if (oauthError) {
      // Clear the URL parameter
      window.history.replaceState({}, '', location.pathname)
      setError(decodeURIComponent(oauthError))
      addToast({ 
        type: 'error', 
        title: 'Gmail Connection Failed', 
        message: decodeURIComponent(oauthError) 
      })
    }
  }, [location.search]) // Only depend on location.search to prevent duplicate runs

  const connectGmail = async () => {
    if (!userId || userId <= 0) {
      setError('Invalid user ID')
      return
    }

    try {
      setIsConnecting(true)
      setError(null)

      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 15000) // 15 second timeout

      // Use new proven OAuth endpoint - GET request with redirect parameter
      // Determine appropriate redirect based on user context
      const redirectUri = getOAuthRedirectUrl()
      const data = await apiClient.startGmailOAuth(redirectUri)

      clearTimeout(timeoutId)

      if (data.url) {
        // Security: Validate the auth URL
        if (!data.url.startsWith('https://accounts.google.com/')) {
          throw new Error('Invalid authentication URL')
        }

        // Redirect to Google OAuth
        window.location.href = data.url
        addToast({ type: 'info', title: 'Redirecting', message: 'Taking you to Gmail authentication...' })
      } else {
        throw new Error(data.error || 'Failed to initiate Gmail connection')
      }
    } catch (err: unknown) {
      console.error('Error connecting Gmail:', err)
      setIsConnecting(false)
      const errorMsg = err instanceof Error ? err.message : 'Failed to connect Gmail. Please try again.'
      if (err instanceof Error && err.name === 'AbortError') {
        setError('Request timed out. Please try again.')
        addToast({ type: 'error', title: 'Connection Timeout', message: 'Please try again.' })
      } else {
        setError(errorMsg)
        addToast({ type: 'error', title: 'Connection Failed', message: errorMsg })
      }
    }
  }

  const disconnectGmail = async () => {
    if (!confirm('Are you sure you want to disconnect your Gmail account? This will stop syncing your emails.')) {
      return
    }

    try {
      const data = await apiClient.disconnectGmail(userId)
      
      if (data.success) {
        setGmailStatus({ connected: false })
        setError(null)
        // Refresh status to confirm disconnect
        await checkGmailStatus()
        addToast({ 
          type: 'success', 
          title: 'Gmail Disconnected', 
          message: 'Your Gmail account has been disconnected successfully.' 
        })
        onConnected() // Notify parent to refresh
      } else {
        throw new Error(data.error || 'Failed to disconnect Gmail')
      }
    } catch (error: any) {
      console.error('Error disconnecting Gmail:', error)
      const errorMessage = error.message || 'Failed to disconnect Gmail. Please try again.'
      setError(errorMessage)
      addToast({ 
        type: 'error', 
        title: 'Disconnect Failed', 
        message: errorMessage 
      })
    }
  }

  const getScopeDescription = (scope: string) => {
    const descriptions: { [key: string]: string } = {
      'gmail.readonly': 'Read your Gmail messages',
      'gmail.send': 'Send emails on your behalf',
      'gmail.modify': 'Organize your emails with labels',
      'userinfo.email': 'Access your email address',
      'userinfo.profile': 'Access your basic profile'
    }
    return descriptions[scope] || scope
  }

  // Show connection status with clear visual feedback
  if (gmailStatus?.connected) {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
            <CheckCircle className="h-8 w-8 text-green-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Gmail Connected!</h2>
          <p className="text-gray-600">We're ready to sync your emails</p>
        </div>

        <div className="bg-green-50 border border-green-200 rounded-lg p-6">
          <div className="flex items-center mb-4">
            <Mail className="h-5 w-5 text-green-600 mr-3" />
            <div>
              <h3 className="font-semibold text-green-900">Connected Account</h3>
              <p className="text-sm text-green-800">{gmailStatus.email}</p>
            </div>
          </div>
          
          {gmailStatus.last_sync && (
            <div className="flex items-center text-sm text-green-700">
              <Clock className="h-4 w-4 mr-2" />
              Last sync: {new Date(gmailStatus.last_sync).toLocaleString()}
            </div>
          )}
        </div>

        <div className="text-center">
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            {showDetails ? 'Hide' : 'Show'} permission details
          </button>
        </div>

        {showDetails && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h4 className="font-medium text-gray-900 mb-3">What we can do:</h4>
            <ul className="space-y-2 text-sm text-gray-700">
              {gmailStatus.scopes?.map((scope) => (
                <li key={scope} className="flex items-center">
                  <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                  {getScopeDescription(scope)}
                </li>
              ))}
            </ul>
            
            <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded">
              <div className="flex items-start">
                <Shield className="h-5 w-5 text-blue-600 mr-3 mt-0.5" />
                <div>
                  <h5 className="font-medium text-blue-900">Your privacy is protected</h5>
                  <p className="text-sm text-blue-800 mt-1">
                    We only access emails you've received and never read your personal messages. 
                    You can revoke access anytime in your settings.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="flex justify-center space-x-4">
          <button
            onClick={disconnectGmail}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Disconnect
          </button>
          <button
            onClick={onConnected}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Continue
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="mx-auto w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
          <Mail className="h-8 w-8 text-blue-600" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Connect your Gmail</h2>
        <p className="text-gray-600">We'll sync your emails to find leads and automate responses</p>
      </div>

      {/* Trust Indicators */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="text-center p-4 bg-white border border-gray-200 rounded-lg">
          <Shield className="h-8 w-8 text-green-600 mx-auto mb-2" />
          <h3 className="font-medium text-gray-900">Secure</h3>
          <p className="text-sm text-gray-600">OAuth 2.0 encryption</p>
        </div>
        
        <div className="text-center p-4 bg-white border border-gray-200 rounded-lg">
          <Eye className="h-8 w-8 text-blue-600 mx-auto mb-2" />
          <h3 className="font-medium text-gray-900">Transparent</h3>
          <p className="text-sm text-gray-600">See exactly what we access</p>
        </div>
        
        <div className="text-center p-4 bg-white border border-gray-200 rounded-lg">
          <Clock className="h-8 w-8 text-purple-600 mx-auto mb-2" />
          <h3 className="font-medium text-gray-900">Reversible</h3>
          <p className="text-sm text-gray-600">Disconnect anytime</p>
        </div>
      </div>

      {/* Permission Details */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
        <h3 className="font-semibold text-gray-900 mb-4">What we'll access:</h3>
        <ul className="space-y-3">
          <li className="flex items-start">
            <CheckCircle className="h-5 w-5 text-green-500 mr-3 mt-0.5" />
            <div>
              <span className="font-medium text-gray-900">Read emails</span>
              <p className="text-sm text-gray-600">To identify leads and extract contact information</p>
            </div>
          </li>
          <li className="flex items-start">
            <CheckCircle className="h-5 w-5 text-green-500 mr-3 mt-0.5" />
            <div>
              <span className="font-medium text-gray-900">Send emails</span>
              <p className="text-sm text-gray-600">To respond to leads automatically (with your approval)</p>
            </div>
          </li>
          <li className="flex items-start">
            <CheckCircle className="h-5 w-5 text-green-500 mr-3 mt-0.5" />
            <div>
              <span className="font-medium text-gray-900">Organize emails</span>
              <p className="text-sm text-gray-600">To label and categorize your business emails</p>
            </div>
          </li>
        </ul>
      </div>

      {/* Privacy Notice */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start">
          <Shield className="h-5 w-5 text-blue-600 mr-3 mt-0.5" />
          <div>
            <h4 className="font-medium text-blue-900">Your privacy is our priority</h4>
            <p className="text-sm text-blue-800 mt-1">
              We only process business-related emails and never access your personal messages. 
              All data is encrypted and you can delete it anytime.
            </p>
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center">
            <AlertCircle className="h-5 w-5 text-red-400 mr-3" />
            <p className="text-sm text-red-800">{error}</p>
          </div>
        </div>
      )}

      {/* Connect Button */}
      <div className="text-center">
        <button
          onClick={connectGmail}
          disabled={isConnecting}
          className="bg-blue-600 text-white px-8 py-4 rounded-lg font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center mx-auto"
        >
          {isConnecting ? (
            <>
              <Loader2 className="animate-spin h-5 w-5 mr-2" />
              Connecting...
            </>
          ) : (
            <>
              <Mail className="h-5 w-5 mr-2" />
              Connect Gmail
            </>
          )}
        </button>
        
        <p className="text-xs text-gray-500 mt-3">
          By connecting, you agree to our Terms of Service and Privacy Policy
        </p>
      </div>
    </div>
  )
}