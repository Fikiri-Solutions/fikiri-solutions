/**
 * Canonical copy for how paid signup works (Billing → Stripe Checkout → access).
 * Keep in sync with BillingPage (handleSelectPlan → createCheckoutSession).
 * Success/cancel URLs: see core/billing_api.py create_checkout_session (dashboard / pricing).
 */

export type SubscriptionSignupStep = {
  heading: string
  detail: string
}

export const SUBSCRIPTION_SIGNUP_STEPS: readonly SubscriptionSignupStep[] = [
  {
    heading: 'Open billing',
    detail:
      'Use “Go to billing & plans” (or the Billing link in the sidebar). You must be signed in with this account.',
  },
  {
    heading: 'Choose billing period',
    detail: 'Pick Monthly or Yearly on the Billing page. Yearly pricing shows any advertised discount.',
  },
  {
    heading: 'Select a plan',
    detail:
      'Click “Select Plan” on the tier you want. We open a secure Stripe Checkout page in this browser window. If you leave checkout early, you may land on the marketing pricing page—open Billing from the sidebar again to retry.',
  },
  {
    heading: 'Pay or start a trial',
    detail:
      'Enter your payment details on Stripe. If your plan includes a trial, it will be shown before you confirm. Charges are processed by Stripe, not stored on our servers.',
  },
  {
    heading: 'Return to the app',
    detail:
      'After checkout, Stripe redirects you back to this app (typically your dashboard). Your subscription is recorded automatically; if the app still asks you to subscribe, wait a minute and refresh, or open Billing to confirm your plan.',
  },
]

const BILLING_FIRST_STEP: SubscriptionSignupStep = {
  heading: 'You are on Billing',
  detail:
    'Scroll to “Available Plans” below. Choose Monthly or Yearly, then click “Select Plan” on a tier. You are already in the right place—use the sidebar Billing link only if you left this page.',
}

/** Gate vs Billing: step 1 differs so we do not tell users to “open Billing” while they are already there. */
export function getSubscriptionSignupSteps(variant: 'gate' | 'billing'): SubscriptionSignupStep[] {
  if (variant === 'billing') {
    return [BILLING_FIRST_STEP, ...SUBSCRIPTION_SIGNUP_STEPS.slice(1)]
  }
  return [...SUBSCRIPTION_SIGNUP_STEPS]
}
