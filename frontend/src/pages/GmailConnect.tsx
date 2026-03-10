import React, { useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Mail, RefreshCw, Activity, AlertCircle, Clock, Shield, Loader2 } from 'lucide-react'
import { GmailConnection } from '../components/GmailConnection'
import { useAuth } from '../contexts/AuthContext'
import { apiClient, EmailSyncStatus, GmailConnectionStatus } from '../services/apiClient'
import { useToast } from '../components/Toast'

export const GmailConnect: React.FC = () => {
  const { user } = useAuth()
  const { addToast } = useToast()
  const queryClient = useQueryClient()
  type SyncResponse = { message?: string; data?: { message?: string } }

  const {
    data: gmailStatus,
    isLoading: gmailLoading,
    refetch: refetchGmailStatus
  } = useQuery<GmailConnectionStatus>({
    queryKey: ['gmail-connection', user?.id],
    queryFn: () => apiClient.getGmailConnectionStatus(),
    enabled: !!user,
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  })

  const {
    data: syncStatus,
    isLoading: syncLoading,
    refetch: refetchSyncStatus
  } = useQuery<EmailSyncStatus>({
    queryKey: ['gmail-sync-status', user?.id],
    queryFn: () => apiClient.getEmailSyncStatus(),
    enabled: !!user && !!gmailStatus?.connected, // Only fetch sync status if Gmail is connected
    staleTime: 0, // Always consider data stale to get fresh progress
    gcTime: 5 * 60 * 1000, // 5 minutes
    // Dynamic refetch interval: faster when syncing, slower when idle
    refetchInterval: (query) => {
      if (!gmailStatus?.connected) return false
      const data = query.state.data as EmailSyncStatus | undefined
      const isSyncing = data?.syncing || 
                       data?.sync_status === 'in_progress' || 
                       data?.sync_status === 'processing' || 
                       data?.sync_status === 'pending'
      // Poll every 1 second when syncing (faster updates), every 10 seconds when idle
      return isSyncing ? 1 * 1000 : 10 * 1000
    },
  })

  // Track previous sync status to detect when sync completes
  const prevSyncStatusRef = React.useRef<EmailSyncStatus | undefined>(syncStatus)
  useEffect(() => {
    const prev = prevSyncStatusRef.current
    const current = syncStatus
    
    // Detect when sync completes (was syncing, now completed)
    if (prev && current) {
      const wasSyncing = prev.syncing || 
                        prev.sync_status === 'in_progress' || 
                        prev.sync_status === 'processing' || 
                        prev.sync_status === 'pending'
      const isCompleted = current.sync_status === 'completed' && 
                         !current.syncing &&
                         current.last_sync
      
      if (wasSyncing && isCompleted) {
        // Sync just completed - invalidate queries to force fresh data
        queryClient.invalidateQueries({ queryKey: ['gmail-sync-status', user?.id] })
        queryClient.invalidateQueries({ queryKey: ['gmail-connection', user?.id] })
        refetchSyncStatus()
        refetchGmailStatus()
      }
    }
    
    prevSyncStatusRef.current = syncStatus
  }, [syncStatus, queryClient, user?.id, refetchSyncStatus, refetchGmailStatus])

  const syncMutation = useMutation({
    mutationFn: () => apiClient.triggerGmailSync(),
    onSuccess: (data: SyncResponse) => {
      const message = data?.message || data?.data?.message || 'Gmail sync triggered successfully'
      addToast({ 
        type: 'success', 
        title: 'Gmail Sync Started', 
        message: message + ' Check the live logs for progress.' 
      })
      // Invalidate and refetch immediately to show "syncing" state
      queryClient.invalidateQueries({ queryKey: ['gmail-sync-status', user?.id] })
      queryClient.invalidateQueries({ queryKey: ['gmail-connection', user?.id] })
      // Also refetch after short delays to catch status updates
      setTimeout(() => {
        refetchSyncStatus()
        refetchGmailStatus()
      }, 500)
      setTimeout(() => {
        refetchSyncStatus()
      }, 2000)
    },
    onError: (error: any) => {
      const errorMessage = error?.response?.data?.message || error?.message || 'Unable to start Gmail sync. Please try again.'
      addToast({ 
        type: 'error', 
        title: 'Sync Failed', 
        message: errorMessage 
      })
    }
  })

  if (!user) {
    return (
      <div className="flex items-center justify-center h-full text-center text-brand-text/70 dark:text-gray-300">
        <div>
          <h2 className="text-2xl font-semibold mb-2">Sign in required</h2>
          <p>Please log in to connect your Gmail inbox.</p>
        </div>
      </div>
    )
  }

  const logItems = [
    {
      label: 'Connection status',
      value: gmailStatus?.connected ? 'Connected' : 'Not connected',
      icon: gmailStatus?.connected ? Mail : AlertCircle,
      tone: gmailStatus?.connected ? 'text-green-700' : 'text-red-600',
      showProgress: false
    },
    {
      label: 'Last sync',
      value: syncStatus?.last_sync
        ? (() => {
            try {
              const date = new Date(syncStatus.last_sync)
              // Format in user's local timezone with better formatting
              return date.toLocaleString(undefined, {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: true
              })
            } catch (e) {
              return new Date(syncStatus.last_sync).toLocaleString()
            }
          })()
        : syncStatus?.syncing
          ? 'Syncing now...'
          : gmailStatus?.connected 
            ? 'Never synced'
            : 'N/A',
      icon: Clock,
      tone: syncStatus?.last_sync 
        ? 'text-green-600' 
        : syncStatus?.syncing
          ? 'text-blue-600 animate-pulse'
          : gmailStatus?.connected 
            ? 'text-gray-500' 
            : 'text-gray-400',
      showProgress: false
    },
    {
      label: 'Sync status',
      value: (() => {
        const isSyncing = syncStatus?.syncing || syncStatus?.sync_status === 'in_progress' || syncStatus?.sync_status === 'processing' || syncStatus?.sync_status === 'pending'
        if (isSyncing) {
          const progress = syncStatus?.progress ?? 0
          const emailsCount = syncStatus?.emails_synced_this_job ?? 0
          if (progress > 0) {
            return `Syncing... ${progress}%${emailsCount > 0 ? ` (${emailsCount} emails)` : ''}`
          }
          return 'Syncing in progress...'
        }
        if (syncStatus?.sync_status === 'pending') return 'Sync queued...'
        if (syncStatus?.sync_status === 'completed') return 'Sync completed'
        if (syncStatus?.sync_status === 'failed') return 'Sync failed'
        if (syncStatus?.sync_status === 'connected_pending_sync') return 'Ready to sync'
        if (syncStatus?.sync_status === 'not_connected') return 'Not connected'
        return gmailStatus?.connected ? 'Ready to sync' : 'Not connected'
      })(),
      icon: Activity,
      tone: syncStatus?.syncing || syncStatus?.sync_status === 'in_progress' || syncStatus?.sync_status === 'processing'
        ? 'text-blue-600 animate-pulse' 
        : syncStatus?.sync_status === 'pending'
          ? 'text-blue-600 animate-pulse'
        : syncStatus?.sync_status === 'completed'
          ? 'text-green-600'
          : syncStatus?.sync_status === 'failed'
            ? 'text-red-600'
            : syncStatus?.sync_status === 'connected_pending_sync'
              ? 'text-yellow-600'
              : gmailStatus?.connected 
                ? 'text-yellow-600' 
                : 'text-red-600',
      showProgress: syncStatus?.syncing || syncStatus?.sync_status === 'in_progress' || syncStatus?.sync_status === 'processing' || syncStatus?.sync_status === 'pending',
      progress: syncStatus?.progress !== undefined ? syncStatus.progress : (syncStatus?.syncing || syncStatus?.sync_status === 'in_progress' || syncStatus?.sync_status === 'processing' || syncStatus?.sync_status === 'pending' ? 1 : 0)
    }
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-wide text-brand-text/60 dark:text-gray-400">Integrations</p>
          <h1 className="text-3xl font-bold text-brand-text dark:text-white mt-1">Gmail Automation</h1>
          <p className="mt-2 text-brand-text/70 dark:text-gray-300">
            Connect your inbox, monitor sync health, and trigger AI automations without leaving the dashboard.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => {
              refetchGmailStatus()
              refetchSyncStatus()
              addToast({ type: 'info', title: 'Status refreshed' })
            }}
            className="inline-flex items-center gap-2 rounded-lg border border-brand-text/20 px-4 py-2 text-sm font-medium text-brand-text hover:bg-brand-accent/10 dark:text-gray-200"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <button
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending || gmailStatus?.connected === false}
            className="inline-flex items-center gap-2 rounded-lg bg-brand-primary px-4 py-2 text-sm font-medium text-white hover:bg-brand-secondary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Activity className="h-4 w-4" />
            Sync inbox
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-brand-text/10 dark:border-gray-700 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="bg-brand-accent/20 p-2 rounded-full">
              <Mail className="h-5 w-5 text-brand-primary" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-brand-text dark:text-white">Gmail connection</h2>
              <p className="text-sm text-brand-text/70 dark:text-gray-400">Secure OAuth connection to your inbox.</p>
            </div>
          </div>
          <GmailConnection
            userId={user.id}
            onConnected={() => {
              refetchGmailStatus()
              refetchSyncStatus()
            }}
          />
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-brand-text/10 dark:border-gray-700 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="bg-brand-accent/20 p-2 rounded-full">
              <Shield className="h-5 w-5 text-brand-primary" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-brand-text dark:text-white">Live sync health</h2>
              <p className="text-sm text-brand-text/70 dark:text-gray-400">
                Monitor sync cycles, errors, and activity in real time.
              </p>
            </div>
          </div>

          <div className="space-y-4">
            {gmailLoading || syncLoading ? (
              <div className="text-sm text-brand-text/70 dark:text-gray-300">Loading status…</div>
            ) : (
              logItems.map(item => (
                <div
                  key={item.label}
                  className="flex flex-col gap-2 rounded-xl border border-brand-text/10 dark:border-gray-700 px-4 py-3"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {item.showProgress ? (
                        <Loader2 className={`h-5 w-5 ${item.tone} animate-spin`} />
                      ) : (
                        <item.icon className={`h-5 w-5 ${item.tone}`} />
                      )}
                      <div>
                        <p className="text-xs uppercase tracking-wide text-brand-text/60 dark:text-gray-400">{item.label}</p>
                        <p className="text-base font-medium text-brand-text dark:text-white">{item.value}</p>
                      </div>
                    </div>
                  </div>
                  {item.showProgress && (
                    <div className="w-full mt-2">
                      <div className="flex items-center justify-between text-xs text-brand-text/60 dark:text-gray-400 mb-1.5">
                        <span className="font-medium">Progress</span>
                        <span className="font-semibold text-blue-600">
                          {item.progress !== undefined && item.progress > 0 
                            ? `${item.progress}%` 
                            : 'Syncing...'}
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 overflow-hidden relative">
                        <div
                          className="bg-blue-600 h-2.5 rounded-full transition-all duration-500 ease-out"
                          style={{ width: `${Math.max(item.progress || 1, 1)}%` }}
                        />
                        {(!item.progress || item.progress === 0 || item.progress === 1) && (
                          <div className="absolute inset-0 bg-gradient-to-r from-blue-400 via-blue-500 to-blue-400 animate-pulse opacity-50" 
                               style={{ 
                                 backgroundSize: '200% 100%',
                                 animation: 'shimmer 2s infinite'
                               }} 
                          />
                        )}
                      </div>
                      <style>{`
                        @keyframes shimmer {
                          0% { background-position: -200% 0; }
                          100% { background-position: 200% 0; }
                        }
                      `}</style>
                    </div>
                  )}
                </div>
              ))
            )}

            {syncStatus?.error && (
              <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
                <AlertCircle className="h-5 w-5" />
                <div>
                  <p className="font-semibold">Sync issues detected</p>
                  <p>{syncStatus.error}</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
