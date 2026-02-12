import React, { useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Mail, RefreshCw, Activity, AlertCircle, Clock, Shield, Loader2 } from 'lucide-react'
import { OutlookConnection } from '../components/OutlookConnection'
import { useAuth } from '../contexts/AuthContext'
import { apiClient, OutlookConnectionStatus } from '../services/apiClient'
import { useToast } from '../components/Toast'

export const OutlookConnect: React.FC = () => {
  const { user } = useAuth()
  const { addToast } = useToast()
  const queryClient = useQueryClient()

  const {
    data: outlookStatus,
    isLoading: outlookLoading,
    refetch: refetchOutlookStatus
  } = useQuery<OutlookConnectionStatus>({
    queryKey: ['outlook-connection', user?.id],
    queryFn: () => apiClient.getOutlookConnectionStatus(),
    enabled: !!user,
    staleTime: 2 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  })

  const syncMutation = useMutation({
    mutationFn: () => apiClient.triggerOutlookSync(),
    onSuccess: (data) => {
      const message = data?.message || data?.data?.message || 'Outlook sync triggered successfully'
      addToast({ 
        type: 'success', 
        title: 'Outlook Sync Started', 
        message: message
      })
      queryClient.invalidateQueries({ queryKey: ['outlook-connection', user?.id] })
      setTimeout(() => {
        refetchOutlookStatus()
      }, 2000)
    },
    onError: (error: any) => {
      const errorMessage = error?.response?.data?.message || error?.message || 'Unable to start Outlook sync. Please try again.'
      addToast({ 
        type: 'error', 
        title: 'Sync Failed', 
        message: errorMessage
      })
    }
  })

  if (!user) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="text-center py-12">
          <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">Authentication Required</h2>
          <p className="text-gray-600 dark:text-gray-400">Please log in to connect your Outlook account.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Outlook Integration</h1>
        <p className="text-gray-600 dark:text-gray-400">
          Connect your Microsoft Outlook or Office 365 account to automate email workflows and capture leads.
        </p>
      </div>

      <OutlookConnection 
        userId={user.id} 
        onConnected={() => {
          refetchOutlookStatus()
          queryClient.invalidateQueries({ queryKey: ['outlook-connection', user.id] })
        }} 
      />

      {outlookStatus?.connected && (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Sync Your Emails</h2>
            <button
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {syncMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Syncing...
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4" />
                  Sync Now
                </>
              )}
            </button>
          </div>
          
          <div className="space-y-3 text-sm text-gray-600 dark:text-gray-400">
            <div className="flex items-center gap-2">
              <Mail className="h-4 w-4" />
              <span>Emails will be synced to your inbox automatically</span>
            </div>
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4" />
              <span>Leads will be automatically captured from emails</span>
            </div>
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4" />
              <span>Your data is encrypted and secure</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

