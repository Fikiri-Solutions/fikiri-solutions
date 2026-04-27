import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../services/apiClient'
import { AUTOCOMPLETE } from '../constants/autocomplete'
import { useAuth } from '../contexts/AuthContext'
import { hasActiveSubscription } from '../lib/subscriptionAccess'

const LIMITS = { name: 200, email: 254, phone: 50, company: 200, subject: 200, message: 3000 }

export const InternalContact: React.FC = () => {
  const { user } = useAuth()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [company, setCompany] = useState('')
  const [subject, setSubject] = useState('Consultation request')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')

  const { data: subscriptionPayload } = useQuery({
    queryKey: ['current-subscription', user?.id, 'internal-contact'],
    queryFn: async () => {
      try {
        return await apiClient.getCurrentSubscription()
      } catch {
        return { success: true, subscription: null }
      }
    },
    enabled: !!user?.id,
    staleTime: 60 * 1000,
    retry: 1,
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess(false)
    if (!name.trim() || !email.trim() || !message.trim()) {
      setError('Name, email, and message are required.')
      return
    }

    setLoading(true)
    try {
      const isPayingCustomer = hasActiveSubscription(subscriptionPayload)
      const onboardingState = user?.onboarding_completed ? 'Onboarded' : 'Signed in (onboarding incomplete/unknown)'
      const customerState = isPayingCustomer ? 'Paying customer' : 'Signed in (no active paid/trial subscription)'
      const sourceContext = `\n\n---\nContact Source: In-app support/contact form\nUser Stage: ${onboardingState}\nBilling Stage: ${customerState}`
      const subjectPrefix = isPayingCustomer ? '[Customer Paying]' : '[Customer Non-paying]'
      const trimmedSubject = subject.trim()
      const res = await apiClient.submitContact({
        name: name.trim().slice(0, LIMITS.name),
        email: email.trim().slice(0, LIMITS.email),
        phone: phone.trim() ? phone.trim().slice(0, LIMITS.phone) : undefined,
        company: company.trim() ? company.trim().slice(0, LIMITS.company) : undefined,
        subject: trimmedSubject
          ? `${subjectPrefix} ${trimmedSubject}`.slice(0, LIMITS.subject)
          : `${subjectPrefix} Support request`,
        message: `${message.trim().slice(0, LIMITS.message)}${sourceContext}`,
      })

      if (res.success) {
        setSuccess(true)
        setName('')
        setEmail('')
        setPhone('')
        setCompany('')
        setSubject('Consultation request')
        setMessage('')
      } else {
        setError(res.error || 'Something went wrong.')
      }
    } catch (err: unknown) {
      setError(apiClient.handleError(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto py-6 sm:py-8">
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm p-6 sm:p-8">
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-2">Contact support</h1>
        <p className="text-sm sm:text-base text-gray-600 dark:text-gray-400 mb-6">
          You are contacting us from inside your account. Send your request and we will follow up with next steps.
        </p>

        {success && (
          <div className="mb-6 p-4 rounded-lg bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200 border border-green-200 dark:border-green-800">
            Thank you. We will get back to you soon.
          </div>
        )}
        {error && (
          <div className="mb-6 p-4 rounded-lg bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200 border border-red-200 dark:border-red-800">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5" autoComplete="on">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label htmlFor="support-name" className="block text-sm font-medium text-gray-900 dark:text-gray-200 mb-1">
                Name <span className="text-red-500">*</span>
              </label>
              <input
                id="support-name"
                name="name"
                type="text"
                autoComplete={AUTOCOMPLETE.contact.name}
                required
                maxLength={LIMITS.name}
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                placeholder="Your name"
              />
            </div>

            <div>
              <label htmlFor="support-email" className="block text-sm font-medium text-gray-900 dark:text-gray-200 mb-1">
                Email <span className="text-red-500">*</span>
              </label>
              <input
                id="support-email"
                name="email"
                type="email"
                autoComplete={AUTOCOMPLETE.contact.email}
                required
                maxLength={LIMITS.email}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                placeholder="you@example.com"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label htmlFor="support-phone" className="block text-sm font-medium text-gray-900 dark:text-gray-200 mb-1">
                Phone
              </label>
              <input
                id="support-phone"
                name="phone"
                type="tel"
                autoComplete={AUTOCOMPLETE.contact.tel}
                maxLength={LIMITS.phone}
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                placeholder="+1 (555) 000-0000"
              />
            </div>

            <div>
              <label htmlFor="support-company" className="block text-sm font-medium text-gray-900 dark:text-gray-200 mb-1">
                Company
              </label>
              <input
                id="support-company"
                name="company"
                type="text"
                autoComplete={AUTOCOMPLETE.contact.organization}
                maxLength={LIMITS.company}
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                placeholder="Your company"
              />
            </div>
          </div>

          <div>
            <label htmlFor="support-subject" className="block text-sm font-medium text-gray-900 dark:text-gray-200 mb-1">
              Subject
            </label>
            <input
              id="support-subject"
              name="subject"
              type="text"
              autoComplete={AUTOCOMPLETE.contact.subject}
              maxLength={LIMITS.subject}
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              placeholder="How can we help?"
            />
          </div>

          <div>
            <label htmlFor="support-message" className="block text-sm font-medium text-gray-900 dark:text-gray-200 mb-1">
              Message <span className="text-red-500">*</span>
            </label>
            <textarea
              id="support-message"
              name="message"
              autoComplete={AUTOCOMPLETE.contact.message}
              required
              rows={6}
              maxLength={LIMITS.message}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-orange-500 focus:border-transparent resize-y"
              placeholder="Tell us what you want help with..."
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{message.length}/{LIMITS.message} characters</p>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full sm:w-auto min-h-[44px] px-5 py-2.5 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50"
          >
            {loading ? 'Sending…' : 'Send message'}
          </button>
        </form>
      </div>
    </div>
  )
}

