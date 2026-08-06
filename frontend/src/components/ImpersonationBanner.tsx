import { useQuery } from '@tanstack/react-query'
import { ShieldAlert, X } from 'lucide-react'
import { apiClient } from '../services/apiClient'
import { usePlatformAdmin } from '../hooks/usePlatformAdmin'
import { useAuth } from '../contexts/AuthContext'
import type { ImpersonationContext } from '../types/admin'

export const USER_PROFILE_QUERY_KEY = 'user-profile'

export function useUserProfile(userId?: number | null) {
  return useQuery({
    queryKey: [USER_PROFILE_QUERY_KEY, userId ?? null],
    queryFn: () => apiClient.getProfile(),
    enabled: Boolean(userId),
    staleTime: 60_000,
  })
}

export function ImpersonationBanner() {
  const { user } = useAuth()
  const { stopImpersonation } = usePlatformAdmin()
  const { data: profile } = useUserProfile(user?.id)
  const impersonation = (profile?.impersonation ?? null) as ImpersonationContext | null

  if (!impersonation?.active) {
    return null
  }

  return (
    <div className="sticky top-0 z-[60] border-b border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-950 dark:border-amber-700 dark:bg-amber-950/80 dark:text-amber-100">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <ShieldAlert className="h-4 w-4 shrink-0" />
          <span>
            Viewing as <strong>{user?.email}</strong>
            {impersonation.actor_email ? (
              <>
                {' '}
                (operator: {impersonation.actor_email})
              </>
            ) : null}
          </span>
        </div>
        <button
          type="button"
          onClick={() => void stopImpersonation()}
          className="inline-flex items-center gap-1 rounded-md border border-amber-400 px-2 py-1 text-xs font-medium hover:bg-amber-100 dark:hover:bg-amber-900"
        >
          <X className="h-3 w-3" />
          Exit impersonation
        </button>
      </div>
    </div>
  )
}
