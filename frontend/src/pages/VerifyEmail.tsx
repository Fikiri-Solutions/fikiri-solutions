import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { toast } from 'react-hot-toast'
import { CheckCircle2, Mail, AlertCircle } from 'lucide-react'
import { useAuth, type User } from '../contexts/AuthContext'
import { apiClient } from '../services/apiClient'
import { RadiantLayout } from '../components/radiant'
import { safeInternalPath } from '../utils/safeInternalPath'

type VerifyPhase = 'loading' | 'success' | 'error'

function continuePathFor(user: { onboarding_completed?: boolean } | null | undefined): string {
  return user?.onboarding_completed ? '/dashboard' : '/onboarding'
}

export const VerifyEmail: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { user, isAuthenticated, updateUser } = useAuth()

  const token = useMemo(() => {
    const raw = searchParams.get('token')
    return raw ? raw.trim() : ''
  }, [searchParams])

  const [phase, setPhase] = useState<VerifyPhase>(() => (token ? 'loading' : 'error'))
  const [error, setError] = useState<string | null>(() =>
    token ? null : 'This verification link is missing a token.'
  )
  const [verifiedUser, setVerifiedUser] = useState<{ onboarding_completed?: boolean } | null>(null)
  const hasHandledRef = useRef(false)

  useEffect(() => {
    const run = async () => {
      if (hasHandledRef.current) return
      if (!token) {
        setPhase('error')
        setError('This verification link is missing a token.')
        return
      }

      setPhase('loading')
      setError(null)
      try {
        const data = await apiClient.verifyEmail(token)
        if (data?.success) {
          hasHandledRef.current = true
          const nextUser = data?.data ?? null
          setVerifiedUser(nextUser)
          setPhase('success')
          toast.success('Email verified successfully!')

          const nextPath = continuePathFor(nextUser)

          if (isAuthenticated && user) {
            updateUser({
              ...user,
              ...nextUser,
              email_verified: true,
            } as User)
            navigate(nextPath, { replace: true })
            return
          }

          try {
            const whoami = await apiClient.whoami()
            const sessionUser = whoami?.data?.user
            if (whoami?.success && sessionUser) {
              updateUser({
                ...sessionUser,
                email_verified: true,
              } as User)
              navigate(continuePathFor(sessionUser), { replace: true })
              return
            }
          } catch {
            // Different browser context / no session — show sign-in success UI below.
          }
        } else {
          setPhase('error')
          setError(data?.error || 'This verification link is invalid or has expired.')
        }
      } catch (e: unknown) {
        const err = e as { response?: { data?: { error?: string } }; message?: string }
        setPhase('error')
        setError(
          err?.response?.data?.error ||
            err?.message ||
            'This verification link is invalid or has expired.'
        )
      }
    }

    void run()
  }, [token, isAuthenticated, user, navigate, updateUser])

  const destination = continuePathFor(verifiedUser ?? user)
  const loginHref = `/login?redirect=${encodeURIComponent(
    safeInternalPath(destination) ?? '/onboarding'
  )}`

  const handleContinue = () => {
    navigate(destination, { replace: true })
  }

  return (
    <RadiantLayout showFooterCta={false} backdropIntensity="subtle">
      <div className="relative overflow-x-clip">
        <div className="relative z-10 flex items-start justify-center px-4 pb-10 pt-4 sm:items-center sm:px-6 sm:pb-16 sm:pt-8">
          <div className="w-full max-w-lg min-w-0">
            <div className="rounded-3xl border border-white/40 bg-white p-5 shadow-2xl ring-1 ring-black/5 sm:p-8">
              <div className="flex items-start gap-3">
                <div className="mt-1 shrink-0">
                  {phase === 'success' ? (
                    <CheckCircle2 className="h-6 w-6 text-green-600" aria-hidden />
                  ) : phase === 'error' ? (
                    <AlertCircle className="h-6 w-6 text-red-600" aria-hidden />
                  ) : (
                    <Mail className="h-6 w-6 text-brand-primary" aria-hidden />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <h1 className="text-2xl font-bold font-serif text-stone-900">
                    {phase === 'success'
                      ? 'Email verified'
                      : phase === 'error'
                        ? 'Verification link expired'
                        : 'Verifying your email'}
                  </h1>
                  <p className="mt-2 text-sm leading-relaxed text-stone-600">
                    {phase === 'loading' &&
                      'Please wait a moment while we confirm your verification link.'}
                    {phase === 'success' &&
                      (isAuthenticated
                        ? 'Your email is verified. We’ll continue setting up your workspace.'
                        : 'Your email has been verified. Please sign in to continue setting up your account.')}
                    {phase === 'error' &&
                      'This verification link is invalid or has expired. Please sign in or request a new verification email from your account.'}
                  </p>
                </div>
              </div>

              <div className="mt-6">
                {phase === 'loading' && (
                  <div className="flex min-h-[44px] items-center gap-3 text-sm text-stone-600">
                    <div
                      className="h-5 w-5 animate-spin rounded-full border-2 border-brand-primary border-t-transparent"
                      aria-hidden
                    />
                    Verifying…
                  </div>
                )}

                {phase === 'error' && (
                  <div className="space-y-3">
                    {error && (
                      <div className="rounded-xl border border-red-200 bg-red-50 p-4">
                        <p className="text-sm text-red-700">{error}</p>
                      </div>
                    )}
                    <div className="flex flex-col gap-3 sm:flex-row">
                      <Link
                        to="/login"
                        className="inline-flex min-h-[44px] w-full items-center justify-center rounded-xl bg-brand-primary px-4 py-3 text-center font-medium text-white touch-manipulation hover:bg-fikiri-400 sm:w-auto sm:flex-1"
                      >
                        Sign in
                      </Link>
                      {isAuthenticated && (
                        <button
                          type="button"
                          onClick={async () => {
                            try {
                              await apiClient.resendEmailVerification()
                              toast.success('Verification email sent. Check your inbox and spam folder.')
                            } catch (e: unknown) {
                              const err = e as { response?: { data?: { error?: string } }; message?: string }
                              toast.error(
                                err?.response?.data?.error ||
                                  err?.message ||
                                  'Failed to resend verification email.'
                              )
                            }
                          }}
                          className="inline-flex min-h-[44px] w-full items-center justify-center rounded-xl border border-stone-300 bg-stone-50 px-4 py-3 font-medium text-stone-800 touch-manipulation hover:bg-stone-100 sm:w-auto sm:flex-1"
                        >
                          Resend verification email
                        </button>
                      )}
                    </div>
                    {!isAuthenticated && (
                      <p className="text-xs text-stone-500">
                        After you sign in, you can resend a verification email from the setup banner if needed.
                      </p>
                    )}
                  </div>
                )}

                {phase === 'success' && (
                  <div className="space-y-3">
                    {isAuthenticated ? (
                      <button
                        type="button"
                        onClick={handleContinue}
                        className="inline-flex min-h-[44px] w-full items-center justify-center rounded-xl bg-brand-primary px-4 py-3 font-medium text-white touch-manipulation hover:bg-fikiri-400"
                      >
                        Continue
                      </button>
                    ) : (
                      <Link
                        to={loginHref}
                        className="inline-flex min-h-[44px] w-full items-center justify-center rounded-xl bg-brand-primary px-4 py-3 text-center font-medium text-white touch-manipulation hover:bg-fikiri-400"
                      >
                        Sign in to continue
                      </Link>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </RadiantLayout>
  )
}
