import React, { useState } from 'react'
import { RadiantLayout, Container, Gradient, AnimatedBackground } from '../components/radiant'
import { Button } from '../components/radiant/Button'
import { apiClient } from '../services/apiClient'
import { PublicChatbotWidget } from '../components/PublicChatbotWidget'

const LIMITS = { name: 200, email: 254, phone: 50, company: 200, subject: 200, message: 3000 }

export const Contact: React.FC = () => {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [company, setCompany] = useState('')
  const [subject, setSubject] = useState('')
  const [message, setMessage] = useState('')
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
      const res = await apiClient.submitContact({
        name: name.trim().slice(0, LIMITS.name),
        email: email.trim().slice(0, LIMITS.email),
        phone: phone.trim() ? phone.trim().slice(0, LIMITS.phone) : undefined,
        company: company.trim() ? company.trim().slice(0, LIMITS.company) : undefined,
        subject: subject.trim() ? subject.trim().slice(0, LIMITS.subject) : undefined,
        message: message.trim().slice(0, LIMITS.message),
      })
      if (res.success) {
        setSuccess(true)
        setName('')
        setEmail('')
        setPhone('')
        setCompany('')
        setSubject('')
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
    <RadiantLayout>
      <div className="min-h-screen bg-background text-foreground relative">
        <div className="absolute inset-0 fikiri-gradient-animated">
          <AnimatedBackground />
        </div>
        <section className="relative py-16 sm:py-20 z-10">
          <Gradient className="absolute inset-x-2 top-0 bottom-0 rounded-3xl ring-1 ring-black/5 ring-inset opacity-20" />
          <Container className="relative">
            <div className="max-w-xl mx-auto">
              <h1 className="text-4xl font-bold text-foreground mb-2 sm:text-5xl">
                Contact us
              </h1>
              <p className="text-lg text-muted-foreground mb-8">
                Questions, feedback, or a demo? We’ll get back to you soon.
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

              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label htmlFor="contact-name" className="block text-sm font-medium text-foreground mb-1">
                    Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    id="contact-name"
                    type="text"
                    required
                    maxLength={LIMITS.name}
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:ring-2 focus:ring-brand-primary focus:border-transparent"
                    placeholder="Your name"
                  />
                  <p className="mt-1 text-xs text-muted-foreground">{name.length}/{LIMITS.name}</p>
                </div>
                <div>
                  <label htmlFor="contact-email" className="block text-sm font-medium text-foreground mb-1">
                    Email <span className="text-red-500">*</span>
                  </label>
                  <input
                    id="contact-email"
                    type="email"
                    required
                    maxLength={LIMITS.email}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:ring-2 focus:ring-brand-primary focus:border-transparent"
                    placeholder="you@example.com"
                  />
                </div>
                <div>
                  <label htmlFor="contact-phone" className="block text-sm font-medium text-foreground mb-1">
                    Phone
                  </label>
                  <input
                    id="contact-phone"
                    type="tel"
                    maxLength={LIMITS.phone}
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:ring-2 focus:ring-brand-primary focus:border-transparent"
                    placeholder="+1 (555) 000-0000"
                  />
                </div>
                <div>
                  <label htmlFor="contact-company" className="block text-sm font-medium text-foreground mb-1">
                    Company
                  </label>
                  <input
                    id="contact-company"
                    type="text"
                    maxLength={LIMITS.company}
                    value={company}
                    onChange={(e) => setCompany(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:ring-2 focus:ring-brand-primary focus:border-transparent"
                    placeholder="Your company"
                  />
                </div>
                <div>
                  <label htmlFor="contact-subject" className="block text-sm font-medium text-foreground mb-1">
                    Subject
                  </label>
                  <input
                    id="contact-subject"
                    type="text"
                    maxLength={LIMITS.subject}
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:ring-2 focus:ring-brand-primary focus:border-transparent"
                    placeholder="Brief subject"
                  />
                </div>
                <div>
                  <label htmlFor="contact-message" className="block text-sm font-medium text-foreground mb-1">
                    Message <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    id="contact-message"
                    required
                    rows={6}
                    maxLength={LIMITS.message}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:ring-2 focus:ring-brand-primary focus:border-transparent resize-y"
                    placeholder="Your question or request..."
                  />
                  <p className="mt-1 text-xs text-muted-foreground">{message.length}/{LIMITS.message} characters</p>
                </div>
                <Button type="submit" disabled={loading} className="w-full sm:w-auto">
                  {loading ? 'Sending…' : 'Send message'}
                </Button>
              </form>
            </div>
          </Container>
        </section>
      </div>
      <PublicChatbotWidget />
    </RadiantLayout>
  )
}
