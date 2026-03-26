import React, { useMemo, useState } from 'react'
import { Mail, AlertTriangle, RefreshCw } from 'lucide-react'
import type { User } from '../contexts/AuthContext'
import { useAuth } from '../contexts/AuthContext'
import { apiClient } from '../services/apiClient'
import { toast } from 'react-hot-toast'

export const EmailVerificationBanner: React.FC<{ user?: User | null }> = ({ user }) => {
  const { user: authUser, updateUser } = useAuth()
  const effectiveUser = user ?? authUser

  // Backend may return `email_verified` as `1` (number) or `true` (boolean).
  // Treat any truthy value as verified.
  const emailVerified = !!effectiveUser?.email_verified
  const userEmail = effectiveUser?.email

  const [resending, setResending] = useState(false)
  const [refreshingStatus, setRefreshingStatus] = useState(false)

  const shouldShow = useMemo(() => !!effectiveUser && !emailVerified, [effectiveUser, emailVerified])
  if (!shouldShow) return null

  const handleResend = async () => {
    if (resending) return
    setResending(true)
    try {
      await apiClient.resendEmailVerification()
      toast.success('Verification email sent. Check your inbox and spam folder.')
    } catch (e: any) {
      toast.error(e?.response?.data?.error || e?.message || 'Failed to resend verification email.')
    } finally {
      setResending(false)
    }
  }

  const handleAlreadyVerified = async () => {
    if (refreshingStatus) return
    setRefreshingStatus(true)
    try {
      const data = await apiClient.whoami()
      const nextUser = data?.data?.user
      if (data?.success && nextUser) {
        const nextVerified = !!nextUser.email_verified
        updateUser({
          ...(effectiveUser as User),
          ...nextUser,
          email_verified: nextVerified,
        } as User)

        if (nextVerified) {
          toast.success('Thanks for verifying your email.')
        } else {
          toast('Still not verified yet—please check the link in your inbox.')
        }
      } else {
        toast.error(data?.error || 'Failed to refresh verification status.')
      }
    } catch (e: any) {
      toast.error(e?.response?.data?.error || e?.message || 'Failed to refresh verification status.')
    } finally {
      setRefreshingStatus(false)
    }
  }

  return (
    <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 dark:bg-amber-900/20 dark:border-amber-800 p-4">
      <div className="flex items-start gap-3">
        <AlertTriangle className="h-5 w-5 text-amber-700 dark:text-amber-300 mt-0.5 flex-shrink-0" />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <Mail className="h-4 w-4 text-amber-700 dark:text-amber-300" />
            <p className="text-sm font-semibold text-amber-900 dark:text-amber-100">
              Verify your email
            </p>
          </div>
          <p className="text-sm text-amber-800 dark:text-amber-200 mt-1">
            We sent a verification link to <span className="font-medium">{userEmail}</span>. You can complete onboarding now, but
            verification is required before enabling higher-trust features like live integrations and production API keys.
          </p>

          <div className="mt-3 flex flex-col sm:flex-row gap-2">
            <button
              onClick={handleResend}
              disabled={resending}
              className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
            >
              {resending ? <RefreshCw className="h-4 w-4 animate-spin" /> : null}
              Resend verification email
            </button>

            <button
              onClick={handleAlreadyVerified}
              disabled={refreshingStatus}
              className="inline-flex items-center justify-center px-4 py-2 rounded-lg bg-amber-100 hover:bg-amber-200 dark:bg-amber-900/20 dark:hover:bg-amber-900/35 disabled:opacity-50 disabled:cursor-not-allowed text-amber-900 dark:text-amber-100 text-sm font-medium transition-colors"
            >
              {refreshingStatus ? 'Checking...' : 'I already verified'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

