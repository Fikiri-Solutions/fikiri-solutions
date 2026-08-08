import React, { useState } from 'react'
import { Mail, ArrowLeft, CheckCircle } from 'lucide-react'
import { RadiantLayout } from '../components/radiant'
import { motion, useReducedMotion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '../services/apiClient'
import { AUTOCOMPLETE } from '../constants/autocomplete'

export const ForgotPassword: React.FC = () => {
  const [email, setEmail] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const navigate = useNavigate()
  const reduceMotion = useReducedMotion()

  const validateEmail = (email: string) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return emailRegex.test(email)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')
    
    try {
      if (!email) {
        throw new Error('Please enter your email address')
      }
      
      if (!validateEmail(email)) {
        throw new Error('Please enter a valid email address')
      }
      
      const data = await apiClient.request<{ success?: boolean; error?: string }>(
        'POST',
        '/auth/forgot-password',
        { data: { email } }
      )

      if (data.success) {
        setSuccess(true)
      } else {
        setError(data.error || 'Failed to send reset email. Please try again.')
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Network error. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const panel = (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.45, ease: 'easeOut' }}
      className="w-full max-w-md min-w-0 rounded-3xl border border-white/40 bg-white p-5 shadow-2xl ring-1 ring-black/5 sm:p-8"
    >
      {success ? (
        <div className="text-center">
          <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
            <CheckCircle className="h-8 w-8 text-green-600" aria-hidden />
          </div>
          <h1 className="mb-3 text-2xl font-bold text-stone-900 font-serif">Check Your Email</h1>
          <p className="mb-6 text-sm text-stone-600 leading-relaxed">
            We&apos;ve sent a password reset link to <strong className="text-stone-900">{email}</strong>.
            Please check your email and click the link to reset your password.
          </p>
          <div className="space-y-3">
            <button
              type="button"
              onClick={() => navigate('/login')}
              className="w-full min-h-[44px] rounded-xl bg-brand-primary px-6 py-3 font-medium text-white touch-manipulation hover:bg-fikiri-400 transition-colors"
            >
              Back to Login
            </button>
            <button
              type="button"
              onClick={() => {
                setSuccess(false)
                setEmail('')
              }}
              className="w-full min-h-[44px] rounded-xl px-6 py-3 font-medium text-stone-700 touch-manipulation hover:bg-stone-100 transition-colors"
            >
              Try Different Email
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="mb-6 text-center">
            <h1 className="mb-2 text-2xl font-bold text-stone-900 font-serif">Forgot Password?</h1>
            <p className="text-sm text-stone-600 leading-relaxed">
              Enter your email address and we&apos;ll send you a link to reset your password.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6" autoComplete="on">
            {error && (
              <div className="rounded-xl border border-red-200 bg-red-50 p-4">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            <div>
              <label htmlFor="email" className="mb-2 block text-sm font-medium text-stone-800">
                Email Address
              </label>
              <div className="relative">
                <Mail className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-stone-500" aria-hidden />
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete={AUTOCOMPLETE.forgotPassword.email}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-xl border border-stone-300 bg-stone-50 py-3 pl-10 pr-4 text-stone-900 placeholder:text-stone-500 focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary"
                  placeholder="Enter your email address"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="flex w-full min-h-[44px] items-center justify-center rounded-xl bg-brand-primary px-6 py-3 font-medium text-white touch-manipulation transition-colors hover:bg-fikiri-400 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <div className="mr-2 h-5 w-5 animate-spin rounded-full border-b-2 border-white" aria-hidden />
                  Sending Reset Link...
                </>
              ) : (
                'Send Reset Link'
              )}
            </button>

            <div className="text-center">
              <button
                type="button"
                onClick={() => navigate('/login')}
                className="inline-flex min-h-[44px] items-center justify-center text-stone-700 touch-manipulation transition-colors hover:text-stone-900"
              >
                <ArrowLeft className="mr-2 h-4 w-4" aria-hidden />
                Back to Login
              </button>
            </div>
          </form>
        </>
      )}
    </motion.div>
  )

  return (
    <RadiantLayout showFooterCta={false} backdropIntensity="subtle">
      <div className="relative overflow-x-clip">
        <div className="pointer-events-none absolute inset-0" aria-hidden>
          <div className="absolute -left-16 top-10 h-56 w-56 rounded-full bg-brand-accent/12 blur-3xl sm:h-72 sm:w-72" />
          <div className="absolute -right-20 top-40 h-64 w-64 rounded-full bg-brand-secondary/12 blur-3xl sm:h-96 sm:w-96" />
        </div>
        <div className="relative z-10 flex items-start justify-center px-4 pb-10 pt-4 sm:items-center sm:px-6 sm:pb-16 sm:pt-8">
          <div className="w-full max-w-md min-w-0">
            {!success && (
              <div className="mb-5 text-center sm:mb-6">
                <h2 className="text-3xl font-bold font-serif tracking-tight text-white sm:text-4xl">
                  Reset password
                </h2>
                <p className="mt-1 text-base text-white/85">We&apos;ll email you a secure link</p>
              </div>
            )}
            {panel}
          </div>
        </div>
      </div>
    </RadiantLayout>
  )
}
