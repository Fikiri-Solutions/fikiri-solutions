import { useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../services/apiClient'
import { useAuth } from '../contexts/AuthContext'
import type { AdminTenant, PlatformAdminContext } from '../types/admin'

const ADMIN_SESSION_BACKUP_KEY = 'fikiri-admin-session-backup'
export const PLATFORM_ADMIN_ME_QUERY_KEY = 'platform-admin-me'

interface AdminSessionBackup {
  accessToken: string | null
  refreshToken: string | null
  user: string | null
  userId: string | null
}

function readBackup(): AdminSessionBackup | null {
  if (typeof window === 'undefined') return null
  const raw = sessionStorage.getItem(ADMIN_SESSION_BACKUP_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as AdminSessionBackup
  } catch {
    return null
  }
}

function writeBackup(): void {
  if (typeof window === 'undefined') return
  const backup: AdminSessionBackup = {
    accessToken: localStorage.getItem('fikiri-token'),
    refreshToken: localStorage.getItem('fikiri-refresh-token'),
    user: localStorage.getItem('fikiri-user'),
    userId: localStorage.getItem('fikiri-user-id'),
  }
  sessionStorage.setItem(ADMIN_SESSION_BACKUP_KEY, JSON.stringify(backup))
}

function restoreBackup(): boolean {
  const backup = readBackup()
  if (!backup || typeof window === 'undefined') return false
  if (backup.accessToken) localStorage.setItem('fikiri-token', backup.accessToken)
  else localStorage.removeItem('fikiri-token')
  if (backup.refreshToken) localStorage.setItem('fikiri-refresh-token', backup.refreshToken)
  else localStorage.removeItem('fikiri-refresh-token')
  if (backup.user) localStorage.setItem('fikiri-user', backup.user)
  if (backup.userId) localStorage.setItem('fikiri-user-id', backup.userId)
  sessionStorage.removeItem(ADMIN_SESSION_BACKUP_KEY)
  return true
}

/** Pure helper for nav/tests: show Admin only after a successful operator confirmation. */
export function shouldShowPlatformAdminNav(state: {
  loading: boolean
  isPlatformAdmin: boolean
  failed?: boolean
}): boolean {
  if (state.loading || state.failed) return false
  return Boolean(state.isPlatformAdmin)
}

/**
 * Shared platform-operator context (single React Query cache across Layout / AdminRoute / pages).
 * Operator status comes only from GET /api/admin/platform/me — never from tenant role.
 */
export function usePlatformAdmin() {
  const { isAuthenticated, user } = useAuth()
  const queryClient = useQueryClient()

  const query = useQuery({
    queryKey: [PLATFORM_ADMIN_ME_QUERY_KEY, user?.id ?? null],
    queryFn: () => apiClient.getPlatformAdminContext(),
    enabled: Boolean(isAuthenticated && user?.id),
    retry: false,
    staleTime: 60_000,
  })

  const loading = Boolean(isAuthenticated && user?.id) && query.isLoading
  const context = query.data ?? null
  const failed = query.isError
  const error = failed ? 'Failed to load admin context' : null

  const refresh = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: [PLATFORM_ADMIN_ME_QUERY_KEY] })
  }, [queryClient])

  const startImpersonation = useCallback(async (
    tenant: AdminTenant,
    password: string,
    mfaCode?: string,
    recoveryCode?: string,
  ) => {
    writeBackup()
    // Server-side step-up only — never treat local success as authorization.
    const stepUp = await apiClient.reauthenticateAdmin({
      password,
      mfa_code: mfaCode,
      recovery_code: recoveryCode,
    })
    if (!stepUp?.step_up_confirmed) {
      throw new Error('Step-up authentication required')
    }
    const result = await apiClient.startPlatformImpersonation(tenant.id)
    const token = result.tokens?.access_token
    if (!token) {
      throw new Error('Impersonation token missing')
    }
    localStorage.setItem('fikiri-token', token)
    localStorage.removeItem('fikiri-refresh-token')
    if (result.target_user) {
      localStorage.setItem('fikiri-user', JSON.stringify(result.target_user))
      localStorage.setItem('fikiri-user-id', String(result.target_user.id))
    }
    window.location.assign('/dashboard')
  }, [])

  const stopImpersonation = useCallback(async () => {
    try {
      await apiClient.stopPlatformImpersonation()
    } catch {
      // Still attempt local restore if server rejects (e.g. token already expired).
    }
    if (!restoreBackup()) {
      localStorage.removeItem('fikiri-token')
      localStorage.removeItem('fikiri-refresh-token')
    }
    window.location.assign('/admin')
  }, [])

  return {
    context,
    loading,
    error,
    refresh,
    startImpersonation,
    stopImpersonation,
    showAdminNav: shouldShowPlatformAdminNav({
      loading,
      isPlatformAdmin: Boolean(context?.is_platform_admin),
      failed,
    }),
    hasCapability: (capability: string) => Boolean(context?.capabilities?.includes(capability)),
  }
}
