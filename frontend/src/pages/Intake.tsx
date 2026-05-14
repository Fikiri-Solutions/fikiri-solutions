import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { RadiantLayout, Container, Gradient, AnimatedBackground } from '../components/radiant'
import { Button } from '../components/radiant/Button'
import { apiClient } from '../services/apiClient'
import { PublicChatbotWidget } from '../components/PublicChatbotWidget'
import { AUTOCOMPLETE } from '../constants/autocomplete'

/** Mirrors backend core/contact_api INTAKE_LIMITS */
const LIMITS = {
  business_name: 200,
  contact_name: 200,
  email: 254,
  phone: 50,
  website: 300,
  location: 120,
  industry: 80,
  source: 80,
  business_size: 40,
  monthly_revenue_range: 80,
  weekly_volume: 80,
  current_tools: 1500,
  workflow_focus: 400,
  input_summary: 1500,
  decision_bottleneck: 1500,
  execution_process: 1500,
  follow_up_process: 1500,
  money_impact: 1500,
  main_pain: 1500,
  automation_opportunity: 1500,
  fixed_looks_like: 500,
} as const

const INDUSTRIES = [
  '',
  'Transportation / logistics',
  'Construction / trades',
  'Home services',
  'Real estate',
  'Healthcare / wellness',
  'Beauty',
  'Retail / ecommerce',
  'Hospitality',
  'Professional services',
  'Manufacturing',
  'Other',
]

const SOURCES = [
  '',
  'Website',
  'Referral',
  'LinkedIn',
  'Event',
  'Cold outreach',
  'Partner',
  'Inbound form',
  'Other',
]

const BUSINESS_SIZES = ['', 'Solo', '2–5', '6–15', '16–50', '51+']

const REVENUE_BANDS = [
  '',
  'Under $10K',
  '$10K–$25K',
  '$25K–$50K',
  '$50K–$100K',
  '$100K+',
  'Prefer not to say',
]

const WEEKLY_VOLUME = [
  '',
  'Fewer than 5',
  '5–15',
  '16–50',
  '51–150',
  '151+',
  'Unknown',
]

const inputCls =
  'w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:ring-2 focus:ring-brand-primary focus:border-transparent'
const labelCls = 'block text-sm font-medium text-foreground mb-1'

export const Intake: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')
  const [honeypot, setHoneypot] = useState('')

  const [business_name, setBusinessName] = useState('')
  const [contact_name, setContactName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [website, setWebsite] = useState('')
  const [location, setLocation] = useState('')
  const [industry, setIndustry] = useState('')
  const [source, setSource] = useState('')
  const [business_size, setBusinessSize] = useState('')
  const [monthly_revenue_range, setMonthlyRevenueRange] = useState('')
  const [weekly_volume, setWeeklyVolume] = useState('')
  const [current_tools, setCurrentTools] = useState('')
  const [workflow_focus, setWorkflowFocus] = useState('')
  const [input_summary, setInputSummary] = useState('')
  const [decision_bottleneck, setDecisionBottleneck] = useState('')
  const [execution_process, setExecutionProcess] = useState('')
  const [follow_up_process, setFollowUpProcess] = useState('')
  const [money_impact, setMoneyImpact] = useState('')
  const [main_pain, setMainPain] = useState('')
  const [automation_opportunity, setAutomationOpportunity] = useState('')
  const [fixed_looks_like, setFixedLooksLike] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess(false)
    if (!business_name.trim() || !contact_name.trim() || !email.trim()) {
      setError('Business name, contact name, and email are required.')
      return
    }
    setLoading(true)
    try {
      const res = await apiClient.submitConsultationIntake({
        leave_blank: honeypot,
        business_name: business_name.trim().slice(0, LIMITS.business_name),
        contact_name: contact_name.trim().slice(0, LIMITS.contact_name),
        email: email.trim().slice(0, LIMITS.email),
        phone: phone.trim() ? phone.trim().slice(0, LIMITS.phone) : undefined,
        website: website.trim() ? website.trim().slice(0, LIMITS.website) : undefined,
        location: location.trim() ? location.trim().slice(0, LIMITS.location) : undefined,
        industry: industry || undefined,
        source: source || undefined,
        business_size: business_size || undefined,
        monthly_revenue_range: monthly_revenue_range || undefined,
        weekly_volume: weekly_volume || undefined,
        current_tools: current_tools.trim()
          ? current_tools.trim().slice(0, LIMITS.current_tools)
          : undefined,
        workflow_focus: workflow_focus.trim()
          ? workflow_focus.trim().slice(0, LIMITS.workflow_focus)
          : undefined,
        input_summary: input_summary.trim()
          ? input_summary.trim().slice(0, LIMITS.input_summary)
          : undefined,
        decision_bottleneck: decision_bottleneck.trim()
          ? decision_bottleneck.trim().slice(0, LIMITS.decision_bottleneck)
          : undefined,
        execution_process: execution_process.trim()
          ? execution_process.trim().slice(0, LIMITS.execution_process)
          : undefined,
        follow_up_process: follow_up_process.trim()
          ? follow_up_process.trim().slice(0, LIMITS.follow_up_process)
          : undefined,
        money_impact: money_impact.trim()
          ? money_impact.trim().slice(0, LIMITS.money_impact)
          : undefined,
        main_pain: main_pain.trim() ? main_pain.trim().slice(0, LIMITS.main_pain) : undefined,
        automation_opportunity: automation_opportunity.trim()
          ? automation_opportunity.trim().slice(0, LIMITS.automation_opportunity)
          : undefined,
        fixed_looks_like: fixed_looks_like.trim()
          ? fixed_looks_like.trim().slice(0, LIMITS.fixed_looks_like)
          : undefined,
      })
      if (res.success) {
        setSuccess(true)
        setBusinessName('')
        setContactName('')
        setEmail('')
        setPhone('')
        setWebsite('')
        setLocation('')
        setIndustry('')
        setSource('')
        setBusinessSize('')
        setMonthlyRevenueRange('')
        setWeeklyVolume('')
        setCurrentTools('')
        setWorkflowFocus('')
        setInputSummary('')
        setDecisionBottleneck('')
        setExecutionProcess('')
        setFollowUpProcess('')
        setMoneyImpact('')
        setMainPain('')
        setAutomationOpportunity('')
        setFixedLooksLike('')
        setHoneypot('')
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
            <div className="max-w-2xl mx-auto">
              <h1 className="text-4xl font-bold text-foreground mb-2 sm:text-5xl">
                Consultation intake
              </h1>
              <p className="text-lg text-muted-foreground mb-2">
                Share context before we talk—about 10–15 minutes. We&apos;ll still walk through your real workflow
                live on the call; this just saves setup time.
              </p>
              <p className="text-sm text-muted-foreground mb-8">
                Prefer email only?{' '}
                <Link to="/contact" className="text-brand-primary hover:underline">
                  Contact us here
                </Link>
                .
              </p>

              {success && (
                <div className="mb-6 p-4 rounded-lg bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200 border border-green-200 dark:border-green-800">
                  Thank you. We received your intake and will use it to prepare for your conversation.
                </div>
              )}
              {error && (
                <div className="mb-6 p-4 rounded-lg bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200 border border-red-200 dark:border-red-800">
                  {error}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-8" autoComplete="on">
                <input
                  id="intake-honeypot"
                  type="text"
                  name="leave_blank"
                  value={honeypot}
                  onChange={(e) => setHoneypot(e.target.value)}
                  tabIndex={-1}
                  autoComplete="off"
                  className="absolute opacity-0 pointer-events-none h-0 w-0 overflow-hidden"
                  aria-hidden="true"
                />

                <section className="space-y-4">
                  <h2 className="text-lg font-semibold text-foreground border-b border-border pb-2">
                    Business & contact
                  </h2>
                  <div>
                    <label htmlFor="intake-business" className={labelCls}>
                      Business name <span className="text-red-500">*</span>
                    </label>
                    <input
                      id="intake-business"
                      name="business_name"
                      type="text"
                      required
                      maxLength={LIMITS.business_name}
                      value={business_name}
                      onChange={(e) => setBusinessName(e.target.value)}
                      className={inputCls}
                      placeholder="Company or DBA"
                    />
                  </div>
                  <div>
                    <label htmlFor="intake-contact" className={labelCls}>
                      Your name (primary contact) <span className="text-red-500">*</span>
                    </label>
                    <input
                      id="intake-contact"
                      name="contact_name"
                      type="text"
                      required
                      maxLength={LIMITS.contact_name}
                      value={contact_name}
                      onChange={(e) => setContactName(e.target.value)}
                      className={inputCls}
                      autoComplete={AUTOCOMPLETE.contact.name}
                    />
                  </div>
                  <div>
                    <label htmlFor="intake-email" className={labelCls}>
                      Email <span className="text-red-500">*</span>
                    </label>
                    <input
                      id="intake-email"
                      name="email"
                      type="email"
                      required
                      maxLength={LIMITS.email}
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className={inputCls}
                      autoComplete={AUTOCOMPLETE.contact.email}
                    />
                  </div>
                  <div>
                    <label htmlFor="intake-phone" className={labelCls}>
                      Phone
                    </label>
                    <input
                      id="intake-phone"
                      name="phone"
                      type="tel"
                      maxLength={LIMITS.phone}
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      className={inputCls}
                      autoComplete={AUTOCOMPLETE.contact.tel}
                    />
                  </div>
                  <div>
                    <label htmlFor="intake-website" className={labelCls}>
                      Website
                    </label>
                    <input
                      id="intake-website"
                      name="website"
                      type="url"
                      maxLength={LIMITS.website}
                      value={website}
                      onChange={(e) => setWebsite(e.target.value)}
                      className={inputCls}
                      placeholder="https://"
                    />
                  </div>
                  <div>
                    <label htmlFor="intake-location" className={labelCls}>
                      Location
                    </label>
                    <input
                      id="intake-location"
                      name="location"
                      type="text"
                      maxLength={LIMITS.location}
                      value={location}
                      onChange={(e) => setLocation(e.target.value)}
                      className={inputCls}
                      placeholder="City, ST"
                    />
                  </div>
                  <div>
                    <label htmlFor="intake-industry" className={labelCls}>
                      Industry
                    </label>
                    <select
                      id="intake-industry"
                      name="industry"
                      value={industry}
                      onChange={(e) => setIndustry(e.target.value)}
                      className={inputCls}
                    >
                      {INDUSTRIES.map((opt) => (
                        <option key={opt || 'empty'} value={opt}>
                          {opt || 'Select…'}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="intake-source" className={labelCls}>
                      How did you hear about Fikiri?
                    </label>
                    <select
                      id="intake-source"
                      name="source"
                      value={source}
                      onChange={(e) => setSource(e.target.value)}
                      className={inputCls}
                    >
                      {SOURCES.map((opt) => (
                        <option key={opt || 'empty-src'} value={opt}>
                          {opt || 'Select…'}
                        </option>
                      ))}
                    </select>
                  </div>
                </section>

                <section className="space-y-4">
                  <h2 className="text-lg font-semibold text-foreground border-b border-border pb-2">
                    Business profile
                  </h2>
                  <div>
                    <label htmlFor="intake-size" className={labelCls}>
                      Business size
                    </label>
                    <select
                      id="intake-size"
                      name="business_size"
                      value={business_size}
                      onChange={(e) => setBusinessSize(e.target.value)}
                      className={inputCls}
                    >
                      {BUSINESS_SIZES.map((opt) => (
                        <option key={opt || 'empty-bs'} value={opt}>
                          {opt || 'Select…'}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="intake-revenue" className={labelCls}>
                      Monthly revenue (approximate band)
                    </label>
                    <select
                      id="intake-revenue"
                      name="monthly_revenue_range"
                      value={monthly_revenue_range}
                      onChange={(e) => setMonthlyRevenueRange(e.target.value)}
                      className={inputCls}
                    >
                      {REVENUE_BANDS.map((opt) => (
                        <option key={opt || 'empty-rev'} value={opt}>
                          {opt || 'Select…'}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="intake-volume" className={labelCls}>
                      Weekly lead / job volume (throughput)
                    </label>
                    <select
                      id="intake-volume"
                      name="weekly_volume"
                      value={weekly_volume}
                      onChange={(e) => setWeeklyVolume(e.target.value)}
                      className={inputCls}
                    >
                      {WEEKLY_VOLUME.map((opt) => (
                        <option key={opt || 'empty-vol'} value={opt}>
                          {opt || 'Select…'}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="intake-tools" className={labelCls}>
                      Current tools (CRM, spreadsheets, industry software, etc.)
                    </label>
                    <textarea
                      id="intake-tools"
                      name="current_tools"
                      rows={3}
                      maxLength={LIMITS.current_tools}
                      value={current_tools}
                      onChange={(e) => setCurrentTools(e.target.value)}
                      className={`${inputCls} resize-y`}
                    />
                    <p className="mt-1 text-xs text-muted-foreground">
                      {current_tools.length}/{LIMITS.current_tools}
                    </p>
                  </div>
                </section>

                <section className="space-y-4">
                  <h2 className="text-lg font-semibold text-foreground border-b border-border pb-2">
                    Workflow focus (Input → Decision → Execution → Follow-Up → Money)
                  </h2>
                  <div>
                    <label htmlFor="intake-workflow" className={labelCls}>
                      One workflow to map on our call (one sentence)
                    </label>
                    <textarea
                      id="intake-workflow"
                      name="workflow_focus"
                      rows={2}
                      maxLength={LIMITS.workflow_focus}
                      value={workflow_focus}
                      onChange={(e) => setWorkflowFocus(e.target.value)}
                      className={`${inputCls} resize-y`}
                      placeholder="e.g. new inquiry to first paid job"
                    />
                  </div>
                  <div>
                    <label htmlFor="intake-input" className={labelCls}>
                      Where does work enter? (channels, volume)
                    </label>
                    <textarea
                      id="intake-input"
                      name="input_summary"
                      rows={3}
                      maxLength={LIMITS.input_summary}
                      value={input_summary}
                      onChange={(e) => setInputSummary(e.target.value)}
                      className={`${inputCls} resize-y`}
                    />
                  </div>
                  <div>
                    <label htmlFor="intake-decision" className={labelCls}>
                      Decision bottleneck (who decides, delays, unclear rules)
                    </label>
                    <textarea
                      id="intake-decision"
                      name="decision_bottleneck"
                      rows={3}
                      maxLength={LIMITS.decision_bottleneck}
                      value={decision_bottleneck}
                      onChange={(e) => setDecisionBottleneck(e.target.value)}
                      className={`${inputCls} resize-y`}
                    />
                  </div>
                  <div>
                    <label htmlFor="intake-exec" className={labelCls}>
                      Execution — who does the work after “yes”?
                    </label>
                    <textarea
                      id="intake-exec"
                      name="execution_process"
                      rows={3}
                      maxLength={LIMITS.execution_process}
                      value={execution_process}
                      onChange={(e) => setExecutionProcess(e.target.value)}
                      className={`${inputCls} resize-y`}
                    />
                  </div>
                  <div>
                    <label htmlFor="intake-fu" className={labelCls}>
                      Follow-up / confirmations / reviews
                    </label>
                    <textarea
                      id="intake-fu"
                      name="follow_up_process"
                      rows={3}
                      maxLength={LIMITS.follow_up_process}
                      value={follow_up_process}
                      onChange={(e) => setFollowUpProcess(e.target.value)}
                      className={`${inputCls} resize-y`}
                    />
                  </div>
                  <div>
                    <label htmlFor="intake-money" className={labelCls}>
                      Money — invoicing, leakage, cash timing
                    </label>
                    <textarea
                      id="intake-money"
                      name="money_impact"
                      rows={3}
                      maxLength={LIMITS.money_impact}
                      value={money_impact}
                      onChange={(e) => setMoneyImpact(e.target.value)}
                      className={`${inputCls} resize-y`}
                    />
                  </div>
                  <div>
                    <label htmlFor="intake-pain" className={labelCls}>
                      Main pain point
                    </label>
                    <textarea
                      id="intake-pain"
                      name="main_pain"
                      rows={3}
                      maxLength={LIMITS.main_pain}
                      value={main_pain}
                      onChange={(e) => setMainPain(e.target.value)}
                      className={`${inputCls} resize-y`}
                    />
                  </div>
                  <div>
                    <label htmlFor="intake-auto" className={labelCls}>
                      What would you automate first if you could?
                    </label>
                    <textarea
                      id="intake-auto"
                      name="automation_opportunity"
                      rows={3}
                      maxLength={LIMITS.automation_opportunity}
                      value={automation_opportunity}
                      onChange={(e) => setAutomationOpportunity(e.target.value)}
                      className={`${inputCls} resize-y`}
                    />
                  </div>
                  <div>
                    <label htmlFor="intake-fixed" className={labelCls}>
                      What does “fixed” look like in one sentence?
                    </label>
                    <textarea
                      id="intake-fixed"
                      name="fixed_looks_like"
                      rows={2}
                      maxLength={LIMITS.fixed_looks_like}
                      value={fixed_looks_like}
                      onChange={(e) => setFixedLooksLike(e.target.value)}
                      className={`${inputCls} resize-y`}
                    />
                  </div>
                </section>

                <Button type="submit" disabled={loading} className="w-full sm:w-auto">
                  {loading ? 'Submitting…' : 'Submit intake'}
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
