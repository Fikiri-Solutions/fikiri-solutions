import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../contexts/AuthContext'
import { apiClient } from '../services/apiClient'
import { useToast } from '../components/Toast'
import {
  CreditCard,
  FileText,
  XCircle,
  CheckCircle,
  ArrowUpRight,
  Loader2,
  Settings
} from 'lucide-react'

export const BillingPage: React.FC = () => {
  const navigate = useNavigate()
  const { user, isAuthenticated } = useAuth()
  const { addToast } = useToast()
  const [billingPeriod, setBillingPeriod] = useState<'monthly' | 'yearly'>('monthly')
  const [loadingAction, setLoadingAction] = useState<string | null>(null)

  const { data: pricingTiers = {}, isLoading: pricingLoading } = useQuery({
    queryKey: ['pricing-tiers'],
    queryFn: () => apiClient.getPricingTiers(),
    staleTime: 5 * 60 * 1000
  })

  const { data: subscription, isLoading: subscriptionLoading, error: subscriptionError } = useQuery({
    queryKey: ['current-subscription', user?.id],
    queryFn: async () => {
      try {
        return await apiClient.getCurrentSubscription()
      } catch (error: any) {
        if (error?.response?.status === 404 || error?.response?.status === 401) {
          return { success: true, subscription: null, message: 'No active subscription' }
        }
        throw error
      }
    },
    enabled: !!isAuthenticated,
    staleTime: 30 * 1000,
    retry: 1
  })

  const { data: invoices = [], isLoading: invoicesLoading, error: invoicesError } = useQuery({
    queryKey: ['invoices', user?.id],
    queryFn: async () => {
      try {
        return await apiClient.getInvoices()
      } catch (error: any) {
        if (error?.response?.status === 404 || error?.response?.status === 401) {
          return []
        }
        throw error
      }
    },
    enabled: !!isAuthenticated,
    staleTime: 60 * 1000,
    retry: 1
  })

  const { data: paymentMethods = [], isLoading: paymentMethodsLoading, refetch: refetchPaymentMethods } = useQuery({
    queryKey: ['payment-methods', user?.id],
    queryFn: async () => {
      try {
        return await apiClient.getPaymentMethods()
      } catch (error: any) {
        if (error?.response?.status === 404 || error?.response?.status === 401) {
          return []
        }
        throw error
      }
    },
    enabled: !!isAuthenticated,
    staleTime: 30 * 1000,
    retry: 1
  })

  const { data: customerDetails, isLoading: customerDetailsLoading } = useQuery({
    queryKey: ['customer-details', user?.id],
    queryFn: async () => {
      try {
        return await apiClient.getCustomerDetails()
      } catch (error: any) {
        if (error?.response?.status === 404 || error?.response?.status === 401) {
          return null
        }
        throw error
      }
    },
    enabled: !!isAuthenticated,
    staleTime: 60 * 1000,
    retry: 1
  })

  const handleSelectPlan = async (tierName: string) => {
    if (!isAuthenticated) {
      addToast({
        type: 'info',
        title: 'Sign in required',
        message: 'Please sign in to select a plan'
      })
      navigate('/login?redirect=/billing')
      return
    }

    try {
      setLoadingAction(`select-${tierName}`)
      const billingPeriodParam = billingPeriod === 'monthly' ? 'monthly' : 'annual'
      const { checkout_url } = await apiClient.createCheckoutSession(tierName, billingPeriodParam, true)
      window.location.href = checkout_url
    } catch (error: any) {
      addToast({
        type: 'error',
        title: 'Checkout Failed',
        message: error?.message || 'Failed to start checkout'
      })
      setLoadingAction(null)
    }
  }

  const handleCancelSubscription = async (subscriptionId: string) => {
    if (!confirm('Are you sure you want to cancel your subscription? You\'ll continue to have access until the end of your billing period.')) {
      return
    }

    try {
      setLoadingAction('cancel')
      await apiClient.cancelSubscription(subscriptionId, true)
      addToast({
        type: 'success',
        title: 'Subscription Canceled',
        message: 'Your subscription will remain active until the end of the current billing period'
      })
    } catch (error: any) {
      addToast({
        type: 'error',
        title: 'Cancel Failed',
        message: error?.message || 'Failed to cancel subscription'
      })
    } finally {
      setLoadingAction(null)
    }
  }

  const handleManagePayment = async () => {
    try {
      setLoadingAction('portal')
      const { url } = await apiClient.createPortalSession()
      window.location.href = url
    } catch (error: any) {
      addToast({
        type: 'error',
        title: 'Portal Access Failed',
        message: error?.message || 'Failed to open billing portal'
      })
      setLoadingAction(null)
    }
  }

  const handleRemovePaymentMethod = async (paymentMethodId: string) => {
    if (!confirm('Are you sure you want to remove this payment method?')) {
      return
    }

    try {
      setLoadingAction(`remove-${paymentMethodId}`)
      await apiClient.removePaymentMethod(paymentMethodId)
      addToast({
        type: 'success',
        title: 'Payment Method Removed',
        message: 'The payment method has been removed successfully'
      })
      refetchPaymentMethods()
    } catch (error: any) {
      addToast({
        type: 'error',
        title: 'Remove Failed',
        message: error?.message || 'Failed to remove payment method'
      })
    } finally {
      setLoadingAction(null)
    }
  }

  const handleSetDefault = async (paymentMethodId: string) => {
    try {
      setLoadingAction(`default-${paymentMethodId}`)
      await apiClient.setDefaultPaymentMethod(paymentMethodId)
      addToast({
        type: 'success',
        title: 'Default Updated',
        message: 'Default payment method updated successfully'
      })
      refetchPaymentMethods()
    } catch (error: any) {
      addToast({
        type: 'error',
        title: 'Update Failed',
        message: error?.message || 'Failed to set default payment method'
      })
    } finally {
      setLoadingAction(null)
    }
  }

  const handleAddPaymentMethod = async (type: 'card' | 'ach' = 'card') => {
    try {
      setLoadingAction('add-payment')
      const { client_secret } = await apiClient.createSetupIntent(type === 'ach' ? ['us_bank_account'] : ['card'])
      
      // Redirect to Stripe Elements or use Stripe.js to collect payment method
      // For now, redirect to portal for adding payment methods
      const { url } = await apiClient.createPortalSession()
      window.location.href = url
    } catch (error: any) {
      addToast({
        type: 'error',
        title: 'Add Payment Method Failed',
        message: error?.message || 'Failed to add payment method'
      })
      setLoadingAction(null)
    }
  }

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }

  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(amount)
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-8 text-center">
            <CreditCard className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Sign In Required</h2>
            <p className="text-gray-600 dark:text-gray-400 mb-6">Please sign in to manage your billing</p>
            <button
              onClick={() => navigate('/login?redirect=/billing')}
              className="px-6 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700"
            >
              Sign In
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Billing & Subscription</h1>
          <p className="text-gray-600 dark:text-gray-400">Manage your subscription, payment methods, and invoices</p>
        </div>

        {/* Current Subscription */}
        {subscriptionLoading ? (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-8 mb-8">
            <div className="animate-pulse">Loading subscription...</div>
          </div>
        ) : subscription?.subscription ? (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-8">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Current Plan</h2>
                <p className="text-gray-600 dark:text-gray-400 mt-1">
                  {subscription.subscription?.items?.[0]?.product_name || 'Active Subscription'}
                </p>
              </div>
              <div className="flex items-center gap-2">
                {subscription.subscription?.status === 'active' ? (
                  <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium flex items-center gap-1">
                    <CheckCircle className="w-4 h-4" />
                    Active
                  </span>
                ) : (
                  <span className="px-3 py-1 bg-gray-100 text-gray-800 rounded-full text-sm font-medium">
                    {subscription.subscription?.status || 'Unknown'}
                  </span>
                )}
              </div>
            </div>

            {subscription.subscription?.trial_end && (
              <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <p className="text-sm text-blue-800 dark:text-blue-200">
                  Trial ends: {formatDate(subscription.subscription.trial_end)}
                </p>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Current Period</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">
                  {subscription.subscription?.current_period_start && subscription.subscription?.current_period_end
                    ? `${formatDate(subscription.subscription.current_period_start)} - ${formatDate(subscription.subscription.current_period_end)}`
                    : 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Amount</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">
                  {subscription.subscription?.items?.[0]?.amount 
                    ? formatCurrency(subscription.subscription.items[0].amount)
                    : 'N/A'} / {subscription.subscription?.items?.[0]?.interval || 'month'}
                </p>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleManagePayment}
                disabled={loadingAction === 'portal'}
                className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 flex items-center gap-2"
              >
                {loadingAction === 'portal' ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Settings className="w-4 h-4" />
                )}
                Manage Payment Methods
              </button>
              {subscription.subscription?.cancel_at_period_end ? (
                <span className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm">
                  Cancels on {subscription.subscription?.current_period_end ? formatDate(subscription.subscription.current_period_end) : 'N/A'}
                </span>
              ) : (
                <button
                  onClick={() => subscription.subscription?.id && handleCancelSubscription(subscription.subscription.id)}
                  disabled={loadingAction === 'cancel' || !subscription.subscription?.id}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 flex items-center gap-2"
                >
                  {loadingAction === 'cancel' ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <XCircle className="w-4 h-4" />
                  )}
                  Cancel Subscription
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-8 mb-8 text-center">
            <CreditCard className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">No Active Subscription</h2>
            <p className="text-gray-600 dark:text-gray-400 mb-6">Select a plan below to get started</p>
          </div>
        )}

        {/* Available Plans */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Available Plans</h2>
            <div className="flex gap-2 bg-gray-200 dark:bg-gray-700 rounded-lg p-1">
              <button
                onClick={() => setBillingPeriod('monthly')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  billingPeriod === 'monthly'
                    ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow'
                    : 'text-gray-600 dark:text-gray-400'
                }`}
              >
                Monthly
              </button>
              <button
                onClick={() => setBillingPeriod('yearly')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  billingPeriod === 'yearly'
                    ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow'
                    : 'text-gray-600 dark:text-gray-400'
                }`}
              >
                Yearly <span className="text-green-600">Save 10%</span>
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {Object.entries(pricingTiers).map(([key, tier]: [string, any]) => (
              <div
                key={key}
                className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border border-gray-200 dark:border-gray-700"
              >
                <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">{tier.name}</h3>
                <div className="mb-4">
                  <span className="text-3xl font-bold text-gray-900 dark:text-white">
                    ${billingPeriod === 'monthly' ? tier.monthly_price : tier.annual_price}
                  </span>
                  <span className="text-gray-600 dark:text-gray-400">/{billingPeriod === 'monthly' ? 'month' : 'year'}</span>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">{tier.description}</p>
                <button
                  onClick={() => handleSelectPlan(key)}
                  disabled={loadingAction === `select-${key}`}
                  className="w-full px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {loadingAction === `select-${key}` ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <ArrowUpRight className="w-4 h-4" />
                      Select Plan
                    </>
                  )}
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Payment Methods */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Payment Methods</h2>
            <div className="flex gap-2">
              <button
                onClick={() => handleAddPaymentMethod('card')}
                disabled={loadingAction === 'add-payment'}
                className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 flex items-center gap-2"
              >
                {loadingAction === 'add-payment' ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <CreditCard className="w-4 h-4" />
                )}
                Add Card
              </button>
              <button
                onClick={() => handleAddPaymentMethod('ach')}
                disabled={loadingAction === 'add-payment'}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
              >
                {loadingAction === 'add-payment' ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Settings className="w-4 h-4" />
                )}
                Add Bank Account
              </button>
            </div>
          </div>

          {paymentMethodsLoading ? (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-8">
              <div className="animate-pulse">Loading payment methods...</div>
            </div>
          ) : paymentMethods.length > 0 ? (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
              <div className="divide-y divide-gray-200 dark:divide-gray-700">
                {paymentMethods.map((pm: any) => (
                  <div key={pm.id} className="p-6 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center">
                        {pm.type === 'card' ? (
                          <CreditCard className="w-6 h-6 text-gray-600 dark:text-gray-300" />
                        ) : (
                          <Settings className="w-6 h-6 text-gray-600 dark:text-gray-300" />
                        )}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-semibold text-gray-900 dark:text-white">
                            {pm.type === 'card' 
                              ? `${pm.card?.brand?.toUpperCase() || 'Card'} •••• ${pm.card?.last4 || ''}`
                              : `${pm.us_bank_account?.bank_name || 'Bank'} •••• ${pm.us_bank_account?.last4 || ''}`}
                          </p>
                          {pm.id === customerDetails?.default_payment_method && (
                            <span className="px-2 py-1 bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded text-xs font-medium">
                              Default
                            </span>
                          )}
                        </div>
                        {pm.type === 'card' && pm.card && (
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            Expires {pm.card.exp_month}/{pm.card.exp_year}
                          </p>
                        )}
                        {pm.type === 'us_bank_account' && pm.us_bank_account && (
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            {pm.us_bank_account.account_type || 'Bank Account'}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      {pm.id !== customerDetails?.default_payment_method && (
                        <button
                          onClick={() => handleSetDefault(pm.id)}
                          disabled={loadingAction === `default-${pm.id}`}
                          className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50"
                        >
                          {loadingAction === `default-${pm.id}` ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            'Set Default'
                          )}
                        </button>
                      )}
                      <button
                        onClick={() => handleRemovePaymentMethod(pm.id)}
                        disabled={loadingAction === `remove-${pm.id}`}
                        className="px-3 py-1 text-sm bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 rounded hover:bg-red-200 dark:hover:bg-red-800 disabled:opacity-50"
                      >
                        {loadingAction === `remove-${pm.id}` ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          'Remove'
                        )}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-8 text-center">
              <CreditCard className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600 dark:text-gray-400 mb-4">No payment methods on file</p>
              <button
                onClick={() => handleAddPaymentMethod('card')}
                className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700"
              >
                Add Payment Method
              </button>
            </div>
          )}
        </div>

        {/* Account Information */}
        {customerDetails && (
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Account Information</h2>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Email</p>
                  <p className="font-semibold text-gray-900 dark:text-white">{customerDetails.email || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Name</p>
                  <p className="font-semibold text-gray-900 dark:text-white">{customerDetails.name || 'N/A'}</p>
                </div>
                {customerDetails.phone && (
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Phone</p>
                    <p className="font-semibold text-gray-900 dark:text-white">{customerDetails.phone}</p>
                  </div>
                )}
                {customerDetails.address && (
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Address</p>
                    <p className="font-semibold text-gray-900 dark:text-white">
                      {customerDetails.address.line1}
                      {customerDetails.address.line2 && `, ${customerDetails.address.line2}`}
                      {customerDetails.address.city && `, ${customerDetails.address.city}`}
                      {customerDetails.address.state && ` ${customerDetails.address.state}`}
                      {customerDetails.address.postal_code && ` ${customerDetails.address.postal_code}`}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Invoices */}
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Invoice History</h2>
          {invoicesLoading ? (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-8">
              <div className="animate-pulse">Loading invoices...</div>
            </div>
          ) : invoices.length > 0 ? (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Invoice</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Date</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Amount</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {invoices.map((invoice: any) => (
                    <tr key={invoice.id}>
                      <td className="px-6 py-4 text-sm text-gray-900 dark:text-white">{invoice.number || invoice.id}</td>
                      <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                        {formatDate(invoice.created)}
                      </td>
                      <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-white">
                        {formatCurrency(invoice.amount_paid || invoice.amount_due, invoice.currency)}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 text-xs rounded-full ${
                          invoice.status === 'paid'
                            ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                            : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                        }`}>
                          {invoice.status}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        {invoice.hosted_invoice_url && (
                          <a
                            href={invoice.hosted_invoice_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-orange-600 hover:text-orange-700 flex items-center gap-1"
                          >
                            <FileText className="w-4 h-4" />
                            View
                          </a>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-8 text-center">
              <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600 dark:text-gray-400">No invoices yet</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

