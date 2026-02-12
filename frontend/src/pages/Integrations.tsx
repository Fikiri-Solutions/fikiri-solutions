import React from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Mail, CheckCircle, XCircle, Loader2, RefreshCw, PlugZap, AlertCircle } from 'lucide-react'
import { GmailConnection } from '../components/GmailConnection'
import { OutlookConnection } from '../components/OutlookConnection'
import { useAuth } from '../contexts/AuthContext'
import { apiClient, GmailConnectionStatus, OutlookConnectionStatus, EmailSyncStatus } from '../services/apiClient'
import { useToast } from '../components/Toast'

export const Integrations: React.FC = () => {
  const { user } = useAuth()
  const { addToast } = useToast()
  const queryClient = useQueryClient()

  // Fetch connection statuses
  const { data: gmailStatus, refetch: refetchGmail } = useQuery<GmailConnectionStatus>({
    queryKey: ['gmail-connection', user?.id],
    queryFn: () => apiClient.getGmailConnectionStatus(),
    enabled: !!user,
    staleTime: 2 * 60 * 1000,
  })

  const { data: outlookStatus, refetch: refetchOutlook } = useQuery<OutlookConnectionStatus>({
    queryKey: ['outlook-connection', user?.id],
    queryFn: () => apiClient.getOutlookConnectionStatus(),
    enabled: !!user,
    staleTime: 2 * 60 * 1000,
  })

  const { data: syncStatus } = useQuery<EmailSyncStatus>({
    queryKey: ['gmail-sync-status', user?.id],
    queryFn: () => apiClient.getEmailSyncStatus(),
    enabled: !!user && !!gmailStatus?.connected,
    refetchInterval: 5000,
  })

  if (!user) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="text-center py-12">
          <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">Authentication Required</h2>
          <p className="text-gray-600 dark:text-gray-400">Please log in to manage integrations.</p>
        </div>
      </div>
    )
  }

  const connectedCount = [gmailStatus?.connected, outlookStatus?.connected].filter(Boolean).length
  const totalIntegrations = 2

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Integrations</h1>
        <p className="text-gray-600 dark:text-gray-400">
          Connect your email accounts and services to automate workflows and capture leads.
        </p>
      </div>

      {/* Summary Card */}
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Connection Status</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {connectedCount} of {totalIntegrations} integrations connected
            </p>
          </div>
          <div className="flex items-center gap-2">
            {connectedCount === totalIntegrations ? (
              <CheckCircle className="h-8 w-8 text-green-600" />
            ) : (
              <XCircle className="h-8 w-8 text-gray-400" />
            )}
          </div>
        </div>
      </div>

      {/* Email Integrations */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <Mail className="h-5 w-5" />
          Email Accounts
        </h2>

        {/* Gmail */}
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
          <GmailConnection 
            userId={user.id} 
            onConnected={() => {
              refetchGmail()
              queryClient.invalidateQueries({ queryKey: ['gmail-connection', user.id] })
            }} 
          />
          {gmailStatus?.connected && syncStatus && (
            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">Last Sync</p>
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    {syncStatus.last_sync 
                      ? new Date(syncStatus.last_sync).toLocaleString()
                      : 'Never synced'}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">Total Emails</p>
                  <p className="text-xs text-gray-600 dark:text-gray-400">{syncStatus.total_emails || 0}</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Outlook */}
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
          <OutlookConnection 
            userId={user.id} 
            onConnected={() => {
              refetchOutlook()
              queryClient.invalidateQueries({ queryKey: ['outlook-connection', user.id] })
            }} 
          />
        </div>
      </div>

      {/* Coming Soon */}
      <div className="bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
        <div className="flex items-center gap-3">
          <PlugZap className="h-5 w-5 text-gray-400" />
          <div>
            <h3 className="text-sm font-medium text-gray-900 dark:text-white">More Integrations Coming Soon</h3>
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
              HubSpot, Slack, and more integrations are on the way.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

