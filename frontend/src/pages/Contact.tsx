import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { RadiantLayout, Container } from '../components/radiant'
import { Button } from '../components/radiant/Button'
import { apiClient } from '../services/apiClient'
import { MarketingChatWidget } from '../components/MarketingChatWidget'
import { AUTOCOMPLETE } from '../constants/autocomplete'

const LIMITS = { name: 200, email: 254, phone: 50, company: 200, subject: 200, message: 3000 }

export const Contact: React.FC = () => {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [company, setCompany] = useState('')
  const [subject, setSubject] = useState('')
  const [message, setMessage] = useState('')
  const [leaveBlank, setLeaveBlank] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')

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
      const sourceContext = '\n\n---\nContact Source: Public website contact form\nUser Stage: Prospect (not signed in)'
      const res = await apiClient.submitContact({
        name: name.trim().slice(0, LIMITS.name),
        email: email.trim().slice(0, LIMITS.email),
        phone: phone.trim() ? phone.trim().slice(0, LIMITS.phone) : undefined,
        company: company.trim() ? company.trim().slice(0, LIMITS.company) : undefined,
        subject: subject.trim()
          ? `[Prospect] ${subject.trim()}`.slice(0, LIMITS.subject)
          : '[Prospect] General inquiry',
        message: `${message.trim().slice(0, LIMITS.message)}${sourceContext}`,
        leave_blank: leaveBlank,
      })
      if (res.success) {
        setSuccess(true)
        setName('')
        setEmail('')
        setPhone('')
        setCompany('')
        setSubject('')
        setMessage('')
        setLeaveBlank('')
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
    <RadiantLayout>
      <div className="relative min-h-dvh pb-[env(safe-area-inset-bottom)]">
        <section className="relative py-10 sm:py-16 z-10">
          <Container className="relative">
            <div className="max-w-xl mx-auto min-w-0">
              <h1 className="font-serif text-3xl font-bold text-white mb-2 sm:text-5xl">
                Contact us
              </h1>
              <p className="font-serif text-lg text-white/70 mb-2">
                Questions, feedback, or a demo? We’ll get back to you soon.
              </p>
              <p className="font-serif text-sm text-white/55 mb-8">
                Booking a consultation? Complete the{' '}
                <Link to="/intake" className="text-orange-300 font-medium hover:underline">
                  consultation intake
                </Link>{' '}
                first (about 10–15 minutes) so we can focus the session on your workflow.
              </p>

              {success && (
                <div className="mb-6 p-4 rounded-lg bg-green-100 text-green-800 border border-green-200">
                  Thank you. We will get back to you soon.
                </div>
              )}
              {error && (
                <div className="mb-6 p-4 rounded-lg bg-red-100 text-red-800 border border-red-200">
                  {error}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-5 rounded-2xl bg-white/[0.95] p-6 font-serif shadow-lg shadow-orange-950/20 ring-1 ring-white/25 backdrop-blur-sm sm:p-8" autoComplete="on">
                <div className="hidden" aria-hidden="true">
                  <label htmlFor="contact-leave-blank">Leave this field blank</label>
                  <input
                    id="contact-leave-blank"
                    name="leave_blank"
                    type="text"
                    tabIndex={-1}
                    autoComplete="off"
                    value={leaveBlank}
                    onChange={(e) => setLeaveBlank(e.target.value)}
                  />
                </div>
                <div>
                  <label htmlFor="contact-name" className="mb-1 block font-serif text-sm font-medium text-stone-800">
                    Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    id="contact-name"
                    name="name"
                    type="text"
                    autoComplete={AUTOCOMPLETE.contact.name}
                    required
                    maxLength={LIMITS.name}
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full min-h-[44px] rounded-lg border border-stone-200 bg-white px-3 py-2.5 font-serif text-stone-900 placeholder:text-stone-400 focus:border-transparent focus:ring-2 focus:ring-brand-primary touch-manipulation"
                    placeholder="Your name"
                  />
                  <p className="mt-1 text-xs text-stone-500">{name.length}/{LIMITS.name}</p>
                </div>
                <div>
                  <label htmlFor="contact-email" className="mb-1 block font-serif text-sm font-medium text-stone-800">
                    Email <span className="text-red-500">*</span>
                  </label>
                  <input
                    id="contact-email"
                    name="email"
                    type="email"
                    autoComplete={AUTOCOMPLETE.contact.email}
                    required
                    maxLength={LIMITS.email}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full min-h-[44px] rounded-lg border border-stone-200 bg-white px-3 py-2.5 font-serif text-stone-900 placeholder:text-stone-400 focus:border-transparent focus:ring-2 focus:ring-brand-primary touch-manipulation"
                    placeholder="you@example.com"
                  />
                </div>
                <div>
                  <label htmlFor="contact-phone" className="mb-1 block font-serif text-sm font-medium text-stone-800">
                    Phone
                  </label>
                  <input
                    id="contact-phone"
                    name="phone"
                    type="tel"
                    autoComplete={AUTOCOMPLETE.contact.tel}
                    maxLength={LIMITS.phone}
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full min-h-[44px] rounded-lg border border-stone-200 bg-white px-3 py-2.5 font-serif text-stone-900 placeholder:text-stone-400 focus:border-transparent focus:ring-2 focus:ring-brand-primary touch-manipulation"
                    placeholder="+1 (555) 000-0000"
                  />
                </div>
                <div>
                  <label htmlFor="contact-company" className="mb-1 block font-serif text-sm font-medium text-stone-800">
                    Company
                  </label>
                  <input
                    id="contact-company"
                    name="company"
                    type="text"
                    autoComplete={AUTOCOMPLETE.contact.organization}
                    maxLength={LIMITS.company}
                    value={company}
                    onChange={(e) => setCompany(e.target.value)}
                    className="w-full min-h-[44px] rounded-lg border border-stone-200 bg-white px-3 py-2.5 font-serif text-stone-900 placeholder:text-stone-400 focus:border-transparent focus:ring-2 focus:ring-brand-primary touch-manipulation"
                    placeholder="Your company"
                  />
                </div>
                <div>
                  <label htmlFor="contact-subject" className="mb-1 block font-serif text-sm font-medium text-stone-800">
                    Subject
                  </label>
                  <input
                    id="contact-subject"
                    name="subject"
                    type="text"
                    autoComplete={AUTOCOMPLETE.contact.subject}
                    maxLength={LIMITS.subject}
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    className="w-full min-h-[44px] rounded-lg border border-stone-200 bg-white px-3 py-2.5 font-serif text-stone-900 placeholder:text-stone-400 focus:border-transparent focus:ring-2 focus:ring-brand-primary touch-manipulation"
                    placeholder="Brief subject"
                  />
                </div>
                <div>
                  <label htmlFor="contact-message" className="mb-1 block font-serif text-sm font-medium text-stone-800">
                    Message <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    id="contact-message"
                    name="message"
                    autoComplete={AUTOCOMPLETE.contact.message}
                    required
                    rows={6}
                    maxLength={LIMITS.message}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    className="w-full resize-y rounded-lg border border-stone-200 bg-white px-3 py-2 font-serif text-stone-900 placeholder:text-stone-400 focus:border-transparent focus:ring-2 focus:ring-brand-primary"
                    placeholder="Your question or request..."
                  />
                  <p className="mt-1 font-serif text-xs text-stone-500">{message.length}/{LIMITS.message} characters</p>
                </div>
                <Button type="submit" disabled={loading} className="w-full sm:w-auto">
                  {loading ? 'Sending…' : 'Send message'}
                </Button>
              </form>
            </div>
          </Container>
        </section>
      </div>
      <MarketingChatWidget />
    </RadiantLayout>
  )
}
