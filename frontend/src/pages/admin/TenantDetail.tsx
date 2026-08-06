import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiClient } from '../../services/apiClient'
import { usePlatformAdmin } from '../../hooks/usePlatformAdmin'
import { AdminReauthModal } from '../../components/AdminReauthModal'
import type {
  AdminTenant,
  AdminTenantDetailResponse,
  CustomerHealthSummary,
  OAuthProviderState,
  TenantInfrastructure,
  TenantSupportActivityItem,
  TenantSupportChecklistItem,
  UsageAdoptionSummary,
} from '../../types/admin'
import {
  AdminPanel,
  AdminSubPanel,
  FieldGrid,
  FieldItem,
  MetricTile,
  StatusBadge,
  checklistStatusLabel,
  checklistTone,
  type StatusTone,
} from './adminUi'

interface SyncJobRow {
  job_id: string
  status: string
  error_message?: string | null
  created_at?: string
  retryable?: boolean
}

function oauthTone(state: OAuthProviderState | undefined): StatusTone {
  switch (state) {
    case 'connected':
      return 'ok'
    case 'expired':
    case 'refresh_failed':
      return 'warn'
    case 'revoked':
    case 'disconnected':
      return 'bad'
    default:
      return 'unknown'
  }
}

function subscriptionTone(status: string | undefined): StatusTone {
  const s = (status || 'unknown').toLowerCase()
  if (s === 'active' || s === 'trialing') return 'ok'
  if (s === 'past_due' || s === 'unpaid') return 'warn'
  if (s === 'canceled' || s === 'cancelled' || s === 'incomplete_expired') return 'bad'
  if (s === 'unknown' || !s) return 'unknown'
  return 'neutral'
}

const SECTION_JUMP = [
  { id: 'support-checklist', label: 'Checklist' },
  { id: 'customer-success', label: 'Success' },
  { id: 'account-access', label: 'Account' },
  { id: 'integration-health', label: 'Integrations' },
  { id: 'product-health', label: 'Product' },
  { id: 'commercial', label: 'Commercial' },
  { id: 'support-activity', label: 'Support' },
  { id: 'sync-jobs', label: 'Sync' },
  { id: 'support-actions', label: 'Actions' },
] as const

function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export function TenantDetail() {
  const { tenantId } = useParams()
  const id = Number(tenantId)
  const { startImpersonation, context } = usePlatformAdmin()
  const destructiveEnabled = Boolean(context?.security?.destructive_enabled)
  const [tenant, setTenant] = useState<AdminTenant | null>(null)
  const [infrastructure, setInfrastructure] = useState<TenantInfrastructure | null>(null)
  const [dossier, setDossier] = useState<Partial<AdminTenantDetailResponse> | null>(null)
  const [syncJobs, setSyncJobs] = useState<SyncJobRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [impersonating, setImpersonating] = useState(false)
  const [showStepUp, setShowStepUp] = useState(false)
  const [retryJobId, setRetryJobId] = useState<string | null>(null)
  const [lifecycleAction, setLifecycleAction] = useState<'suspend' | 'resume' | null>(null)
  const [confirmText, setConfirmText] = useState('')
  const [retryBusy, setRetryBusy] = useState(false)
  const [retryMessage, setRetryMessage] = useState<string | null>(null)

  const loadSyncJobs = useCallback(async (tenantNumericId: number) => {
    try {
      const result = await apiClient.listAdminTenantSyncJobs(tenantNumericId, { limit: 10 })
      setSyncJobs((result.items || []) as SyncJobRow[])
    } catch {
      setSyncJobs([])
    }
  }, [])

  useEffect(() => {
    if (!Number.isFinite(id)) {
      setError('Invalid tenant id')
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    void apiClient
      .getAdminTenant(id)
      .then(async (result) => {
        if (cancelled) return
        setTenant(result.tenant as AdminTenant)
        setInfrastructure(result.infrastructure as TenantInfrastructure)
        setDossier(result)
        await loadSyncJobs(id)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load tenant')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id, loadSyncJobs])

  if (loading) return <p className="text-sm text-zinc-500">Loading tenant…</p>
  if (error && !tenant) return <p className="text-sm text-red-600">{error}</p>
  if (!tenant) return <p className="text-sm text-red-600">Tenant not found</p>

  const account = dossier?.account
  const access = dossier?.access
  const integrations = dossier?.integrations
  const productHealth = dossier?.product_health
  const commercial = dossier?.commercial
  const supportActivity: TenantSupportActivityItem[] = dossier?.support_activity || []
  const gmailState = (integrations?.gmail?.state ||
    (infrastructure?.gmail_connected ? 'connected' : 'disconnected')) as OAuthProviderState
  const outlookState = (integrations?.outlook?.state ||
    (infrastructure?.outlook_connected ? 'connected' : 'disconnected')) as OAuthProviderState
  const completedSync = syncJobs.find((job) => String(job.status).toLowerCase() === 'completed')
  const failedSync = syncJobs.find((job) =>
    ['failed', 'retrying'].includes(String(job.status).toLowerCase()),
  )
  const failedJobCount =
    integrations?.failed_job_count ??
    syncJobs.filter((job) => ['failed', 'retrying'].includes(String(job.status).toLowerCase()))
      .length
  const pendingJobCount =
    integrations?.pending_job_count ??
    infrastructure?.pending_gmail_jobs ??
    syncJobs.filter((job) => String(job.status).toLowerCase() === 'pending').length
  const processingJobCount =
    integrations?.processing_job_count ??
    syncJobs.filter((job) => String(job.status).toLowerCase() === 'processing').length
  const lastSuccessfulSync =
    integrations?.last_successful_sync_at ||
    completedSync?.created_at ||
    (infrastructure?.sync_status?.last_sync
      ? String(infrastructure.sync_status.last_sync)
      : null)
  const lastFailedSync = integrations?.last_failed_sync_at || failedSync?.created_at || null
  const retryableKnown =
    integrations?.has_retryable_failed_job !== undefined
      ? Boolean(integrations.has_retryable_failed_job)
      : syncJobs.some((job) => job.retryable)
  const lastActivity =
    productHealth?.last_product_activity_at ||
    access?.last_login ||
    tenant.last_login ||
    null
  const backgroundJobsLabel = (() => {
    const counts =
      productHealth?.background_jobs ||
      integrations?.job_counts ||
      (failedJobCount || pendingJobCount || processingJobCount
        ? {
            pending: pendingJobCount,
            processing: processingJobCount,
            failed: failedJobCount,
          }
        : syncJobs.length
          ? {
              completed: syncJobs.filter((j) => String(j.status).toLowerCase() === 'completed')
                .length,
              failed: failedJobCount,
            }
          : null)
    if (!counts) return 'Unknown'
    const entries = Object.entries(counts)
    if (!entries.length) return 'None'
    return entries.map(([k, v]) => `${k}:${v}`).join(' · ')
  })()
  const checklist: TenantSupportChecklistItem[] = dossier?.support_checklist || []
  const impersonationEligibility = dossier?.impersonation_eligibility || {
    eligible: tenant.is_active,
    reason_code: tenant.is_active ? 'AVAILABLE' : 'USER_INACTIVE',
    reason_label: tenant.is_active
      ? 'Available after operator step-up and MFA'
      : 'Account inactive',
  }
  const impersonationDisabled =
    impersonating || impersonationEligibility.eligible === false
  const hasBlockedChecklist = checklist.some((item) => item.status === 'blocked')

  const health = dossier?.customer_health as CustomerHealthSummary | undefined
  const usage = dossier?.usage_adoption as UsageAdoptionSummary | undefined
  const friction = dossier?.friction_experience
  const outcomes = dossier?.customer_outcomes
  const analyticsState = dossier?.analytics_state || health?.analytics_state || usage?.analytics_state
  const showCustomerSuccess = Boolean(health || usage || analyticsState)
  const stateStatus = analyticsState?.status || 'unknown'
  const analyticsDisabled = stateStatus === 'disabled'
  const healthTone = checklistTone(
    health?.status === 'at_risk'
      ? 'attention'
      : health?.status === 'insufficient_data'
        ? 'unknown'
        : (health?.status as string) || 'unknown',
  )

  const scrollToSection = (sectionId: string) => {
    const el = document.getElementById(sectionId)
    if (!el) return
    el.scrollIntoView({
      behavior: prefersReducedMotion() ? 'auto' : 'smooth',
      block: 'start',
    })
  }

  const jumpItems = SECTION_JUMP.filter((item) => {
    if (item.id === 'support-checklist') return checklist.length > 0
    if (item.id === 'customer-success') return showCustomerSuccess
    return true
  })

  return (
    <div className="space-y-5">
      {/* Identity hero */}
      <div
        className={
          hasBlockedChecklist
            ? 'rounded-xl bg-red-500 p-0 pl-1 dark:bg-red-600'
            : undefined
        }
      >
        <div
          className={[
            'rounded-xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900',
            hasBlockedChecklist ? 'rounded-l-[10px]' : '',
          ].join(' ')}
        >
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <Link
              to="/admin/tenants"
              className="text-sm text-teal-700 underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600 dark:text-teal-400"
            >
              ← Back to tenants
            </Link>
            <h2 className="mt-2 break-words text-xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
              {tenant.name}
            </h2>
            <p className="mt-0.5 break-words text-sm text-zinc-600 dark:text-zinc-300">
              {tenant.email}
            </p>
            {(account?.business_name ?? tenant.business_name) ? (
              <p className="mt-1 break-words text-sm text-zinc-500">
                {account?.business_name ?? tenant.business_name}
              </p>
            ) : null}
            <div className="mt-3 flex flex-wrap gap-2">
              <StatusBadge
                label={tenant.is_active ? 'Active' : 'Inactive'}
                tone={tenant.is_active ? 'ok' : 'bad'}
              />
              <StatusBadge
                label={tenant.email_verified ? 'Verified' : 'Unverified'}
                tone={tenant.email_verified ? 'ok' : 'warn'}
              />
              <StatusBadge
                label={tenant.onboarding_completed ? 'Onboarding complete' : 'Onboarding incomplete'}
                tone={tenant.onboarding_completed ? 'ok' : 'warn'}
              />
              {hasBlockedChecklist ? (
                <StatusBadge label="Attention needed" tone="bad" />
              ) : null}
            </div>
          </div>
          <div className="flex flex-col items-stretch gap-1 sm:items-end">
            <button
              type="button"
              disabled={impersonationDisabled}
              title={
                impersonationEligibility.eligible
                  ? impersonationEligibility.reason_label
                  : impersonationEligibility.reason_label
              }
              aria-label={
                impersonationEligibility.eligible
                  ? 'View as this user'
                  : `View as this user unavailable: ${impersonationEligibility.reason_label}`
              }
              onClick={() => {
                setShowStepUp(true)
                setError(null)
              }}
              className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-teal-600 dark:hover:bg-teal-500"
            >
              View as this user
            </button>
            {!impersonationEligibility.eligible ? (
              <p className="text-xs text-zinc-500">{impersonationEligibility.reason_label}</p>
            ) : null}
          </div>
        </div>
        </div>
      </div>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      {retryMessage ? <p className="text-sm text-emerald-700">{retryMessage}</p> : null}

      {/* Sticky section jump — document order matches visual sections */}
      <nav
        aria-label="Tenant dossier sections"
        className="sticky top-[3.75rem] z-30 -mx-1 overflow-x-auto rounded-lg border border-zinc-200/90 bg-white/95 px-2 py-2 shadow-sm backdrop-blur dark:border-zinc-800 dark:bg-zinc-900/95"
      >
        <ul className="flex min-w-min flex-wrap gap-1 sm:flex-nowrap">
          {jumpItems.map((item) => (
            <li key={item.id} className="shrink-0">
              <button
                type="button"
                onClick={() => scrollToSection(item.id)}
                className="rounded-md px-2.5 py-1.5 text-xs font-medium text-zinc-700 hover:bg-teal-50 hover:text-teal-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600 dark:text-zinc-300 dark:hover:bg-teal-950/50 dark:hover:text-teal-200"
              >
                {item.label}
              </button>
            </li>
          ))}
        </ul>
      </nav>

      {checklist.length > 0 ? (
        <AdminPanel
          id="support-checklist"
          title="Support checklist"
          headingAs="h3"
          description="Fast “what is wrong?” view. Click an item to jump to the dossier section. Read-only — no new mutations."
        >
          <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {checklist.map((item) => {
              const explanation = item.explanation || item.detail
              const edge =
                item.status === 'blocked'
                  ? 'border-l-red-500'
                  : item.status === 'attention'
                    ? 'border-l-amber-500'
                    : item.status === 'healthy'
                      ? 'border-l-emerald-500'
                      : 'border-l-zinc-300 dark:border-l-zinc-600'
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => scrollToSection(item.section)}
                    aria-label={`${item.label}: ${checklistStatusLabel(item.status)}${
                      explanation ? `. ${explanation}` : ''
                    }`}
                    className={`flex w-full items-center justify-between gap-2 rounded-lg border border-zinc-200 border-l-4 bg-white px-3 py-2 text-left text-sm hover:border-teal-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600 dark:border-zinc-800 dark:bg-zinc-950 ${edge}`}
                  >
                    <span className="min-w-0">
                      <span className="font-medium text-zinc-900 dark:text-zinc-100">
                        {item.label}
                      </span>
                      {explanation ? (
                        <span className="mt-0.5 block break-words text-xs text-zinc-500">
                          {explanation}
                        </span>
                      ) : null}
                    </span>
                    <StatusBadge
                      label={checklistStatusLabel(item.status)}
                      tone={checklistTone(item.status)}
                    />
                  </button>
                </li>
              )
            })}
          </ul>
        </AdminPanel>
      ) : null}

      {/* At-a-glance — ops/signal tiles; CRM totals live in Customer outcomes when present */}
      {(() => {
        const tiles: Array<{
          key: string
          label: string
          value?: string | number | null
          hint?: string
          availability?: 'ok' | 'disabled' | 'unavailable' | 'unknown' | 'empty'
        }> = []
        // CRM counts belong in Customer outcomes when that panel is shown — avoid double tiles.
        if (!showCustomerSuccess || !outcomes) {
          if (outcomes?.leads_captured != null) {
            tiles.push({ key: 'leads', label: 'Leads', value: outcomes.leads_captured })
          }
          if (outcomes?.contacts_captured != null) {
            tiles.push({ key: 'contacts', label: 'Contacts', value: outcomes.contacts_captured })
          }
          if (outcomes?.syncs_completed != null) {
            tiles.push({
              key: 'syncs',
              label: 'Syncs completed',
              value: outcomes.syncs_completed,
            })
          }
        }
        if (integrations?.failed_job_count != null || syncJobs.length > 0) {
          tiles.push({ key: 'failed', label: 'Failed jobs', value: failedJobCount })
        }
        if (productHealth?.ai_budget?.budget_cap_usd != null) {
          tiles.push({
            key: 'ai',
            label: 'AI usage / cap',
            value: `$${Number(productHealth.ai_budget.estimated_cost_usd || 0).toFixed(2)} / $${Number(productHealth.ai_budget.budget_cap_usd).toFixed(2)}`,
            hint: 'Estimated',
          })
        }
        if (lastActivity) {
          tiles.push({
            key: 'activity',
            label: 'Last activity',
            value: String(lastActivity),
          })
        }
        if (analyticsDisabled) {
          tiles.push({
            key: 'analytics',
            label: 'Analytics',
            availability: 'disabled',
            hint: 'Not zero usage',
          })
        } else if (stateStatus === 'unavailable' || stateStatus === 'stale') {
          tiles.push({
            key: 'analytics',
            label: 'Analytics',
            availability: stateStatus === 'unavailable' ? 'unavailable' : 'ok',
            value: stateStatus === 'stale' ? 'Stale' : null,
            hint: stateStatus === 'stale' ? 'Aggregates may be behind' : undefined,
          })
        }
        if (tiles.length === 0) return null
        return (
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {tiles.map((t) => (
              <MetricTile
                key={t.key}
                label={t.label}
                value={t.value}
                hint={t.hint}
                availability={t.availability ?? 'ok'}
              />
            ))}
          </div>
        )
      })()}

      {showCustomerSuccess ? (
        <AdminPanel
          id="customer-success"
          title="Customer Success"
          headingAs="h3"
          description="Read-only adoption and experience signals. Disabled analytics is not the same as zero usage."
          right={
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="text-zinc-500">Analytics</span>
              <StatusBadge
                label={String(stateStatus)}
                tone={
                  stateStatus === 'available'
                    ? 'ok'
                    : stateStatus === 'disabled' || stateStatus === 'unavailable'
                      ? 'neutral'
                      : stateStatus === 'stale'
                        ? 'warn'
                        : 'unknown'
                }
              />
            </div>
          }
        >
          <div className="space-y-3">
            {usage?.last_aggregated_at ? (
              <p className="text-xs text-zinc-500">
                Aggregates updated {String(usage.last_aggregated_at)}
              </p>
            ) : null}
            {health ? (
              <AdminSubPanel
                id="customer-health"
                title="Customer health"
                headingAs="h4"
                right={
                  <StatusBadge label={health.status || 'unknown'} tone={healthTone} />
                }
              >
                {health.recommended_focus ? (
                  <p className="text-sm text-zinc-600 dark:text-zinc-300">
                    Focus: {health.recommended_focus}
                  </p>
                ) : null}
                <ul className="mt-2 space-y-1 text-sm">
                  {(health.reasons || []).map((r) => (
                    <li key={r.code} className="break-words text-zinc-600 dark:text-zinc-300">
                      <span className="font-mono text-xs">{r.code}</span> — {r.detail}
                    </li>
                  ))}
                </ul>
              </AdminSubPanel>
            ) : null}
            {usage ? (
              <AdminSubPanel
                id="usage-adoption"
                title={`Usage & adoption${usage.lookback_days ? ` (${usage.lookback_days}d)` : ''}`}
                headingAs="h4"
              >
                {analyticsDisabled ? (
                  <p className="text-sm text-zinc-500">
                    Product analytics disabled — metrics unavailable (not zero activity).
                  </p>
                ) : (
                  <FieldGrid>
                    <FieldItem label="Active days" value={usage.active_days ?? '—'} />
                    <FieldItem label="Sessions" value={usage.sessions ?? '—'} />
                    <FieldItem
                      label="Meaningful actions"
                      value={usage.meaningful_actions ?? '—'}
                    />
                    <FieldItem label="Workflow started" value={usage.workflow_started ?? '—'} />
                    <FieldItem label="Workflow failed" value={usage.workflow_failed ?? '—'} />
                    <FieldItem
                      label="Completion rate"
                      value={
                        usage.workflow_completion_rate == null
                          ? '—'
                          : `${Math.round(usage.workflow_completion_rate * 100)}%`
                      }
                    />
                  </FieldGrid>
                )}
                {(usage.top_features || []).length > 0 ? (
                  <p className="mt-2 break-words text-xs text-zinc-500">
                    Top features:{' '}
                    {usage.top_features!.map((f) => `${f.feature_key}(${f.opens})`).join(', ')}
                  </p>
                ) : null}
              </AdminSubPanel>
            ) : null}
            {friction ? (
              <AdminSubPanel id="friction-experience" title="Friction & experience" headingAs="h4">
                {(friction.signals || []).length === 0 ? (
                  <p className="text-sm text-zinc-500">No friction signals.</p>
                ) : (
                  <ul className="space-y-2 text-sm">
                    {friction.signals.map((s) => (
                      <li
                        key={s.code}
                        className="flex flex-wrap items-center justify-between gap-2"
                      >
                        <span className="break-words">
                          <span className="font-mono text-xs">{s.code}</span> — {s.explanation}
                        </span>
                        <StatusBadge
                          label={s.severity}
                          tone={
                            s.severity === 'blocked'
                              ? 'bad'
                              : s.severity === 'attention'
                                ? 'warn'
                                : 'neutral'
                          }
                        />
                      </li>
                    ))}
                  </ul>
                )}
                <p className="mt-2 text-xs text-zinc-500">
                  Accessibility interface signals are disabled until privacy review.
                </p>
              </AdminSubPanel>
            ) : null}
            {outcomes ? (
              <AdminSubPanel id="customer-outcomes" title="Customer outcomes" headingAs="h4">
                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                  <MetricTile label="Leads captured" value={outcomes.leads_captured ?? null} />
                  <MetricTile
                    label="Contacts captured"
                    value={outcomes.contacts_captured ?? null}
                  />
                  <MetricTile label="Syncs completed" value={outcomes.syncs_completed ?? null} />
                  <MetricTile
                    label="Onboarding completed"
                    value={
                      outcomes.onboarding_completed == null
                        ? null
                        : outcomes.onboarding_completed
                          ? 'Yes'
                          : 'No'
                    }
                  />
                </div>
                {outcomes.notes ? (
                  <p className="mt-2 break-words text-xs text-zinc-500">{outcomes.notes}</p>
                ) : null}
              </AdminSubPanel>
            ) : null}
          </div>
        </AdminPanel>
      ) : null}

      <AdminReauthModal
        open={showStepUp}
        title={
          retryJobId
            ? 'Step-up required to retry sync'
            : lifecycleAction === 'suspend'
              ? 'Step-up required to pause tenant'
              : lifecycleAction === 'resume'
                ? 'Step-up required to resume tenant'
                : 'Step-up required to impersonate'
        }
        busy={impersonating || retryBusy}
        error={error}
        onCancel={() => {
          setShowStepUp(false)
          setRetryJobId(null)
          setLifecycleAction(null)
          setConfirmText('')
          setError(null)
        }}
        onConfirm={async (password, mfaCode, recoveryCode) => {
          setError(null)
          try {
            if (retryJobId) {
              if (confirmText.trim().toLowerCase() !== 'retry') {
                setError('Type RETRY to confirm')
                return
              }
              setRetryBusy(true)
              await apiClient.reauthenticateAdmin({
                password,
                mfa_code: mfaCode,
                recovery_code: recoveryCode,
              })
              const idempotencyKey =
                typeof crypto !== 'undefined' && 'randomUUID' in crypto
                  ? crypto.randomUUID()
                  : `retry-${Date.now()}`
              const result = await apiClient.retryAdminTenantSyncJob(tenant.id, retryJobId, {
                confirm: 'retry',
                tenant_id: tenant.id,
                idempotency_key: idempotencyKey,
              })
              setRetryMessage(`Queued new sync job ${result.new_job_id}`)
              setShowStepUp(false)
              setRetryJobId(null)
              setConfirmText('')
              await loadSyncJobs(tenant.id)
            } else if (lifecycleAction) {
              const word = lifecycleAction
              if (confirmText.trim().toLowerCase() !== word) {
                setError(`Type ${word.toUpperCase()} to confirm`)
                return
              }
              setRetryBusy(true)
              await apiClient.reauthenticateAdmin({
                password,
                mfa_code: mfaCode,
                recovery_code: recoveryCode,
              })
              if (word === 'suspend') {
                await apiClient.suspendAdminTenant(tenant.id, { confirm: 'suspend' })
                setRetryMessage('Tenant paused (is_active=false)')
                setTenant({ ...tenant, is_active: false })
              } else {
                await apiClient.resumeAdminTenant(tenant.id, { confirm: 'resume' })
                setRetryMessage('Tenant resumed (is_active=true)')
                setTenant({ ...tenant, is_active: true })
              }
              setShowStepUp(false)
              setLifecycleAction(null)
              setConfirmText('')
            } else {
              setImpersonating(true)
              await startImpersonation(tenant, password, mfaCode, recoveryCode)
            }
          } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Action failed')
            setImpersonating(false)
          } finally {
            setRetryBusy(false)
          }
        }}
      />

      {retryJobId ? (
        <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm dark:border-amber-700 dark:bg-amber-950/40">
          <p className="font-medium text-amber-950 dark:text-amber-100">
            Confirm retry of job <span className="font-mono">{retryJobId}</span>
          </p>
          <p className="mt-1 text-amber-900 dark:text-amber-200">
            Type <strong>RETRY</strong> then complete step-up. This queues a new sync; it does not
            cancel billing or disconnect OAuth.
          </p>
          <input
            type="text"
            value={confirmText}
            onChange={(event) => setConfirmText(event.target.value)}
            placeholder="Type RETRY"
            className="mt-3 w-full max-w-xs rounded-lg border border-amber-300 bg-white px-3 py-2 dark:border-amber-700 dark:bg-zinc-950"
            autoComplete="off"
          />
        </div>
      ) : null}

      {lifecycleAction ? (
        <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm dark:border-amber-700 dark:bg-amber-950/40">
          <p className="font-medium text-amber-950 dark:text-amber-100">
            Confirm {lifecycleAction === 'suspend' ? 'pause' : 'resume'} for tenant #{tenant?.id}
          </p>
          <p className="mt-1 text-amber-900 dark:text-amber-200">
            Type <strong>{lifecycleAction.toUpperCase()}</strong> then complete step-up. This flips
            account access only — it does not delete data.
          </p>
          <input
            type="text"
            value={confirmText}
            onChange={(event) => setConfirmText(event.target.value)}
            placeholder={`Type ${lifecycleAction.toUpperCase()}`}
            className="mt-3 w-full max-w-xs rounded-lg border border-amber-300 bg-white px-3 py-2 dark:border-amber-700 dark:bg-zinc-950"
            autoComplete="off"
          />
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <AdminPanel id="account-access" title="Account & Access" headingAs="h3">
          <FieldGrid>
            <FieldItem label="Tenant ID" value={account?.id ?? tenant.id} />
            <FieldItem label="Name" value={account?.name ?? tenant.name} />
            <FieldItem label="Email" value={account?.email ?? tenant.email} />
            <FieldItem
              label="Business"
              value={account?.business_name ?? tenant.business_name ?? '—'}
            />
            <FieldItem label="Industry" value={account?.industry ?? tenant.industry ?? '—'} />
            <FieldItem label="Role" value={account?.role ?? tenant.role ?? '—'} />
            <FieldItem
              label="Created"
              value={account?.created_at ? String(account.created_at) : tenant.created_at || '—'}
            />
            <FieldItem
              label="Last login"
              value={access?.last_login ? String(access.last_login) : tenant.last_login || '—'}
            />
            <FieldItem
              label="Active sessions"
              value={
                access?.active_session_count === null || access?.active_session_count === undefined
                  ? 'Unknown'
                  : access.active_session_count
              }
            />
            <FieldItem label="Last login IP" value={access?.last_login_ip || 'Unknown'} />
            <FieldItem
              label="Last login UA"
              value={access?.last_login_user_agent || 'Unknown'}
              className="sm:col-span-2"
            />
            <FieldItem
              label="Onboarding"
              value={
                (account?.onboarding_completed ?? tenant.onboarding_completed)
                  ? 'Complete'
                  : `Step ${account?.onboarding_step ?? tenant.onboarding_step ?? 0}`
              }
            />
          </FieldGrid>
        </AdminPanel>

        <AdminPanel id="integration-health" title="Integration Health" headingAs="h3">
          <FieldGrid>
            <FieldItem
              label="Gmail authorization"
              value={<StatusBadge label={gmailState} tone={oauthTone(gmailState)} />}
            />
            <FieldItem
              label="Outlook authorization"
              value={<StatusBadge label={outlookState} tone={oauthTone(outlookState)} />}
            />
            <FieldItem
              label="Sync status"
              value={
                integrations?.sync_status ||
                String(infrastructure?.sync_status?.sync_status || 'Unknown')
              }
            />
            <FieldItem
              label="Last successful sync"
              value={lastSuccessfulSync ? String(lastSuccessfulSync) : 'Unknown'}
            />
            <FieldItem
              label="Last failed sync"
              value={lastFailedSync ? String(lastFailedSync) : '—'}
            />
            <FieldItem
              label="Job health"
              value={
                failedJobCount > 0
                  ? `${failedJobCount} failed`
                  : pendingJobCount + processingJobCount > 0
                    ? `${pendingJobCount + processingJobCount} active`
                    : 'No failed or active jobs'
              }
            />
            <FieldItem label="Pending jobs" value={pendingJobCount} />
            <FieldItem label="Processing jobs" value={processingJobCount} />
            <FieldItem label="Failed jobs" value={failedJobCount} />
            <FieldItem
              label="Latest sync error"
              value={
                integrations?.latest_sanitized_error || failedSync?.error_message || '—'
              }
              className="sm:col-span-2"
            />
            <FieldItem
              label="Retry candidates"
              value={
                integrations?.has_retryable_failed_job === undefined && !syncJobs.length
                  ? 'Unknown'
                  : retryableKnown
                    ? 'Yes'
                    : 'No'
              }
            />
          </FieldGrid>
        </AdminPanel>

        <AdminPanel id="product-health" title="Product Health" headingAs="h3">
          <FieldGrid>
            <FieldItem
              label="Last activity"
              value={lastActivity ? String(lastActivity) : 'Unknown'}
            />
            <FieldItem
              label="Onboarding blockers"
              value={
                productHealth?.onboarding_blockers?.length
                  ? productHealth.onboarding_blockers.join(', ')
                  : tenant.onboarding_completed
                    ? 'None'
                    : `onboarding_incomplete_step_${tenant.onboarding_step ?? 'unknown'}`
              }
            />
            <FieldItem
              label="Entitlements on"
              value={
                productHealth?.entitlements_enabled?.length
                  ? productHealth.entitlements_enabled.join(', ')
                  : 'None listed'
              }
            />
            <FieldItem
              label="Entitlements off"
              value={
                productHealth?.entitlements_disabled?.length
                  ? productHealth.entitlements_disabled.join(', ')
                  : 'None listed'
              }
            />
            <FieldItem
              label="AI budget"
              value={
                <StatusBadge
                  label={productHealth?.ai_budget?.status || 'unknown'}
                  tone={
                    productHealth?.ai_budget?.status === 'ok'
                      ? 'ok'
                      : productHealth?.ai_budget?.status === 'blocked'
                        ? 'bad'
                        : 'unknown'
                  }
                />
              }
            />
            <FieldItem
              label="AI usage / cap"
              value={
                productHealth?.ai_budget?.budget_cap_usd != null
                  ? `$${Number(productHealth.ai_budget.estimated_cost_usd || 0).toFixed(2)} / $${Number(productHealth.ai_budget.budget_cap_usd).toFixed(2)}`
                  : 'Unknown'
              }
            />
            <FieldItem label="Background jobs" value={backgroundJobsLabel} className="sm:col-span-2" />
          </FieldGrid>
        </AdminPanel>

        <AdminPanel id="commercial" title="Commercial Summary" headingAs="h3">
          <FieldGrid>
            <FieldItem
              label="Plan / tier"
              value={
                commercial?.tier ||
                (infrastructure?.subscription
                  ? String(infrastructure.subscription.tier)
                  : 'No subscription on file')
              }
            />
            <FieldItem
              label="Status"
              value={
                <StatusBadge
                  label={
                    commercial?.status ||
                    (infrastructure?.subscription
                      ? String(infrastructure.subscription.status || 'unknown')
                      : 'unknown')
                  }
                  tone={subscriptionTone(
                    commercial?.status ||
                      (infrastructure?.subscription
                        ? String(infrastructure.subscription.status || '')
                        : 'unknown'),
                  )}
                />
              }
            />
            <FieldItem
              label="Period end"
              value={
                commercial?.current_period_end
                  ? String(commercial.current_period_end)
                  : infrastructure?.subscription?.current_period_end
                    ? String(infrastructure.subscription.current_period_end)
                    : '—'
              }
            />
            <FieldItem
              label="Past due"
              value={
                commercial?.past_due === null || commercial?.past_due === undefined
                  ? infrastructure?.subscription
                    ? 'No'
                    : 'Unknown'
                  : commercial.past_due
                    ? 'Yes'
                    : 'No'
              }
            />
          </FieldGrid>
        </AdminPanel>
      </div>

      <AdminPanel
        id="support-activity"
        title="Recent Support Activity"
        headingAs="h3"
        empty={supportActivity.length === 0}
      >
        <ul className="divide-y divide-zinc-100 dark:divide-zinc-800">
          {supportActivity.slice(0, 20).map((item, index) => (
            <li key={`${item.action}-${item.timestamp}-${index}`} className="py-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="break-words font-medium">{item.action}</p>
                <StatusBadge
                  label={item.outcome || 'unknown'}
                  tone={
                    item.outcome === 'success'
                      ? 'ok'
                      : item.outcome === 'denied' || item.outcome === 'failure'
                        ? 'bad'
                        : 'neutral'
                  }
                />
              </div>
              <p className="mt-1 break-words text-zinc-600 dark:text-zinc-300">
                {item.timestamp ? String(item.timestamp) : '—'}
                {item.actor_user_id != null ? ` · actor ${item.actor_user_id}` : ''}
                {item.reason_code ? ` · ${item.reason_code}` : ''}
                {item.correlation_id ? ` · corr ${item.correlation_id}` : ''}
              </p>
            </li>
          ))}
        </ul>
      </AdminPanel>

      <AdminPanel
        id="sync-jobs"
        title="Gmail sync jobs"
        headingAs="h3"
        description="Low-risk ops: retry a failed sync only. Destructive controls remain disabled."
      >
        {syncJobs.length === 0 ? (
          <p className="text-sm text-zinc-500">No sync jobs found.</p>
        ) : (
          <ul className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {syncJobs.map((job) => (
              <li
                key={job.job_id}
                className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm"
              >
                <div className="min-w-0">
                  <p className="break-all font-mono text-xs">{job.job_id}</p>
                  <p className="break-words text-zinc-600 dark:text-zinc-300">
                    {job.status}
                    {job.error_message ? ` — ${job.error_message}` : ''}
                  </p>
                </div>
                {job.retryable ? (
                  <button
                    type="button"
                    disabled={retryBusy}
                    onClick={() => {
                      setRetryJobId(job.job_id)
                      setConfirmText('')
                      setRetryMessage(null)
                      setError(null)
                      setShowStepUp(true)
                    }}
                    className="rounded-lg border border-zinc-300 px-3 py-1.5 text-xs font-medium hover:bg-zinc-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600 dark:border-zinc-700 dark:hover:bg-zinc-800"
                  >
                    Retry failed sync
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </AdminPanel>

      <AdminPanel
        id="support-actions"
        title="Support actions"
        headingAs="h3"
        description="Impersonation and sync retry require step-up. Pause/resume require ADMIN_DESTRUCTIVE_ENABLED. Hard delete is not available."
      >
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={!destructiveEnabled || !tenant?.is_active || retryBusy}
            title={
              destructiveEnabled
                ? 'Pause account access'
                : 'Enable ADMIN_DESTRUCTIVE_ENABLED to unlock pause'
            }
            onClick={() => {
              setLifecycleAction('suspend')
              setRetryJobId(null)
              setConfirmText('')
              setError(null)
              setShowStepUp(true)
            }}
            className="rounded-lg border border-zinc-300 px-3 py-1.5 text-sm font-medium hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-700"
          >
            Pause account
          </button>
          <button
            type="button"
            disabled={!destructiveEnabled || Boolean(tenant?.is_active) || retryBusy}
            title={
              destructiveEnabled
                ? 'Resume account access'
                : 'Enable ADMIN_DESTRUCTIVE_ENABLED to unlock resume'
            }
            onClick={() => {
              setLifecycleAction('resume')
              setRetryJobId(null)
              setConfirmText('')
              setError(null)
              setShowStepUp(true)
            }}
            className="rounded-lg border border-zinc-300 px-3 py-1.5 text-sm font-medium hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-700"
          >
            Resume account
          </button>
        </div>
        {!destructiveEnabled ? (
          <p className="mt-2 text-xs text-zinc-500">
            Pause/resume stay locked while destructive admin is off.
          </p>
        ) : null}
      </AdminPanel>
    </div>
  )
}
