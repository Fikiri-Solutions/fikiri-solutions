import React, { useEffect, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Mail, RefreshCw, Activity, AlertCircle, Clock, Shield, Loader2 } from 'lucide-react'
import { GmailConnection } from '../components/GmailConnection'
import { useAuth } from '../contexts/AuthContext'
import { apiClient, EmailSyncStatus, GmailConnectionStatus } from '../services/apiClient'
import { useToast } from '../components/Toast'

/** True when the API says a sync job is in flight (may be stale if worker never ran). */
function isServerSyncInFlight(data: EmailSyncStatus | undefined): boolean {
  if (!data) return false
  return (
    data.syncing === true ||
    data.sync_status === 'in_progress' ||
    data.sync_status === 'processing' ||
    data.sync_status === 'queued'
  )
}

/** Max time to show live progress after user clicks Sync (backend stale reconcile is ~2 min). */
const SYNC_UI_SESSION_MAX_MS = 4 * 60 * 1000

export const GmailConnect: React.FC = () => {
  const { user } = useAuth()
  const { addToast } = useToast()
  const queryClient = useQueryClient()
  type SyncResponse = { message?: string; data?: { message?: string } }

  /** Only after "Sync inbox" — avoids showing queue/spinner from a stale DB row on page load. */
  const [syncUiSession, setSyncUiSession] = useState(false)
  const syncUiSessionRef = useRef(false)
  syncUiSessionRef.current = syncUiSession

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

  const mutationPendingRef = useRef(false)

  const syncMutation = useMutation({
    mutationFn: () => apiClient.triggerGmailSync(),
    onMutate: () => setSyncUiSession(true),
    onSuccess: (data: SyncResponse) => {
      const message = data?.message || data?.data?.message || 'Gmail sync triggered successfully'
      addToast({
        type: 'success',
        title: 'Gmail Sync Started',
        message: message + ' Check the live logs for progress.'
      })
      const uid = user?.id
      queryClient.invalidateQueries({ queryKey: ['gmail-sync-status', uid] })
      queryClient.invalidateQueries({ queryKey: ['gmail-connection', uid] })
      setTimeout(() => {
        void queryClient.invalidateQueries({ queryKey: ['gmail-sync-status', uid] })
        void queryClient.invalidateQueries({ queryKey: ['gmail-connection', uid] })
      }, 500)
      setTimeout(() => {
        void queryClient.invalidateQueries({ queryKey: ['gmail-sync-status', uid] })
      }, 2000)
    },
    onError: (error: any) => {
      setSyncUiSession(false)
      const errorMessage =
        error?.response?.data?.message || error?.message || 'Unable to start Gmail sync. Please try again.'
      addToast({
        type: 'error',
        title: 'Sync Failed',
        message: errorMessage
      })
    }
  })

  mutationPendingRef.current = syncMutation.isPending

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
    // Fast polling only during a user-started sync session (not stale `queued` on load).
    refetchInterval: (query) => {
      if (!gmailStatus?.connected) return false
      const data = query.state.data as EmailSyncStatus | undefined
      const serverBusy = isServerSyncInFlight(data)
      const session = syncUiSessionRef.current
      const pending = mutationPendingRef.current
      const pollFast = session && (pending || serverBusy)
      return pollFast ? 1 * 1000 : 10 * 1000
    },
  })

  /**
   * Loading / queue UI only after the user clicks Sync, until the server reports
   * completion or failure (or the session times out if the queue is stuck).
   */
  const isActivelySyncing =
    syncUiSession &&
    (syncMutation.isPending || isServerSyncInFlight(syncStatus))

  const hasDefiniteProgress =
    typeof syncStatus?.progress === 'number' && syncStatus.progress > 0

  useEffect(() => {
    if (gmailStatus?.connected === false) {
      setSyncUiSession(false)
    }
  }, [gmailStatus?.connected])

  // End UI session when the server reaches a terminal sync state.
  useEffect(() => {
    if (!syncUiSession || !syncStatus) return
    if (syncStatus.sync_status === 'failed') {
      setSyncUiSession(false)
      addToast({
        type: 'error',
        title: 'Sync did not complete',
        message: 'Gmail sync failed or timed out. Try Sync inbox again.'
      })
      return
    }
    if (
      syncStatus.sync_status === 'connected_pending_sync' &&
      !syncStatus.syncing
    ) {
      setSyncUiSession(false)
      return
    }
    if (syncStatus.sync_status === 'completed' && !syncStatus.syncing) {
      setSyncUiSession(false)
    }
  }, [syncStatus, syncUiSession, addToast])

  // Hard stop so the card returns to normal if the job never leaves `queued`.
  useEffect(() => {
    if (!syncUiSession) return
    const t = window.setTimeout(() => {
      setSyncUiSession(false)
      addToast({
        type: 'info',
        title: 'Sync monitor closed',
        message: 'No progress was detected. Click Sync inbox again or refresh status.'
      })
    }, SYNC_UI_SESSION_MAX_MS)
    return () => window.clearTimeout(t)
  }, [syncUiSession, addToast])

  // Track previous sync status to detect when sync completes
  const prevSyncStatusRef = React.useRef<EmailSyncStatus | undefined>(syncStatus)
  useEffect(() => {
    const prev = prevSyncStatusRef.current
    const current = syncStatus

    // Detect when sync completes (was syncing, now completed)
    if (prev && current) {
      const wasSyncing = isServerSyncInFlight(prev)
      const isCompleted =
        current.sync_status === 'completed' && !current.syncing && current.last_sync

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

  if (!user) {
    return (
      <div className="flex items-center justify-center h-full text-center text-brand-text/70 dark:text-gray-300">
        <div>
          <h2 className="text-2xl font-semibold mb-2 text-gray-900 dark:text-white">Sign in required</h2>
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
      tone: gmailStatus?.connected ? 'text-green-700 dark:text-green-400' : 'text-red-600 dark:text-red-400',
      showProgress: false
    },
    {
      label: 'Last sync',
      value: syncStatus?.last_sync
        ? (() => {
            try {
              const date = new Date(syncStatus.last_sync)
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
        : isActivelySyncing
          ? 'Syncing now...'
          : gmailStatus?.connected
            ? 'Never synced'
            : 'N/A',
      icon: Clock,
      tone: syncStatus?.last_sync
        ? 'text-green-600 dark:text-green-400'
        : isActivelySyncing
          ? 'text-blue-600 dark:text-blue-400 animate-pulse'
          : gmailStatus?.connected
            ? 'text-gray-500 dark:text-gray-400'
            : 'text-gray-400 dark:text-gray-500',
      showProgress: false
    },
    {
      label: 'Sync status',
      value: (() => {
        if (isActivelySyncing) {
          const progress = typeof syncStatus?.progress === 'number' ? syncStatus.progress : 0
          const emailsCount = syncStatus?.emails_synced_this_job ?? 0
          if (syncStatus?.sync_status === 'queued') {
            return emailsCount > 0
              ? `In queue… (${emailsCount} emails so far)`
              : 'In queue — starting soon…'
          }
          if (progress > 0) {
            return `Syncing... ${progress}%${emailsCount > 0 ? ` (${emailsCount} emails)` : ''}`
          }
          if (emailsCount > 0) {
            return `Syncing… (${emailsCount} emails)`
          }
          return 'Syncing in progress…'
        }
        if (syncStatus?.sync_status === 'completed') return 'Sync completed'
        if (syncStatus?.sync_status === 'failed') return 'Sync failed'
        if (syncStatus?.sync_status === 'not_connected') return 'Not connected'
        return gmailStatus?.connected ? 'Ready to sync' : 'Not connected'
      })(),
      icon: Activity,
      tone: isActivelySyncing
        ? 'text-blue-600 dark:text-blue-400 animate-pulse'
        : syncStatus?.sync_status === 'completed'
          ? 'text-green-600 dark:text-green-400'
          : syncStatus?.sync_status === 'failed'
            ? 'text-red-600 dark:text-red-400'
            : gmailStatus?.connected
              ? 'text-yellow-600 dark:text-yellow-400'
              : 'text-red-600 dark:text-red-400',
      showProgress: isActivelySyncing,
      progress: typeof syncStatus?.progress === 'number' ? syncStatus.progress : 0
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
            className="inline-flex items-center gap-2 rounded-lg border border-brand-text/20 dark:border-gray-600 px-4 py-2 text-sm font-medium text-brand-text hover:bg-brand-accent/10 dark:text-gray-200 dark:hover:bg-gray-700"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <button
            onClick={() => syncMutation.mutate()}
            disabled={
              syncMutation.isPending || gmailStatus?.connected === false || isActivelySyncing
            }
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
              <div className="space-y-4" aria-busy="true" aria-label="Loading Gmail sync status">
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    className="flex flex-col gap-2 rounded-xl border border-brand-text/10 bg-gray-50/80 px-4 py-3 dark:border-gray-700 dark:bg-gray-800/40"
                  >
                    <div className="flex items-center gap-3">
                      <div className="h-5 w-5 shrink-0 rounded-full bg-gray-200 dark:bg-gray-600" />
                      <div className="min-w-0 flex-1 space-y-2">
                        <div className="h-3 w-28 max-w-[55%] rounded bg-gray-200 dark:bg-gray-600" />
                        <div className="h-4 w-48 max-w-[85%] rounded bg-gray-200 dark:bg-gray-600" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
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
                  {item.label === 'Sync status' && gmailStatus?.connected ? (
                    <div className="mt-2 min-h-[3.25rem]">
                      {item.showProgress ? (
                        <>
                          <div className="flex items-center justify-between text-xs text-brand-text/60 dark:text-gray-400 mb-1.5">
                            <span className="font-medium">Progress</span>
                            <span className="font-semibold text-blue-600 dark:text-blue-400">
                              {hasDefiniteProgress
                                ? `${syncStatus?.progress}%`
                                : syncStatus?.sync_status === 'queued'
                                  ? 'Queued…'
                                  : 'Working…'}
                            </span>
                          </div>
                          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 overflow-hidden relative">
                            {hasDefiniteProgress ? (
                              <div
                                className="bg-blue-600 h-2.5 rounded-full transition-all duration-500 ease-out"
                                style={{ width: `${Math.min(100, syncStatus?.progress ?? 0)}%` }}
                              />
                            ) : (
                              <div className="relative h-2.5 w-full overflow-hidden rounded-full bg-blue-500/20">
                                <div
                                  className="absolute inset-0 bg-gradient-to-r from-blue-400/50 via-blue-500/90 to-blue-400/50"
                                  style={{
                                    backgroundSize: '200% 100%',
                                    animation: 'gmailSyncShimmer 2s linear infinite'
                                  }}
                                />
                              </div>
                            )}
                          </div>
                          <style>{`
                            @keyframes gmailSyncShimmer {
                              0% { background-position: -200% 0; }
                              100% { background-position: 200% 0; }
                            }
                          `}</style>
                        </>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ))
            )}

            {syncStatus?.error && (
              <div className="flex items-start gap-3 rounded-xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/30 p-4 text-sm text-red-800 dark:text-red-200">
                <AlertCircle className="h-5 w-5 shrink-0" />
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
