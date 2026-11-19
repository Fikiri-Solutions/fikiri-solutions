import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { RadiantLayout, Container, Button } from '../components/radiant'
import { apiClient } from '../services/apiClient'
import { AUTOCOMPLETE } from '../constants/autocomplete'
import { PageMeta } from '../components/PageMeta'
import { config } from '../config'
import { cn } from '../lib/utils'
import {
  BUDGET_READINESS_OPTIONS,
  INDUSTRIES,
  INTAKE_LIMITS,
  PROJECT_CLARITY_OPTIONS,
  SERVICE_OPTIONS,
  SOFTWARE_DETAIL_OPTIONS,
  TIMELINE_READINESS_OPTIONS,
  WEBSITE_DETAIL_OPTIONS,
  applyPrefillToForm,
  buildIntakeReviewLines,
  buildShortIntakePayload,
  clearIntakeCorrelationId,
  clearIntakeDraft,
  clearPrefillStorage,
  deriveLeadPriorityBand,
  getOrCreateIntakeCorrelationId,
  isValidServiceId,
  leadPriorityBandLabel,
  mergePrefills,
  primaryServiceFollowUp,
  readIntakeDraft,
  readPrefillFromSearch,
  readPrefillFromStorage,
  writeIntakeDraft,
  type BudgetReadinessId,
  type IntakeStepId,
  type PreferredNextStep,
  type ProjectClarityId,
  type ServiceInterestId,
  type ShortIntakeFormState,
  type TimelineReadinessId,
} from '../lib/consultationIntake'

const STEP_ORDER: IntakeStepId[] = [
  'services',
  'detail',
  'context',
  'contact',
  'ready',
  'next',
]

const inputCls =
  'w-full min-h-[44px] px-3 py-2 rounded-lg border border-stone-200 bg-white font-serif text-stone-900 placeholder:text-stone-400 focus:ring-2 focus:ring-brand-primary focus:border-transparent'
const labelCls = 'block text-sm font-serif font-medium text-stone-800 mb-1'

function emptyForm(): ShortIntakeFormState {
  return {
    service_interests: [],
    service_details: [],
    industry: '',
    main_pain: '',
    contact_name: '',
    email: '',
    phone: '',
    business_name: '',
    project_clarity: '',
    timeline_readiness: '',
    budget_readiness: '',
    preferred_next_step: '',
    leave_blank: '',
  }
}

export const Intake: React.FC = () => {
  const location = useLocation()
  const [step, setStep] = useState<IntakeStepId>('services')
  const [form, setForm] = useState<ShortIntakeFormState>(emptyForm)
  const [source, setSource] = useState('consultation_intake_short')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')
  const [bookingOpened, setBookingOpened] = useState(false)
  const [hydrated, setHydrated] = useState(false)
  const stepHeadingRef = useRef<HTMLHeadingElement | null>(null)

  const bookingUrl = config.consultationBookingUrl
  const followUpKind = primaryServiceFollowUp(form.service_interests)
  const bothBuildTracks =
    form.service_interests.includes('website_design_development') &&
    form.service_interests.includes('custom_software_systems')

  const visibleSteps = useMemo(() => {
    if (followUpKind) return STEP_ORDER
    return STEP_ORDER.filter((id) => id !== 'detail')
  }, [followUpKind])

  const reviewLines = useMemo(() => buildIntakeReviewLines(form), [form])

  // If service mix changes (e.g. leave website/software), don't stay on a removed step.
  useEffect(() => {
    if (!visibleSteps.includes(step)) {
      setStep(visibleSteps[Math.max(0, visibleSteps.length - 2)] || 'services')
    }
  }, [visibleSteps, step])

  const stepIndex = Math.max(0, visibleSteps.indexOf(step))
  const progress = ((stepIndex + 1) / visibleSteps.length) * 100

  // Hydrate draft + URL/chatbot prefill once (prefill wins on overlap).
  useEffect(() => {
    const draft = readIntakeDraft()
    const fromUrl = readPrefillFromSearch(location.search)
    const fromStorage = readPrefillFromStorage()
    const merged = mergePrefills(fromStorage, fromUrl)

    let nextForm = emptyForm()
    let nextStep: IntakeStepId = 'services'
    let nextSource = 'consultation_intake_short'

    if (draft?.form) {
      nextForm = { ...draft.form, leave_blank: '' }
      if (draft.step) nextStep = draft.step
      if (draft.source) nextSource = draft.source
    }

    if (Object.keys(merged).length) {
      nextForm = applyPrefillToForm(nextForm, merged)
      if (merged.source) nextSource = merged.source.slice(0, INTAKE_LIMITS.source)
      const interests = (merged.service_interests || []).filter(isValidServiceId)
      const kind = primaryServiceFollowUp(interests)
      const hasContact = Boolean(merged.contact_name && merged.email)
      const hasContext = Boolean(merged.main_pain)
      // Prefill advances completed steps but lands on contact so the client can review.
      if (interests.length && hasContext && hasContact) {
        nextStep = 'contact'
      } else if (interests.length && hasContext) {
        nextStep = 'contact'
      } else if (interests.length) {
        nextStep = kind && !merged.service_detail ? 'detail' : 'context'
      }
    }

    // Old drafts may land on review before the readiness step existed.
    if (
      nextStep === 'next' &&
      (!nextForm.project_clarity ||
        !nextForm.timeline_readiness ||
        !nextForm.budget_readiness)
    ) {
      nextStep = 'ready'
    }

    setForm(nextForm)
    setSource(nextSource)
    setStep(nextStep)
    setHydrated(true)
    // Only on mount / search change — intentional.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.search])

  // Persist in-progress answers (best practice: don't punish refresh).
  useEffect(() => {
    if (!hydrated || success) return
    writeIntakeDraft({ step, source, form })
  }, [hydrated, success, step, source, form])

  // Move keyboard focus to the step heading when the step changes.
  useEffect(() => {
    if (!hydrated || success) return
    const el = stepHeadingRef.current
    if (el && typeof el.focus === 'function') {
      el.focus()
    }
  }, [step, hydrated, success])

  const toggleService = (id: ServiceInterestId) => {
    setForm((prev) => {
      const has = prev.service_interests.includes(id)
      let nextInterests: ServiceInterestId[]
      if (has) {
        nextInterests = prev.service_interests.filter((x) => x !== id)
      } else if (id === 'not_sure_lets_talk') {
        nextInterests = ['not_sure_lets_talk']
      } else {
        nextInterests = [
          ...prev.service_interests.filter((x) => x !== 'not_sure_lets_talk'),
          id,
        ]
      }
      const nextKind = primaryServiceFollowUp(nextInterests)
      const allowed =
        nextKind === 'website'
          ? new Set(WEBSITE_DETAIL_OPTIONS.map((o) => o.id))
          : nextKind === 'software'
            ? new Set(SOFTWARE_DETAIL_OPTIONS.map((o) => o.id))
            : new Set<string>()
      return {
        ...prev,
        service_interests: nextInterests,
        service_details: prev.service_details.filter((d) => allowed.has(d)),
      }
    })
    setError('')
  }

  const toggleServiceDetail = (id: string) => {
    setForm((prev) => {
      const has = prev.service_details.includes(id)
      return {
        ...prev,
        service_details: has
          ? prev.service_details.filter((x) => x !== id)
          : [...prev.service_details, id],
      }
    })
    setError('')
  }

  const goNext = () => {
    setError('')
    if (step === 'services') {
      if (form.service_interests.length === 0) {
        setError('Pick at least one area we can help with.')
        return
      }
      setStep(followUpKind ? 'detail' : 'context')
      return
    }
    if (step === 'detail') {
      if (form.service_details.length === 0) {
        setError('Select at least one focus — you can refine details on the call.')
        return
      }
      setStep('context')
      return
    }
    if (step === 'context') {
      if (!form.main_pain.trim()) {
        setError('Tell us briefly what’s getting in the way.')
        return
      }
      setStep('contact')
      return
    }
    if (step === 'contact') {
      if (!form.contact_name.trim() || !form.email.trim()) {
        setError('Name and email are required so we can follow up.')
        return
      }
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
        setError('Please enter a valid email address.')
        return
      }
      setStep('ready')
      return
    }
    if (step === 'ready') {
      if (!form.project_clarity || !form.timeline_readiness || !form.budget_readiness) {
        setError('Pick one option in each group — helps us prioritize without slowing you down.')
        return
      }
      setStep('next')
    }
  }

  const goBack = () => {
    setError('')
    const idx = visibleSteps.indexOf(step)
    if (idx > 0) setStep(visibleSteps[idx - 1])
  }

  const submit = async (preferred: PreferredNextStep) => {
    setError('')
    setLoading(true)
    setBookingOpened(false)
    const nextForm = { ...form, preferred_next_step: preferred }
    setForm(nextForm)
    const correlationId = getOrCreateIntakeCorrelationId()
    try {
      const payload = buildShortIntakePayload(nextForm, {
        correlationId,
        source,
      })
      const res = await apiClient.submitConsultationIntake(
        payload as Parameters<typeof apiClient.submitConsultationIntake>[0]
      )
      if (!res.success) {
        if (res.error_code === 'RATE_LIMIT_EXCEEDED') {
          setError(
            res.error ||
              'Too many submissions from this network. Please wait a bit and try again.'
          )
        } else {
          setError(res.error || 'Something went wrong. Please try again.')
        }
        return
      }
      setSuccess(true)
      clearPrefillStorage()
      clearIntakeDraft()
      clearIntakeCorrelationId()

      if (preferred === 'book' && bookingUrl) {
        // Lead is persisted first; calendar is external — do not claim the slot is booked.
        window.open(bookingUrl, '_blank', 'noopener,noreferrer')
        setBookingOpened(true)
      }
    } catch (err: unknown) {
      setError(apiClient.handleError(err))
    } finally {
      setLoading(false)
    }
  }

  /** Keep answers, go back to review/edit, allow a fresh resubmit. */
  const redoEditAnswers = () => {
    setSuccess(false)
    setError('')
    setBookingOpened(false)
    setForm((f) => ({ ...f, preferred_next_step: '' }))
    setStep('next')
    clearIntakeCorrelationId()
  }

  /** Full reset for a different request. */
  const startOver = () => {
    setSuccess(false)
    setError('')
    setBookingOpened(false)
    setForm(emptyForm())
    setSource('consultation_intake_short')
    setStep('services')
    clearPrefillStorage()
    clearIntakeDraft()
    clearIntakeCorrelationId()
  }

  const detailOptions =
    followUpKind === 'website'
      ? WEBSITE_DETAIL_OPTIONS
      : followUpKind === 'software'
        ? SOFTWARE_DETAIL_OPTIONS
        : []

  const readinessBand =
    form.project_clarity && form.timeline_readiness && form.budget_readiness
      ? deriveLeadPriorityBand(
          form.project_clarity,
          form.timeline_readiness,
          form.budget_readiness
        )
      : null

  const stepTitle =
    step === 'services'
      ? 'What can we help with?'
      : step === 'detail'
        ? followUpKind === 'website'
          ? 'What kind of website work?'
          : 'What kind of software?'
        : step === 'context'
          ? 'A little context'
          : step === 'contact'
            ? 'How do we reach you?'
            : step === 'ready'
              ? 'How ready are you?'
              : 'What’s next?'

  return (
    <RadiantLayout>
      <PageMeta route="/intake" />
      <div className="relative min-h-dvh pb-[env(safe-area-inset-bottom)]">
        <section className="relative py-10 sm:py-16 z-10">
          <Container className="relative">
            <div className="max-w-xl mx-auto min-w-0">
              <h1 className="font-serif text-3xl font-bold text-white mb-2 sm:text-5xl">
                Let’s talk
              </h1>
              <p className="font-serif text-lg text-white/70 mb-2">
                About a minute — tell us what you need, and we’ll prepare for a focused conversation.
              </p>
              <p className="font-serif text-sm text-white/55 mb-8">
                Prefer a quick note instead?{' '}
                <Link to="/contact" className="text-orange-300 hover:underline">
                  Contact us
                </Link>
                .
              </p>

              {success ? (
                <div className="space-y-4 rounded-2xl bg-white/[0.95] p-6 font-serif shadow-lg shadow-orange-950/20 ring-1 ring-white/25 backdrop-blur-sm sm:p-8">
                  <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-green-900">
                    <p className="font-medium">Thanks — we received your info.</p>
                    <p className="mt-1 text-sm text-green-800/90">
                      {form.preferred_next_step === 'book' && bookingUrl
                        ? bookingOpened
                          ? 'Your details are saved. Use the calendar tab to pick a time — you’re not booked until you confirm a slot there.'
                          : 'Your details are saved. Open the calendar below to choose a time — booking isn’t confirmed until you finish there.'
                        : 'We’ll follow up by email to schedule a consultation. Nothing is booked yet.'}
                    </p>
                  </div>

                  {reviewLines.length > 0 && (
                    <div className="rounded-lg border border-stone-200 bg-stone-50 p-4 text-sm text-stone-800">
                      <p className="font-medium text-stone-900 mb-2">What we saved</p>
                      <ul className="space-y-1 list-disc pl-5">
                        {reviewLines.map((line) => (
                          <li key={line}>{line}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {form.preferred_next_step === 'book' && bookingUrl && (
                    <Button
                      type="button"
                      className="w-full sm:w-auto"
                      onClick={() =>
                        window.open(bookingUrl, '_blank', 'noopener,noreferrer')
                      }
                    >
                      Open calendar
                    </Button>
                  )}

                  <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
                    <Button type="button" variant="secondary" onClick={redoEditAnswers}>
                      Update my answers
                    </Button>
                    <Button type="button" variant="outline" onClick={startOver}>
                      Start a new intake
                    </Button>
                  </div>

                  <p className="text-sm text-stone-600">
                    Questions in the meantime?{' '}
                    <Link to="/contact" className="text-orange-700 underline">
                      Contact us
                    </Link>
                    .
                  </p>
                </div>
              ) : (
                <div className="space-y-6 rounded-2xl bg-white/[0.95] p-5 font-serif shadow-lg shadow-orange-950/20 ring-1 ring-white/25 backdrop-blur-sm sm:p-8">
                  <div>
                    <div className="mb-2 flex items-center justify-between gap-2 text-xs text-stone-500">
                      <span>
                        Step {stepIndex + 1} of {visibleSteps.length}
                      </span>
                      <span>~1 min</span>
                    </div>
                    <div
                      className="h-1.5 overflow-hidden rounded-full bg-stone-200"
                      role="progressbar"
                      aria-valuenow={stepIndex + 1}
                      aria-valuemin={1}
                      aria-valuemax={visibleSteps.length}
                      aria-label="Intake progress"
                    >
                      <div
                        className="h-full rounded-full bg-brand-primary transition-all duration-300"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                  </div>

                  {error && (
                    <div
                      className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800"
                      role="alert"
                    >
                      {error}
                    </div>
                  )}

                  <input
                    id="intake-honeypot"
                    type="text"
                    name="leave_blank"
                    value={form.leave_blank}
                    onChange={(e) => setForm((f) => ({ ...f, leave_blank: e.target.value }))}
                    tabIndex={-1}
                    autoComplete="off"
                    className="absolute opacity-0 pointer-events-none h-0 w-0 overflow-hidden"
                    aria-hidden="true"
                  />

                  <h2
                    ref={stepHeadingRef}
                    tabIndex={-1}
                    className="text-lg font-semibold text-stone-900 outline-none"
                  >
                    {stepTitle}
                  </h2>

                  {step === 'services' && (
                    <fieldset className="space-y-4">
                      <legend className="sr-only">What can we help with?</legend>
                      <p className="text-sm text-stone-600">Select all that apply.</p>
                      <div className="grid gap-3">
                        {SERVICE_OPTIONS.filter((o) => o.featured).map((opt) => {
                          const selected = form.service_interests.includes(opt.id)
                          return (
                            <button
                              key={opt.id}
                              type="button"
                              aria-pressed={selected}
                              onClick={() => toggleService(opt.id)}
                              className={cn(
                                'rounded-xl border-2 p-4 text-left transition touch-manipulation',
                                'focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary',
                                selected
                                  ? 'border-brand-primary bg-orange-50 shadow-sm'
                                  : 'border-stone-200 bg-white hover:border-orange-300'
                              )}
                            >
                              <span className="block text-base font-semibold text-stone-900">
                                {opt.label}
                              </span>
                              <span className="mt-1 block text-sm text-stone-600">
                                {opt.description}
                              </span>
                            </button>
                          )
                        })}
                      </div>
                      <div className="grid gap-2 sm:grid-cols-2">
                        {SERVICE_OPTIONS.filter((o) => !o.featured).map((opt) => {
                          const selected = form.service_interests.includes(opt.id)
                          return (
                            <button
                              key={opt.id}
                              type="button"
                              aria-pressed={selected}
                              onClick={() => toggleService(opt.id)}
                              className={cn(
                                'rounded-xl border px-3 py-3 text-left text-sm transition touch-manipulation',
                                'focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary',
                                selected
                                  ? 'border-brand-primary bg-orange-50 text-stone-900'
                                  : 'border-stone-200 bg-stone-50 text-stone-800 hover:border-orange-200'
                              )}
                            >
                              <span className="font-medium">{opt.label}</span>
                              <span className="mt-0.5 block text-xs text-stone-500">
                                {opt.description}
                              </span>
                            </button>
                          )
                        })}
                      </div>
                    </fieldset>
                  )}

                  {step === 'detail' && (
                    <fieldset className="space-y-4">
                      <legend className="sr-only">{stepTitle}</legend>
                      <p className="text-sm text-stone-600">
                        Select all that apply — no specs needed yet.
                      </p>
                      {bothBuildTracks && (
                        <p className="text-sm text-stone-600 rounded-lg bg-orange-50 border border-orange-100 px-3 py-2">
                          You also picked Custom Software — we’ll cover that on the call. This
                          question is just about the website side.
                        </p>
                      )}
                      <div className="flex flex-wrap gap-2">
                        {detailOptions.map((opt) => {
                          const selected = form.service_details.includes(opt.id)
                          return (
                            <button
                              key={opt.id}
                              type="button"
                              aria-pressed={selected}
                              onClick={() => toggleServiceDetail(opt.id)}
                              className={cn(
                                'min-h-[44px] rounded-full border px-4 py-2 text-sm font-medium transition touch-manipulation',
                                'focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary',
                                selected
                                  ? 'border-brand-primary bg-brand-primary text-white'
                                  : 'border-stone-300 bg-white text-stone-800 hover:border-orange-300'
                              )}
                            >
                              {opt.label}
                            </button>
                          )
                        })}
                      </div>
                    </fieldset>
                  )}

                  {step === 'context' && (
                    <div className="space-y-4">
                      <div>
                        <label htmlFor="intake-industry" className={labelCls}>
                          Industry <span className="text-stone-400">(optional)</span>
                        </label>
                        <select
                          id="intake-industry"
                          name="industry"
                          value={form.industry}
                          onChange={(e) =>
                            setForm((f) => ({ ...f, industry: e.target.value }))
                          }
                          className={inputCls}
                        >
                          <option value="">Select…</option>
                          {INDUSTRIES.map((opt) => (
                            <option key={opt} value={opt}>
                              {opt}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label htmlFor="intake-pain" className={labelCls}>
                          What’s getting in the way? <span className="text-red-500">*</span>
                        </label>
                        <textarea
                          id="intake-pain"
                          name="main_pain"
                          rows={3}
                          maxLength={INTAKE_LIMITS.main_pain}
                          value={form.main_pain}
                          onChange={(e) =>
                            setForm((f) => ({ ...f, main_pain: e.target.value }))
                          }
                          className={`${inputCls} resize-y`}
                          placeholder="One or two sentences is plenty"
                          required
                        />
                      </div>
                    </div>
                  )}

                  {step === 'contact' && (
                    <div className="space-y-4">
                      <div>
                        <label htmlFor="intake-contact" className={labelCls}>
                          Your name <span className="text-red-500">*</span>
                        </label>
                        <input
                          id="intake-contact"
                          name="contact_name"
                          type="text"
                          required
                          maxLength={INTAKE_LIMITS.contact_name}
                          value={form.contact_name}
                          onChange={(e) =>
                            setForm((f) => ({ ...f, contact_name: e.target.value }))
                          }
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
                          maxLength={INTAKE_LIMITS.email}
                          value={form.email}
                          onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                          className={inputCls}
                          autoComplete={AUTOCOMPLETE.contact.email}
                        />
                      </div>
                      <div>
                        <label htmlFor="intake-phone" className={labelCls}>
                          Phone <span className="text-stone-400">(optional)</span>
                        </label>
                        <input
                          id="intake-phone"
                          name="phone"
                          type="tel"
                          maxLength={INTAKE_LIMITS.phone}
                          value={form.phone}
                          onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
                          className={inputCls}
                          autoComplete={AUTOCOMPLETE.contact.tel}
                        />
                      </div>
                      <div>
                        <label htmlFor="intake-business" className={labelCls}>
                          Business name <span className="text-stone-400">(optional)</span>
                        </label>
                        <input
                          id="intake-business"
                          name="business_name"
                          type="text"
                          maxLength={INTAKE_LIMITS.business_name}
                          value={form.business_name}
                          onChange={(e) =>
                            setForm((f) => ({ ...f, business_name: e.target.value }))
                          }
                          className={inputCls}
                          placeholder="Company or DBA"
                        />
                      </div>
                    </div>
                  )}

                  {step === 'ready' && (
                    <div className="space-y-6">
                      <p className="text-sm text-stone-600">
                        Helps us prioritize people who are ready to move — no wrong answers.
                      </p>
                      <fieldset className="space-y-2">
                        <legend className={labelCls}>How clear is the project?</legend>
                        <div className="flex flex-wrap gap-2">
                          {PROJECT_CLARITY_OPTIONS.map((opt) => {
                            const selected = form.project_clarity === opt.id
                            return (
                              <button
                                key={opt.id}
                                type="button"
                                aria-pressed={selected}
                                onClick={() =>
                                  setForm((f) => ({
                                    ...f,
                                    project_clarity: opt.id as ProjectClarityId,
                                  }))
                                }
                                className={cn(
                                  'min-h-[44px] rounded-full border px-4 py-2 text-sm font-medium transition touch-manipulation',
                                  'focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary',
                                  selected
                                    ? 'border-brand-primary bg-brand-primary text-white'
                                    : 'border-stone-300 bg-white text-stone-800 hover:border-orange-300'
                                )}
                              >
                                {opt.label}
                              </button>
                            )
                          })}
                        </div>
                      </fieldset>
                      <fieldset className="space-y-2">
                        <legend className={labelCls}>When do you want to start?</legend>
                        <div className="flex flex-wrap gap-2">
                          {TIMELINE_READINESS_OPTIONS.map((opt) => {
                            const selected = form.timeline_readiness === opt.id
                            return (
                              <button
                                key={opt.id}
                                type="button"
                                aria-pressed={selected}
                                onClick={() =>
                                  setForm((f) => ({
                                    ...f,
                                    timeline_readiness: opt.id as TimelineReadinessId,
                                  }))
                                }
                                className={cn(
                                  'min-h-[44px] rounded-full border px-4 py-2 text-sm font-medium transition touch-manipulation',
                                  'focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary',
                                  selected
                                    ? 'border-brand-primary bg-brand-primary text-white'
                                    : 'border-stone-300 bg-white text-stone-800 hover:border-orange-300'
                                )}
                              >
                                {opt.label}
                              </button>
                            )
                          })}
                        </div>
                      </fieldset>
                      <fieldset className="space-y-2">
                        <legend className={labelCls}>Is there a budget set aside?</legend>
                        <div className="flex flex-wrap gap-2">
                          {BUDGET_READINESS_OPTIONS.map((opt) => {
                            const selected = form.budget_readiness === opt.id
                            return (
                              <button
                                key={opt.id}
                                type="button"
                                aria-pressed={selected}
                                onClick={() =>
                                  setForm((f) => ({
                                    ...f,
                                    budget_readiness: opt.id as BudgetReadinessId,
                                  }))
                                }
                                className={cn(
                                  'min-h-[44px] rounded-full border px-4 py-2 text-sm font-medium transition touch-manipulation',
                                  'focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary',
                                  selected
                                    ? 'border-brand-primary bg-brand-primary text-white'
                                    : 'border-stone-300 bg-white text-stone-800 hover:border-orange-300'
                                )}
                              >
                                {opt.label}
                              </button>
                            )
                          })}
                        </div>
                      </fieldset>
                    </div>
                  )}

                  {step === 'next' && (
                    <div className="space-y-4">
                      {reviewLines.length > 0 && (
                        <div className="rounded-lg border border-stone-200 bg-stone-50 p-4 text-sm text-stone-800">
                          <p className="font-medium text-stone-900 mb-2">Review</p>
                          <ul className="space-y-1 list-disc pl-5">
                            {reviewLines.map((line) => (
                              <li key={line}>{line}</li>
                            ))}
                          </ul>
                          {readinessBand && (
                            <p className="mt-3 text-xs text-stone-500">
                              Queue signal for our team: {leadPriorityBandLabel(readinessBand)}
                            </p>
                          )}
                        </div>
                      )}
                      <p className="text-sm text-stone-600">
                        We’ll save your answers first
                        {bookingUrl
                          ? ', then you can pick a time — or ask us to follow up.'
                          : '. We’ll email you to schedule a consultation.'}
                      </p>
                      <div className="grid gap-3">
                        <Button
                          type="button"
                          disabled={loading}
                          className="w-full justify-center"
                          onClick={() => void submit('book')}
                        >
                          {loading && form.preferred_next_step === 'book'
                            ? 'Saving…'
                            : bookingUrl
                              ? 'Book a consultation'
                              : 'Request a consultation'}
                        </Button>
                        <Button
                          type="button"
                          variant="secondary"
                          disabled={loading}
                          className="w-full justify-center"
                          onClick={() => void submit('follow_up')}
                        >
                          {loading && form.preferred_next_step === 'follow_up'
                            ? 'Saving…'
                            : 'Email me to follow up'}
                        </Button>
                      </div>
                      {!bookingUrl && (
                        <p className="text-xs text-stone-500">
                          Online calendar isn’t configured yet — choosing either option emails our
                          team. You’re not booked until we confirm a time together.
                        </p>
                      )}
                      <Button
                        type="button"
                        variant="outline"
                        disabled={loading}
                        onClick={goBack}
                        className="w-full sm:w-auto"
                      >
                        Back — edit answers
                      </Button>
                    </div>
                  )}

                  {step !== 'next' && (
                    <div className="flex flex-wrap items-center gap-3 pt-2">
                      {stepIndex > 0 && (
                        <Button type="button" variant="outline" onClick={goBack} disabled={loading}>
                          Back
                        </Button>
                      )}
                      <Button type="button" onClick={goNext} disabled={loading} className="ml-auto">
                        Continue
                      </Button>
                    </div>
                  )}

                  <p className="text-xs text-stone-500">
                    By continuing, you agree we may use this information to evaluate and respond.
                    See our{' '}
                    <Link to="/privacy" className="text-orange-700 underline hover:text-orange-900">
                      Privacy Policy
                    </Link>
                    . This is not a marketing signup. Your progress is saved on this device until you
                    submit.
                  </p>
                </div>
              )}
            </div>
          </Container>
        </section>
      </div>
    </RadiantLayout>
  )
}
