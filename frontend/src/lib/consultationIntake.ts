/**
 * Public consultation intake — short conversational flow helpers.
 * Maps to POST /api/intake (core/consultation_intake_service.py).
 */

export const INTAKE_LIMITS = {
  business_name: 200,
  contact_name: 200,
  email: 254,
  phone: 50,
  industry: 80,
  source: 80,
  main_pain: 1500,
  workflow_focus: 400,
  service_interests: 500,
  service_detail: 200,
  preferred_next_step: 40,
  project_clarity: 40,
  timeline_readiness: 40,
  budget_readiness: 40,
  lead_priority_band: 20,
} as const

export const INTAKE_PREFILL_STORAGE_KEY = 'fikiri_intake_prefill'
export const INTAKE_CORRELATION_STORAGE_KEY = 'fikiri_intake_correlation_id'
/** In-progress answers survive refresh / accidental navigation. */
export const INTAKE_DRAFT_STORAGE_KEY = 'fikiri_intake_draft_v2'

export type IntakeStepId =
  | 'services'
  | 'detail'
  | 'context'
  | 'contact'
  | 'ready'
  | 'next'

/** Featured first — website & custom software are primary offerings. */
export const SERVICE_OPTIONS = [
  {
    id: 'website_design_development',
    label: 'Website Design & Development',
    description: 'New sites, redesigns, ecommerce, and integrations',
    featured: true,
  },
  {
    id: 'custom_software_systems',
    label: 'Custom Software & Systems',
    description: 'CRM, dashboards, portals, and internal tools',
    featured: true,
  },
  {
    id: 'ai_business_automation',
    label: 'AI & Business Automation',
    description: 'Cut repetitive work across email and ops',
    featured: false,
  },
  {
    id: 'leads_customer_management',
    label: 'Leads & Customer Management',
    description: 'Capture, follow up, and stay organized',
    featured: false,
  },
  {
    id: 'scheduling_operations',
    label: 'Scheduling & Operations',
    description: 'Bookings, dispatch, and day-to-day flow',
    featured: false,
  },
  {
    id: 'not_sure_lets_talk',
    label: "Not Sure? Let's Talk",
    description: "We'll help you figure out the right starting point",
    featured: false,
  },
] as const

export type ServiceInterestId = (typeof SERVICE_OPTIONS)[number]['id']

export const WEBSITE_DETAIL_OPTIONS = [
  { id: 'new_website', label: 'New website' },
  { id: 'redesign', label: 'Redesign' },
  { id: 'ecommerce', label: 'Ecommerce' },
  { id: 'functionality_integrations', label: 'Functionality / integrations' },
] as const

export const SOFTWARE_DETAIL_OPTIONS = [
  { id: 'crm_systems', label: 'CRM systems' },
  { id: 'dashboards', label: 'Dashboards' },
  { id: 'client_portals', label: 'Client portals' },
  { id: 'internal_applications', label: 'Internal applications' },
  { id: 'custom_operational_tools', label: 'Custom operational tools' },
] as const

/** Soft vetting — prioritize ready-to-engage leads without hard-selling. */
export const PROJECT_CLARITY_OPTIONS = [
  { id: 'exploring', label: 'Still exploring' },
  { id: 'strong_idea', label: 'Strong idea of what I need' },
  { id: 'know_exactly', label: 'I know exactly what I want' },
] as const

export const TIMELINE_READINESS_OPTIONS = [
  { id: 'researching', label: 'Just researching' },
  { id: 'within_1_3_months', label: 'In the next 1–3 months' },
  { id: 'ready_now', label: 'Ready to start soon' },
] as const

export const BUDGET_READINESS_OPTIONS = [
  { id: 'not_sure', label: 'Not sure yet' },
  { id: 'researching', label: 'Researching costs' },
  { id: 'budget_ready', label: 'Budget is ready' },
] as const

export type ProjectClarityId = (typeof PROJECT_CLARITY_OPTIONS)[number]['id']
export type TimelineReadinessId = (typeof TIMELINE_READINESS_OPTIONS)[number]['id']
export type BudgetReadinessId = (typeof BUDGET_READINESS_OPTIONS)[number]['id']
export type LeadPriorityBand = 'priority' | 'warm' | 'nurture'

export const INDUSTRIES = [
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
] as const

export type PreferredNextStep = 'book' | 'follow_up'

export interface IntakePrefill {
  industry?: string
  main_pain?: string
  contact_name?: string
  email?: string
  business_name?: string
  phone?: string
  source?: string
  service_interests?: string[]
  service_detail?: string
}

export interface ShortIntakeFormState {
  service_interests: ServiceInterestId[]
  /** Multi-select focus chips (website / software); serialized as comma-ids. */
  service_details: string[]
  industry: string
  main_pain: string
  contact_name: string
  email: string
  phone: string
  business_name: string
  project_clarity: ProjectClarityId | ''
  timeline_readiness: TimelineReadinessId | ''
  budget_readiness: BudgetReadinessId | ''
  preferred_next_step: PreferredNextStep | ''
  leave_blank: string
}

export interface IntakeDraft {
  step: IntakeStepId
  source?: string
  form: ShortIntakeFormState
}

export function serviceLabel(id: string): string {
  return SERVICE_OPTIONS.find((opt) => opt.id === id)?.label ?? id
}

export function serviceDetailLabel(id: string): string {
  const fromWebsite = WEBSITE_DETAIL_OPTIONS.find((opt) => opt.id === id)
  if (fromWebsite) return fromWebsite.label
  const fromSoftware = SOFTWARE_DETAIL_OPTIONS.find((opt) => opt.id === id)
  if (fromSoftware) return fromSoftware.label
  return id
}

export function projectClarityLabel(id: string): string {
  return PROJECT_CLARITY_OPTIONS.find((o) => o.id === id)?.label ?? id
}

export function timelineReadinessLabel(id: string): string {
  return TIMELINE_READINESS_OPTIONS.find((o) => o.id === id)?.label ?? id
}

export function budgetReadinessLabel(id: string): string {
  return BUDGET_READINESS_OPTIONS.find((o) => o.id === id)?.label ?? id
}

export function leadPriorityBandLabel(band: LeadPriorityBand): string {
  if (band === 'priority') return 'Ready to engage (priority)'
  if (band === 'warm') return 'Warm — nurture with intent'
  return 'Exploring — nurture'
}

/** Queue band for ops: priority = clear + ready + budget. */
export function deriveLeadPriorityBand(
  clarity: string,
  timeline: string,
  budget: string
): LeadPriorityBand {
  const clear = clarity === 'strong_idea' || clarity === 'know_exactly'
  const ready = timeline === 'ready_now'
  const funded = budget === 'budget_ready'
  if (clear && ready && funded) return 'priority'
  if ((ready || funded) && clarity !== 'exploring') return 'warm'
  if (ready || funded || clear) return 'warm'
  return 'nurture'
}

function normalizeDetailIds(raw: unknown): string[] {
  const allowed = new Set([
    ...WEBSITE_DETAIL_OPTIONS.map((o) => o.id),
    ...SOFTWARE_DETAIL_OPTIONS.map((o) => o.id),
  ])
  const items: string[] = []
  const push = (token: string) => {
    const id = token.trim()
    if (id && allowed.has(id as never) && !items.includes(id)) items.push(id)
  }
  if (Array.isArray(raw)) {
    for (const item of raw) push(String(item || ''))
  } else if (typeof raw === 'string' && raw.trim()) {
    for (const part of raw.split(',')) push(part)
  }
  return items
}

/** Compact review lines for the final step / success receipt. */
export function buildIntakeReviewLines(state: ShortIntakeFormState): string[] {
  const lines: string[] = []
  if (state.service_interests.length) {
    lines.push(`Help with: ${state.service_interests.map(serviceLabel).join(', ')}`)
  }
  if (state.service_details.length) {
    lines.push(`Focus: ${state.service_details.map(serviceDetailLabel).join(', ')}`)
  }
  if (state.industry) lines.push(`Industry: ${state.industry}`)
  if (state.main_pain.trim()) lines.push(`Challenge: ${state.main_pain.trim()}`)
  if (state.contact_name.trim()) lines.push(`Name: ${state.contact_name.trim()}`)
  if (state.email.trim()) lines.push(`Email: ${state.email.trim()}`)
  if (state.phone.trim()) lines.push(`Phone: ${state.phone.trim()}`)
  if (state.business_name.trim()) lines.push(`Business: ${state.business_name.trim()}`)
  if (state.project_clarity) {
    lines.push(`Clarity: ${projectClarityLabel(state.project_clarity)}`)
  }
  if (state.timeline_readiness) {
    lines.push(`Timeline: ${timelineReadinessLabel(state.timeline_readiness)}`)
  }
  if (state.budget_readiness) {
    lines.push(`Budget: ${budgetReadinessLabel(state.budget_readiness)}`)
  }
  return lines
}

export function readIntakeDraft(): IntakeDraft | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = sessionStorage.getItem(INTAKE_DRAFT_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as IntakeDraft
    if (!parsed || typeof parsed !== 'object' || !parsed.form) return null
    const interests = (parsed.form.service_interests || []).filter(isValidServiceId)
    const legacyDetail =
      typeof (parsed.form as { service_detail?: string }).service_detail === 'string'
        ? (parsed.form as { service_detail?: string }).service_detail
        : ''
    const details = normalizeDetailIds(
      parsed.form.service_details?.length ? parsed.form.service_details : legacyDetail
    )
    return {
      step: parsed.step || 'services',
      source: parsed.source,
      form: {
        ...parsed.form,
        service_interests: interests,
        service_details: details,
        project_clarity: parsed.form.project_clarity || '',
        timeline_readiness: parsed.form.timeline_readiness || '',
        budget_readiness: parsed.form.budget_readiness || '',
        leave_blank: '',
      },
    }
  } catch {
    return null
  }
}

export function writeIntakeDraft(draft: IntakeDraft): void {
  if (typeof window === 'undefined') return
  try {
    const safe: IntakeDraft = {
      step: draft.step,
      source: draft.source,
      form: { ...draft.form, leave_blank: '' },
    }
    sessionStorage.setItem(INTAKE_DRAFT_STORAGE_KEY, JSON.stringify(safe))
  } catch {
    /* ignore */
  }
}

export function clearIntakeDraft(): void {
  if (typeof window === 'undefined') return
  try {
    sessionStorage.removeItem(INTAKE_DRAFT_STORAGE_KEY)
  } catch {
    /* ignore */
  }
}

export function applyPrefillToForm(
  base: ShortIntakeFormState,
  prefill: IntakePrefill
): ShortIntakeFormState {
  const next = { ...base }
  if (prefill.industry) next.industry = prefill.industry.slice(0, INTAKE_LIMITS.industry)
  if (prefill.main_pain) next.main_pain = prefill.main_pain.slice(0, INTAKE_LIMITS.main_pain)
  if (prefill.contact_name)
    next.contact_name = prefill.contact_name.slice(0, INTAKE_LIMITS.contact_name)
  if (prefill.email) next.email = prefill.email.slice(0, INTAKE_LIMITS.email)
  if (prefill.business_name)
    next.business_name = prefill.business_name.slice(0, INTAKE_LIMITS.business_name)
  if (prefill.phone) next.phone = prefill.phone.slice(0, INTAKE_LIMITS.phone)
  if (prefill.service_detail) {
    next.service_details = normalizeDetailIds(prefill.service_detail)
  }
  if (prefill.service_interests?.length) {
    next.service_interests = prefill.service_interests.filter(isValidServiceId)
  }
  return next
}

/** Primary follow-up: website wins if selected, else software, else none. */
export function primaryServiceFollowUp(
  selected: readonly string[]
): 'website' | 'software' | null {
  if (selected.includes('website_design_development')) return 'website'
  if (selected.includes('custom_software_systems')) return 'software'
  return null
}

export function buildWorkflowFocus(selected: readonly string[]): string {
  const labels = selected.map(serviceLabel).filter(Boolean)
  return labels.join(', ').slice(0, INTAKE_LIMITS.workflow_focus)
}

export function buildShortIntakePayload(
  state: ShortIntakeFormState,
  opts?: { correlationId?: string; source?: string }
): Record<string, unknown> {
  const interests = state.service_interests
  const workflow = buildWorkflowFocus(interests)
  const details = state.service_details
  const priority = deriveLeadPriorityBand(
    state.project_clarity,
    state.timeline_readiness,
    state.budget_readiness
  )
  const payload: Record<string, unknown> = {
    leave_blank: state.leave_blank || undefined,
    contact_name: state.contact_name.trim().slice(0, INTAKE_LIMITS.contact_name),
    email: state.email.trim().slice(0, INTAKE_LIMITS.email),
    phone: state.phone.trim()
      ? state.phone.trim().slice(0, INTAKE_LIMITS.phone)
      : undefined,
    business_name: state.business_name.trim()
      ? state.business_name.trim().slice(0, INTAKE_LIMITS.business_name)
      : undefined,
    industry: state.industry || undefined,
    main_pain: state.main_pain.trim()
      ? state.main_pain.trim().slice(0, INTAKE_LIMITS.main_pain)
      : undefined,
    service_interests: interests,
    service_detail: details.length
      ? details.join(',').slice(0, INTAKE_LIMITS.service_detail)
      : undefined,
    project_clarity: state.project_clarity || undefined,
    timeline_readiness: state.timeline_readiness || undefined,
    budget_readiness: state.budget_readiness || undefined,
    lead_priority_band: state.project_clarity ? priority : undefined,
    preferred_next_step: state.preferred_next_step || undefined,
    workflow_focus: workflow || undefined,
    source: (opts?.source || 'consultation_intake_short').slice(0, INTAKE_LIMITS.source),
  }
  if (opts?.correlationId) {
    payload.correlation_id = opts.correlationId
  }
  return payload
}

export function readPrefillFromSearch(search: string): IntakePrefill {
  const params = new URLSearchParams(search.startsWith('?') ? search : `?${search}`)
  const interestsRaw = params.get('services') || params.get('service_interests') || ''
  const interests = interestsRaw
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
  return {
    industry: params.get('industry') || undefined,
    main_pain: params.get('pain') || params.get('main_pain') || undefined,
    contact_name: params.get('name') || params.get('contact_name') || undefined,
    email: params.get('email') || undefined,
    business_name: params.get('business') || params.get('business_name') || undefined,
    phone: params.get('phone') || undefined,
    source: params.get('source') || undefined,
    service_interests: interests.length ? interests : undefined,
    service_detail: params.get('service_detail') || undefined,
  }
}

export function readPrefillFromStorage(): IntakePrefill | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = sessionStorage.getItem(INTAKE_PREFILL_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as IntakePrefill
    return parsed && typeof parsed === 'object' ? parsed : null
  } catch {
    return null
  }
}

export function writePrefillToStorage(prefill: IntakePrefill): void {
  if (typeof window === 'undefined') return
  try {
    sessionStorage.setItem(INTAKE_PREFILL_STORAGE_KEY, JSON.stringify(prefill))
  } catch {
    /* ignore quota / private mode */
  }
}

export function clearPrefillStorage(): void {
  if (typeof window === 'undefined') return
  try {
    sessionStorage.removeItem(INTAKE_PREFILL_STORAGE_KEY)
  } catch {
    /* ignore */
  }
}

export function mergePrefills(...parts: Array<IntakePrefill | null | undefined>): IntakePrefill {
  const out: IntakePrefill = {}
  for (const part of parts) {
    if (!part) continue
    if (part.industry) out.industry = part.industry
    if (part.main_pain) out.main_pain = part.main_pain
    if (part.contact_name) out.contact_name = part.contact_name
    if (part.email) out.email = part.email
    if (part.business_name) out.business_name = part.business_name
    if (part.phone) out.phone = part.phone
    if (part.source) out.source = part.source
    if (part.service_detail) out.service_detail = part.service_detail
    if (part.service_interests?.length) out.service_interests = [...part.service_interests]
  }
  return out
}

export function getOrCreateIntakeCorrelationId(): string {
  if (typeof window === 'undefined') {
    return `intake_${Date.now()}`
  }
  try {
    const existing = sessionStorage.getItem(INTAKE_CORRELATION_STORAGE_KEY)
    if (existing && existing.trim()) return existing.trim()
    const id =
      typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? crypto.randomUUID()
        : `intake_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`
    sessionStorage.setItem(INTAKE_CORRELATION_STORAGE_KEY, id)
    return id
  } catch {
    return `intake_${Date.now()}`
  }
}

export function clearIntakeCorrelationId(): void {
  if (typeof window === 'undefined') return
  try {
    sessionStorage.removeItem(INTAKE_CORRELATION_STORAGE_KEY)
  } catch {
    /* ignore */
  }
}

export function buildIntakeHandoffPath(
  basePath: string,
  slots?: Record<string, unknown> | null
): string {
  if (!basePath.startsWith('/intake')) return basePath
  if (!slots || typeof slots !== 'object') return basePath
  const params = new URLSearchParams()
  const industry = String(slots.industry || '').trim()
  const pain = String(slots.main_pain || '').trim()
  const email = String(slots.contact_email || slots.email || '').trim()
  const name = String(slots.name || slots.contact_name || '').trim()
  const business = String(slots.business_name || '').trim()
  if (industry) params.set('industry', industry.slice(0, 80))
  if (pain) params.set('pain', pain.slice(0, 400))
  if (email) params.set('email', email.slice(0, 254))
  if (name) params.set('name', name.slice(0, 200))
  if (business) params.set('business', business.slice(0, 200))
  params.set('source', 'site_chatbot')
  const qs = params.toString()
  writePrefillToStorage({
    industry: industry || undefined,
    main_pain: pain || undefined,
    email: email || undefined,
    contact_name: name || undefined,
    business_name: business || undefined,
    source: 'site_chatbot',
  })
  return qs ? `${basePath}?${qs}` : basePath
}

export function isValidServiceId(id: string): id is ServiceInterestId {
  return SERVICE_OPTIONS.some((opt) => opt.id === id)
}
