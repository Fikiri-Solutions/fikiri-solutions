import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { apiClient } from '../services/apiClient'
import { useToast } from '../components/Toast'
import { Mail, CheckCircle, XCircle, Loader2, RefreshCw, ArrowRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export const GmailStatusCheck: React.FC = () => {
  const { user } = useAuth()
  const { addToast } = useToast()
  const navigate = useNavigate()
  const [gmailStatus, setGmailStatus] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [emails, setEmails] = useState<any[]>([])
  const [emailsLoading, setEmailsLoading] = useState(false)

  useEffect(() => {
    if (user) {
      checkGmailStatus()
    } else {
      setLoading(false)
    }
  }, [user])

  const checkGmailStatus = async () => {
    setLoading(true)
    try {
      const status = await apiClient.getGmailConnectionStatus()
      setGmailStatus(status)
      
      if (status?.connected) {
        // Try to load emails to verify connection works
        loadEmails()
      }
    } catch (error) {
      console.error('Error checking Gmail status:', error)
      addToast({ type: 'error', title: 'Failed to check Gmail status' })
    } finally {
      setLoading(false)
    }
  }

  const loadEmails = async () => {
    setEmailsLoading(true)
    try {
      const data = await apiClient.getEmails({ limit: 5 })
      setEmails(data?.emails || data || [])
    } catch (error) {
      console.error('Error loading emails:', error)
      // Don't show error toast - might just be no emails
    } finally {
      setEmailsLoading(false)
    }
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-brand-background dark:bg-gray-900">
        <div className="text-center">
          <XCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-brand-text dark:text-white mb-2">Not Signed In</h2>
          <p className="text-brand-text/70 dark:text-gray-400 mb-4">Please sign in to check Gmail status</p>
          <button
            onClick={() => navigate('/login')}
            className="px-4 py-2 bg-brand-primary text-white rounded-lg hover:bg-brand-primary/90"
          >
            Go to Login
          </button>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-brand-background dark:bg-gray-900">
        <Loader2 className="h-8 w-8 animate-spin text-brand-primary" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-brand-background dark:bg-gray-900 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-2xl font-bold text-brand-text dark:text-white">Gmail Connection Status</h1>
            <button
              onClick={checkGmailStatus}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              title="Refresh"
            >
              <RefreshCw className="h-5 w-5 text-brand-text/70 dark:text-gray-400" />
            </button>
          </div>

          {gmailStatus?.connected ? (
            <div className="space-y-4">
              <div className="flex items-center gap-3 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                <CheckCircle className="h-6 w-6 text-green-500" />
                <div>
                  <p className="font-semibold text-green-800 dark:text-green-400">Gmail Connected!</p>
                  {gmailStatus.email && (
                    <p className="text-sm text-green-700 dark:text-green-300">{gmailStatus.email}</p>
                  )}
                </div>
              </div>

              {gmailStatus.last_sync && (
                <div className="text-sm text-brand-text/70 dark:text-gray-400">
                  Last sync: {new Date(gmailStatus.last_sync).toLocaleString()}
                </div>
              )}

              <div className="mt-6">
                <h2 className="text-lg font-semibold text-brand-text dark:text-white mb-3">Test Email Access</h2>
                {emailsLoading ? (
                  <div className="flex items-center gap-2 text-brand-text/70 dark:text-gray-400">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Loading emails...</span>
                  </div>
                ) : emails.length > 0 ? (
                  <div className="space-y-2">
                    <p className="text-sm text-green-600 dark:text-green-400 font-medium">
                      ✅ Successfully loaded {emails.length} email(s)!
                    </p>
                    <div className="space-y-2 max-h-60 overflow-y-auto">
                      {emails.map((email) => (
                        <div key={email.id} className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                          <p className="font-medium text-brand-text dark:text-white">{email.subject || '(No subject)'}</p>
                          <p className="text-sm text-brand-text/70 dark:text-gray-400">From: {email.from}</p>
                        </div>
                      ))}
                    </div>
                    <button
                      onClick={() => navigate('/inbox')}
                      className="mt-4 flex items-center gap-2 px-4 py-2 bg-brand-primary text-white rounded-lg hover:bg-brand-primary/90"
                    >
                      <Mail className="h-4 w-4" />
                      View Full Inbox
                      <ArrowRight className="h-4 w-4" />
                    </button>
                  </div>
                ) : (
                  <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                    <p className="text-sm text-yellow-800 dark:text-yellow-300">
                      ⚠️ Connection successful, but no emails found. This could mean:
                    </p>
                    <ul className="list-disc list-inside mt-2 text-sm text-yellow-700 dark:text-yellow-400">
                      <li>Your inbox is empty</li>
                      <li>Emails haven't synced yet (try syncing from /integrations/gmail)</li>
                      <li>There was an issue fetching emails</li>
                    </ul>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center gap-3 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
                <XCircle className="h-6 w-6 text-red-500" />
                <div>
                  <p className="font-semibold text-red-800 dark:text-red-400">Gmail Not Connected</p>
                  <p className="text-sm text-red-700 dark:text-red-300">Please connect your Gmail account to continue</p>
                </div>
              </div>
              <button
                onClick={() => navigate('/integrations/gmail')}
                className="flex items-center gap-2 px-4 py-2 bg-brand-primary text-white rounded-lg hover:bg-brand-primary/90"
              >
                <Mail className="h-4 w-4" />
                Connect Gmail
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}



