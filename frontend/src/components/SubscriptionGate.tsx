import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { CreditCard, Mail, Loader2 } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { apiClient } from '../services/apiClient'
import { config } from '../config'
import { hasActiveSubscription, isSubscriptionGateEnabled } from '../lib/subscriptionAccess'
import { getSubscriptionSignupSteps } from '../content/subscriptionSignupInstructions'

const CONSULTING_MAILTO =
  'mailto:info@fikirisolutions.com?subject=' +
  encodeURIComponent('Consulting / custom services inquiry')

interface SubscriptionGateProps {
  children: React.ReactNode
}

/** Paths that stay usable without an active paid/trial subscription (checkout). */
const BILLING_PATH_PREFIX = '/billing'

export const SubscriptionGate: React.FC<SubscriptionGateProps> = ({ children }) => {
  const { user, isAuthenticated } = useAuth()
  const location = useLocation()
  const gateOn = isSubscriptionGateEnabled()
  const onBilling = location.pathname === BILLING_PATH_PREFIX || location.pathname.startsWith(`${BILLING_PATH_PREFIX}/`)

  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ['current-subscription', user?.id],
    queryFn: async () => {
      try {
        return await apiClient.getCurrentSubscription()
      } catch (error: unknown) {
        const err = error as { response?: { status?: number } }
        if (err?.response?.status === 404 || err?.response?.status === 401) {
          return { success: true, subscription: null, message: 'No active subscription' }
        }
        throw error
      }
    },
    enabled: gateOn && isAuthenticated && !!user && !onBilling,
    staleTime: 30 * 1000,
    retry: 1,
  })

  if (!gateOn || !isAuthenticated || !user) {
    return <>{children}</>
  }

  if (onBilling) {
    return <>{children}</>
  }

  if (isPending) {
    return (
      <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3 text-brand-text dark:text-gray-300">
        <Loader2 className="h-10 w-10 animate-spin text-brand-primary" aria-hidden />
        <p className="text-sm">Checking your plan…</p>
      </div>
    )
  }

  if (isError) {
    return (
      <div
        className="mx-auto max-w-lg rounded-xl border border-amber-200 bg-amber-50 p-6 text-center dark:border-amber-800 dark:bg-amber-950/40"
        role="alert"
      >
        <p className="text-sm text-amber-900 dark:text-amber-100">
          We couldn&apos;t verify your subscription. Try again, or go to Billing to continue.
        </p>
        <div className="mt-4 flex flex-wrap justify-center gap-3">
          <button
            type="button"
            onClick={() => refetch()}
            className="rounded-lg bg-brand-primary px-4 py-2 text-sm font-medium text-white hover:opacity-90"
          >
            Retry
          </button>
          <Link
            to="/billing"
            className="rounded-lg border border-amber-300 px-4 py-2 text-sm font-medium text-amber-900 hover:bg-amber-100 dark:border-amber-600 dark:text-amber-100 dark:hover:bg-amber-900/50"
          >
            Billing
          </Link>
        </div>
      </div>
    )
  }

  if (hasActiveSubscription(data)) {
    return <>{children}</>
  }

  return (
    <div className="mx-auto max-w-2xl rounded-2xl border border-gray-200 bg-white p-8 shadow-sm dark:border-gray-700 dark:bg-gray-800/80">
      <div className="text-center">
        <h1 className="text-2xl font-semibold text-brand-text dark:text-white">Subscription required</h1>
        <p className="mt-3 text-base text-gray-600 dark:text-gray-300">
          Your account is signed in, but there isn&apos;t an active subscription or trial on file. To use{' '}
          {config.appName}, complete signup and payment using the steps below (secure checkout via Stripe), or contact us
          for consulting.
        </p>
      </div>

      <section className="mt-8 text-left" aria-labelledby="gate-how-to-subscribe">
        <h2 id="gate-how-to-subscribe" className="text-lg font-semibold text-brand-text dark:text-gray-100">
          How to subscribe and pay
        </h2>
        <ol className="mt-4 list-decimal space-y-4 pl-5 text-sm text-gray-600 dark:text-gray-300 marker:text-brand-primary">
          {getSubscriptionSignupSteps('gate').map((step) => (
            <li key={step.heading}>
              <span className="font-medium text-brand-text dark:text-gray-100">{step.heading}.</span>{' '}
              {step.detail}
            </li>
          ))}
        </ol>
        <p className="mt-4 text-xs text-gray-500 dark:text-gray-400">
          Billing is handled by Stripe. We do not store your full card number on our servers. If you need enterprise
          pricing, onboarding, or services outside self-serve plans, use the consulting options below.
        </p>
      </section>

      <section className="mt-8 text-left" aria-labelledby="gate-consulting">
        <h2 id="gate-consulting" className="text-lg font-semibold text-brand-text dark:text-gray-100">
          Consulting &amp; custom services
        </h2>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
          For implementations, training, or engagements that are not covered by standard plans, email us or use the contact
          form.
        </p>
      </section>

      <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:justify-center">
        <Link
          to="/billing"
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-brand-primary px-5 py-3 text-sm font-semibold text-white shadow hover:opacity-95 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:ring-offset-2 dark:focus:ring-offset-gray-900"
        >
          <CreditCard className="h-4 w-4 shrink-0" aria-hidden />
          Go to billing &amp; plans
        </Link>
        <Link
          to="/pricing"
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-5 py-3 text-sm font-semibold text-brand-text hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:hover:bg-gray-700"
        >
          View pricing
        </Link>
        <a
          href={CONSULTING_MAILTO}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-5 py-3 text-sm font-semibold text-brand-text hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:hover:bg-gray-700"
        >
          <Mail className="h-4 w-4 shrink-0" aria-hidden />
          Email us (consulting)
        </a>
        <Link
          to="/contact"
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-transparent px-5 py-3 text-sm font-semibold text-brand-primary hover:underline"
        >
          Contact form
        </Link>
      </div>
    </div>
  )
}
