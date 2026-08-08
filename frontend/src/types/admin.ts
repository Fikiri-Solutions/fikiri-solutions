export interface PlatformAdminContext {
  is_platform_admin: boolean
  capabilities: string[]
  impersonating: boolean
  actor_user_id: number | null
  effective_user_id: number | null
  security?: PlatformOperatorSecurity
}

export interface PlatformOperatorSecurity {
  mfa_required: boolean
  mfa_enrolled: boolean
  step_up_active: boolean
  step_up_mfa_completed: boolean
  step_up_expires_at?: string | null
  impersonating?: boolean
  impersonation_disabled: boolean
  destructive_enabled?: boolean
  lockdown?: boolean
}

export interface PlatformAdminStatus {
  generated_at: string
  operator: {
    actor_user_id: number
    effective_user_id?: number | null
    capabilities: string[]
    security: PlatformOperatorSecurity
  }
  gates: {
    lockdown: boolean
    destructive_enabled: boolean
  }
  audit: {
    denied_available: boolean
    denied_count: number | null
    window_hours?: number
    since?: string
    reason?: string
    investigate_path: string
  }
  sync_jobs: {
    available: boolean
    failed: number | null
    retrying: number | null
    pending: number | null
    processing: number | null
    actionable: number | null
    reason?: string
    investigate_path: string
  }
  analytics: {
    available: boolean
    enabled: boolean | null
    tables_available: boolean | null
    state: string
    reason?: string
  }
}

export interface AdminTenant {
  id: number
  email: string
  name: string
  role?: string
  business_name?: string | null
  industry?: string | null
  is_active: boolean
  email_verified: boolean
  onboarding_completed: boolean
  onboarding_step?: number
  created_at?: string
  last_login?: string | null
}

export interface TenantInfrastructure {
  gmail_connected: boolean
  outlook_connected: boolean
  sync_status: Record<string, unknown> | null
  subscription: Record<string, unknown> | null
  pending_gmail_jobs: number
}

export type OAuthProviderState =
  | 'connected'
  | 'expired'
  | 'revoked'
  | 'refresh_failed'
  | 'disconnected'
  | 'unknown'

export interface TenantDossierAccount {
  id: number
  name?: string | null
  email?: string | null
  business_name?: string | null
  industry?: string | null
  role?: string | null
  is_active: boolean
  email_verified: boolean
  created_at?: string | null
  updated_at?: string | null
  last_login?: string | null
  onboarding_step?: number | null
  onboarding_completed: boolean
}

export interface TenantDossierAccess {
  is_active: boolean
  email_verified: boolean
  role?: string | null
  last_login?: string | null
  active_session_count?: number | null
  last_login_ip?: string | null
  last_login_user_agent?: string | null
}

export interface TenantDossierIntegrations {
  gmail: {
    provider: string
    connected: boolean
    state: OAuthProviderState
    expires_at?: string | null
    updated_at?: string | null
  }
  outlook: {
    provider: string
    connected: boolean
    state: OAuthProviderState
    expires_at?: string | null
    updated_at?: string | null
  }
  sync_status?: string | null
  last_sync_at?: string | null
  syncing?: boolean
  total_emails_indexed?: number | null
  pending_job_count: number
  processing_job_count: number
  failed_job_count: number
  job_counts?: Record<string, number>
  last_successful_sync_at?: string | null
  last_failed_sync_at?: string | null
  latest_sanitized_error?: string | null
  has_retryable_failed_job?: boolean
}

export interface TenantDossierProductHealth {
  last_product_activity_at?: string | null
  onboarding_complete: boolean
  onboarding_step?: number | null
  onboarding_blockers: string[]
  entitlements_enabled: string[]
  entitlements_disabled: string[]
  ai_budget: {
    status: string
    reason?: string
    tier?: string
    month?: string
    estimated_cost_usd?: number
    budget_cap_usd?: number
    allowed?: boolean
  }
  background_jobs: Record<string, number>
}

export interface TenantDossierCommercial {
  tier?: string | null
  status: string
  current_period_end?: string | null
  past_due?: boolean | null
  ai_budget?: TenantDossierProductHealth['ai_budget']
}

export interface TenantSupportActivityItem {
  timestamp?: string | null
  action: string
  outcome: string
  reason_code?: string | null
  actor_user_id?: number | null
  target_type?: string | null
  target_id?: string | null
  correlation_id?: string | null
}

export type ChecklistStatus =
  | 'healthy'
  | 'attention'
  | 'blocked'
  | 'unknown'
  | 'not_applicable'

export interface TenantSupportChecklistItem {
  id: string
  label: string
  status: ChecklistStatus
  section: string
  explanation?: string
  /** @deprecated use explanation */
  detail?: string
}

export interface ImpersonationEligibility {
  eligible: boolean
  reason_code: string
  reason_label: string
}

export type AnalyticsStateStatus =
  | 'disabled'
  | 'unavailable'
  | 'collecting'
  | 'partial'
  | 'available'
  | 'stale'
  | 'insufficient_data'

export interface AnalyticsState {
  status: AnalyticsStateStatus | string
  tracking_since?: string | null
  last_event_at?: string | null
  last_aggregated_at?: string | null
  coverage?: string | null
}

export interface CustomerHealthReason {
  code: string
  detail: string
}

export interface CustomerHealthSummary {
  status: string
  reasons: CustomerHealthReason[]
  dimensions?: Record<string, { status: string; reasons?: CustomerHealthReason[] }>
  recommended_focus?: string
  evaluated_at?: string
  analytics_state?: AnalyticsState
}

export interface UsageAdoptionSummary {
  lookback_days?: number
  active_days?: number | null
  sessions?: number | null
  meaningful_actions?: number | null
  workflow_started?: number | null
  workflow_failed?: number | null
  workflow_completion_rate?: number | null
  top_features?: Array<{ feature_key: string; opens: number }>
  active_days_7?: number | null
  sessions_7?: number | null
  last_aggregated_at?: string | null
  analytics_state?: AnalyticsState
}

export interface FrictionSignal {
  code: string
  explanation: string
  severity: string
  feature_key?: string | null
  evaluated_at?: string
}

export interface FrictionExperienceSummary {
  signals: FrictionSignal[]
  accessibility_signals?: unknown
}

export interface CustomerOutcomesSummary {
  leads_captured?: number | null
  contacts_captured?: number | null
  syncs_completed?: number | null
  onboarding_completed?: boolean | null
  estimated_time_saved?: number | null
  notes?: string
}

export interface AdminTenantDetailResponse {
  tenant: AdminTenant
  infrastructure: TenantInfrastructure
  account?: TenantDossierAccount
  access?: TenantDossierAccess
  integrations?: TenantDossierIntegrations
  product_health?: TenantDossierProductHealth
  commercial?: TenantDossierCommercial
  support_activity?: TenantSupportActivityItem[]
  support_checklist?: TenantSupportChecklistItem[]
  impersonation_eligibility?: ImpersonationEligibility
  analytics_state?: AnalyticsState
  customer_health?: CustomerHealthSummary
  usage_adoption?: UsageAdoptionSummary
  friction_experience?: FrictionExperienceSummary
  customer_outcomes?: CustomerOutcomesSummary
}

export interface AdminAuditEntry {
  id: number
  actor_user_id: number
  action: string
  target_type?: string | null
  target_id?: string | null
  outcome?: string | null
  capability?: string | null
  correlation_id?: string | null
  metadata?: { reason?: string; error_code?: string; code?: string } | null
  before?: unknown
  after?: unknown
  ip_address?: string | null
  created_at?: string
}

export interface ImpersonationContext {
  active: boolean
  actor_user_id?: number
  actor_email?: string | null
  actor_name?: string | null
}

/** Landing-page (site) chatbot transcript — staff review via /api/admin/site-chat */
export interface SiteChatSessionSummary {
  session_id: string
  source_page?: string | null
  first_seen_at?: string | null
  last_seen_at?: string | null
  turn_count?: number
  last_mode?: string | null
  latest_lead_tier?: string | null
  latest_lead_score?: number | null
  latest_lead_synopsis?: string | null
  latest_handoff_path?: string | null
}

export interface SiteChatMessage {
  role: string
  content: string
  mode?: string | null
  grounded?: boolean | null
  confidence?: number | null
  lead_assessment?: {
    tier?: string
    score?: number
    synopsis?: string
  } | null
  intake?: Record<string, unknown> | null
  handoff?: Record<string, unknown> | null
  created_at?: string | null
}

export interface SiteChatSessionDetail {
  session: SiteChatSessionSummary & {
    hashed_ip?: string | null
    hashed_user_agent?: string | null
    created_at?: string | null
    updated_at?: string | null
  }
  messages: SiteChatMessage[]
}

export interface SiteChatSessionsList {
  sessions: SiteChatSessionSummary[]
  total: number
  limit: number
  offset: number
}

export interface SiteChatTranscriptExport {
  format: 'text' | 'json'
  session_id: string
  content?: string
  session?: SiteChatSessionSummary
  messages?: SiteChatMessage[]
  [key: string]: unknown
}
