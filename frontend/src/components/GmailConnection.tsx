import React, { useState, useEffect } from 'react'
import { CheckCircle, AlertCircle, Mail, Shield, Eye, Clock, Loader2 } from 'lucide-react'

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
  const [isConnecting, setIsConnecting] = useState(false)
  const [gmailStatus, setGmailStatus] = useState<GmailStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showDetails, setShowDetails] = useState(false)

  useEffect(() => {
    checkGmailStatus()
  }, [userId])

  const checkGmailStatus = async () => {
    try {
      const response = await fetch(`https://fikirisolutions.onrender.com/api/auth/gmail/status?user_id=${userId}`)
      const data = await response.json()
      
      if (data.success) {
        setGmailStatus(data.data)
        if (data.data.connected) {
          onConnected()
        }
      }
    } catch (error) {
      console.error('Error checking Gmail status:', error)
    }
  }

  const connectGmail = async () => {
    try {
      setIsConnecting(true)
      setError(null)

      const response = await fetch('https://fikirisolutions.onrender.com/api/auth/gmail/connect', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          redirect_uri: window.location.origin + '/onboarding-flow/2'
        })
      })

      const data = await response.json()
      
      if (data.success) {
        // Redirect to Google OAuth
        window.location.href = data.auth_url
      } else {
        throw new Error(data.error || 'Failed to initiate Gmail connection')
      }
    } catch (error) {
      setError('Failed to connect Gmail. Please try again.')
    } finally {
      setIsConnecting(false)
    }
  }

  const disconnectGmail = async () => {
    try {
      const response = await fetch('https://fikirisolutions.onrender.com/api/auth/gmail/disconnect', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId
        })
      })

      const data = await response.json()
      
      if (data.success) {
        setGmailStatus({ connected: false })
      } else {
        throw new Error(data.error || 'Failed to disconnect Gmail')
      }
    } catch (error) {
      setError('Failed to disconnect Gmail. Please try again.')
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