import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { toast } from 'react-hot-toast'
import { CheckCircle2, Mail, AlertCircle } from 'lucide-react'
import { useAuth, type User } from '../contexts/AuthContext'
import { apiClient } from '../services/apiClient'

export const VerifyEmail: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { user, isAuthenticated, updateUser } = useAuth()

  const token = useMemo(() => {
    const raw = searchParams.get('token')
    return raw ? raw.trim() : ''
  }, [searchParams])

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [verified, setVerified] = useState(false)
  const hasHandledRef = useRef(false)

  useEffect(() => {
    const run = async () => {
      if (hasHandledRef.current) return
      if (!token) {
        setError('Missing verification token.')
        return
      }

      setLoading(true)
      setError(null)
      try {
        const data = await apiClient.verifyEmail(token)
        if (data?.success) {
          hasHandledRef.current = true
          setVerified(true)
          toast.success('Email verified successfully!')

          const verifiedUser = data?.data
          const nextPath = verifiedUser?.onboarding_completed ? '/dashboard' : '/onboarding'

          // If the user is already signed in, update local auth state + redirect.
          if (isAuthenticated && user) {
            updateUser({
              ...user,
              ...verifiedUser,
              email_verified: true,
            } as User)
            navigate(nextPath, { replace: true })
            return
          }

          // If AuthContext hasn't marked us as authenticated yet, attempt to refresh.
          try {
            const whoami = await apiClient.whoami()
            const nextUser = whoami?.data?.user
            if (whoami?.success && nextUser) {
              updateUser({
                ...nextUser,
                email_verified: true,
              } as User)
              navigate(nextPath, { replace: true })
              return
            }
          } catch {
            // If we can't refresh auth, fall back to the UI below (Go to Login).
          }
        } else {
          setError(data?.error || 'Verification failed.')
        }
      } catch (e: any) {
        setError(e?.response?.data?.error || e?.message || 'Verification failed.')
      } finally {
        setLoading(false)
      }
    }

    run()
  }, [token, isAuthenticated, user, navigate, updateUser])

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12 bg-gray-50 dark:bg-gray-900">
      <div className="w-full max-w-lg">
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700 p-8">
          <div className="flex items-start gap-3">
            <div className="mt-1">
              {verified ? (
                <CheckCircle2 className="h-6 w-6 text-green-600 dark:text-green-400" />
              ) : (
                <Mail className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              )}
            </div>
            <div className="min-w-0 flex-1">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                {verified ? 'Email Verified' : 'Verify Your Email'}
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-300 mt-2">
                {verified
                  ? 'You can now finish setup and enable integrations.'
                  : 'Click below if you are already signed in, or sign in after verification.'}
              </p>
            </div>
          </div>

          <div className="mt-6">
            {loading && (
              <div className="flex items-center gap-3 text-sm text-gray-600 dark:text-gray-300">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-brand-primary" />
                Verifying...
              </div>
            )}

            {!loading && error && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-red-800 dark:text-red-200">Verification failed</p>
                  <p className="text-sm text-red-700 dark:text-red-300 mt-1">{error}</p>
                </div>
              </div>
            )}

            {!loading && verified && (
              <div className="mt-4 space-y-3">
                {isAuthenticated ? (
                  <button
                    onClick={() => navigate(user?.onboarding_completed ? '/dashboard' : '/onboarding', { replace: true })}
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-3 rounded-xl font-medium transition-colors"
                  >
                    Continue
                  </button>
                ) : (
                  <div className="space-y-2">
                    <p className="text-sm text-gray-600 dark:text-gray-300">
                      You verified the email successfully. Please sign in to continue.
                    </p>
                    <Link
                      to="/login"
                      className="block w-full text-center bg-blue-600 hover:bg-blue-700 text-white px-4 py-3 rounded-xl font-medium transition-colors"
                    >
                      Go to Login
                    </Link>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
