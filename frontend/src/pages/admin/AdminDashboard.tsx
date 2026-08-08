import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Building2, ClipboardList, KeyRound, MessageSquare } from 'lucide-react'
import { apiClient } from '../../services/apiClient'
import type { PlatformAdminStatus } from '../../types/admin'
import { AdminPanel, MetricTile, StatusBadge, type StatusTone } from './adminUi'

const destinations = [
  {
    to: '/admin/tenants',
    title: 'Tenant Directory',
    description: 'Browse client accounts and open a tenant dossier.',
    icon: Building2,
  },
  {
    to: '/admin/site-chat',
    title: 'Site Chat Logs',
    description: 'Review and download landing-page chatbot transcripts.',
    icon: MessageSquare,
  },
  {
    to: '/admin/security',
    title: 'MFA Security',
    description: 'Enroll an authenticator for privileged admin actions.',
    icon: KeyRound,
  },
  {
    to: '/admin/audit',
    title: 'Audit Log',
    description: 'Investigate operator and security events.',
    icon: ClipboardList,
  },
] as const

type SyncInboxItem = {
  job_id: string
  tenant_id: number
  tenant_email?: string | null
  tenant_name?: string | null
  business_name?: string | null
  status?: string
  error_message?: string | null
  created_at?: string | null
  dossier_path?: string | null
}

function boolLabel(value: boolean | null | undefined): string {
  if (value == null) return '—'
  return value ? 'Yes' : 'No'
}

function gateTone(lockdown: boolean, destructive: boolean): StatusTone {
  if (lockdown) return 'bad'
  if (destructive) return 'warn'
  return 'ok'
}

function analyticsTone(state: string): StatusTone {
  switch (state) {
    case 'available':
      return 'ok'
    case 'disabled':
      return 'neutral'
    case 'unavailable':
      return 'warn'
    default:
      return 'unknown'
  }
}

export function AdminDashboard() {
  const [status, setStatus] = useState<PlatformAdminStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [syncInbox, setSyncInbox] = useState<SyncInboxItem[]>([])
  const [syncInboxTotal, setSyncInboxTotal] = useState(0)
  const [syncInboxError, setSyncInboxError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    void apiClient
      .getPlatformAdminStatus()
      .then((result) => {
        if (!cancelled) setStatus(result)
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load platform status')
          setStatus(null)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    void apiClient
      .listPlatformSyncJobs({ status: 'failed,retrying', limit: 20, offset: 0 })
      .then((result) => {
        if (cancelled) return
        setSyncInbox((result.items || []) as SyncInboxItem[])
        setSyncInboxTotal(typeof result.total === 'number' ? result.total : 0)
        setSyncInboxError(result.available ? null : result.reason || 'Unavailable')
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setSyncInbox([])
        setSyncInboxTotal(0)
        setSyncInboxError(err instanceof Error ? err.message : 'Failed to load sync inbox')
      })

    return () => {
      cancelled = true
    }
  }, [])

  const security = status?.operator.security
  const gates = status?.gates
  const audit = status?.audit
  const sync = status?.sync_jobs
  const analytics = status?.analytics
  const capabilities = status?.operator.capabilities ?? []

  return (
    <div className="space-y-6">
      <div className="overflow-hidden rounded-xl border border-zinc-200/90 bg-white dark:border-zinc-800 dark:bg-zinc-900">
        <div className="flex">
          <div className="w-1 shrink-0 bg-teal-700 dark:bg-teal-500" aria-hidden />
          <div className="min-w-0 flex-1 p-5">
            <p className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">
              Platform operators
            </p>
            <h2 className="mt-1 text-xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
              Operator Console
            </h2>
            <p className="mt-1.5 max-w-2xl text-sm text-zinc-600 dark:text-zinc-300">
              Live read-only platform posture for operators. Investigate denied actions in Audit and
              tenant sync issues in the failed-sync inbox.
            </p>

            {loading ? <p className="mt-4 text-sm text-zinc-500">Loading platform status…</p> : null}
            {error ? <p className="mt-4 text-sm text-red-600">{error}</p> : null}

            {status ? (
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <MetricTile label="Operator ID" value={status.operator.actor_user_id} />
                <MetricTile
                  label="Capabilities"
                  value={capabilities.length}
                  hint={capabilities.length === 1 ? 'Named grant' : 'Named grants'}
                />
                <MetricTile
                  label="Denied (24h)"
                  value={audit?.denied_available ? audit.denied_count : null}
                  availability={audit?.denied_available ? 'ok' : 'unavailable'}
                  hint={
                    audit?.denied_available
                      ? `Last ${audit.window_hours ?? 24} hours`
                      : audit?.reason || 'Unavailable'
                  }
                  status={
                    audit?.denied_available && (audit.denied_count ?? 0) > 0 ? (
                      <StatusBadge label="Investigate" tone="warn" />
                    ) : undefined
                  }
                />
                <MetricTile
                  label="Failed syncs"
                  value={sync?.available ? sync.actionable : null}
                  availability={sync?.available ? 'ok' : 'unavailable'}
                  hint={
                    sync?.available
                      ? `${sync.failed ?? 0} failed · ${sync.retrying ?? 0} retrying`
                      : sync?.reason || 'Unavailable'
                  }
                  status={
                    sync?.available && (sync.actionable ?? 0) > 0 ? (
                      <StatusBadge label="Attention" tone="warn" />
                    ) : undefined
                  }
                />
              </div>
            ) : null}
          </div>
        </div>
      </div>

      {status ? (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            <AdminPanel
              title="Operator security"
              headingAs="h2"
              description="Session posture for this operator. MFA enrollment is managed under MFA Security."
              right={
                <StatusBadge
                  label={security?.step_up_active ? 'Step-up active' : 'Step-up idle'}
                  tone={security?.step_up_active ? 'ok' : 'neutral'}
                />
              }
            >
              <div className="grid gap-3 sm:grid-cols-2">
                <MetricTile label="MFA required" value={boolLabel(security?.mfa_required)} />
                <MetricTile label="MFA enrolled" value={boolLabel(security?.mfa_enrolled)} />
                <MetricTile
                  label="Step-up MFA done"
                  value={boolLabel(security?.step_up_mfa_completed)}
                />
                <MetricTile
                  label="Impersonation"
                  value={
                    security?.impersonation_disabled
                      ? 'Disabled'
                      : security?.impersonating
                        ? 'Active'
                        : 'Allowed'
                  }
                />
              </div>
              {security?.step_up_expires_at ? (
                <p className="mt-3 text-xs text-zinc-500">
                  Step-up expires at {security.step_up_expires_at}
                </p>
              ) : null}
            </AdminPanel>

            <AdminPanel
              title="Platform gates"
              headingAs="h2"
              description="Emergency lockdown and destructive mutation switch."
              right={
                <StatusBadge
                  label={
                    gates?.lockdown
                      ? 'Lockdown'
                      : gates?.destructive_enabled
                        ? 'Destructive on'
                        : 'Safe mode'
                  }
                  tone={gateTone(Boolean(gates?.lockdown), Boolean(gates?.destructive_enabled))}
                />
              }
            >
              <div className="grid gap-3 sm:grid-cols-2">
                <MetricTile label="Lockdown" value={boolLabel(gates?.lockdown)} />
                <MetricTile
                  label="Destructive enabled"
                  value={boolLabel(gates?.destructive_enabled)}
                  hint="ADMIN_DESTRUCTIVE_ENABLED"
                />
              </div>
            </AdminPanel>
          </div>

          <AdminPanel
            title="Named capabilities"
            headingAs="h2"
            description="Server-granted capabilities for this operator (not a client-side role)."
          >
            {capabilities.length ? (
              <ul className="flex flex-wrap gap-2">
                {capabilities.map((cap) => (
                  <li key={cap}>
                    <StatusBadge label={cap} tone="neutral" />
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-zinc-500">No capabilities returned.</p>
            )}
          </AdminPanel>

          <div className="grid gap-4 lg:grid-cols-2">
            <AdminPanel
              title="Audit pulse"
              headingAs="h2"
              description="Denied operator actions in the recent window."
              right={
                <Link
                  to={audit?.investigate_path || '/admin/audit?outcome=denied'}
                  className="text-sm font-medium text-teal-700 underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600 dark:text-teal-400"
                >
                  Open denied in Audit →
                </Link>
              }
            >
              <MetricTile
                label={`Denied (${audit?.window_hours ?? 24}h)`}
                value={audit?.denied_available ? audit.denied_count : null}
                availability={audit?.denied_available ? 'ok' : 'unavailable'}
                hint={audit?.denied_available ? audit.since || undefined : audit?.reason}
              />
            </AdminPanel>

            <AdminPanel
              title="Sync queue pulse"
              headingAs="h2"
              description="Cross-tenant Gmail sync jobs in actionable or in-flight states."
              right={
                <a
                  href="#failed-syncs"
                  className="text-sm font-medium text-teal-700 underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600 dark:text-teal-400"
                >
                  Jump to inbox →
                </a>
              }
            >
              <div className="grid gap-3 sm:grid-cols-2">
                <MetricTile
                  label="Failed"
                  value={sync?.available ? sync.failed : null}
                  availability={sync?.available ? 'ok' : 'unavailable'}
                />
                <MetricTile
                  label="Retrying"
                  value={sync?.available ? sync.retrying : null}
                  availability={sync?.available ? 'ok' : 'unavailable'}
                />
                <MetricTile
                  label="Pending"
                  value={sync?.available ? sync.pending : null}
                  availability={sync?.available ? 'ok' : 'unavailable'}
                />
                <MetricTile
                  label="Processing"
                  value={sync?.available ? sync.processing : null}
                  availability={sync?.available ? 'ok' : 'unavailable'}
                />
              </div>
            </AdminPanel>
          </div>

          <AdminPanel
            id="failed-syncs"
            title="Failed sync inbox"
            headingAs="h2"
            description="Actionable Gmail sync jobs across tenants. Open the dossier to retry."
          >
            {syncInboxError ? <p className="text-sm text-zinc-500">{syncInboxError}</p> : null}
            {!syncInboxError && syncInbox.length === 0 ? (
              <p className="text-sm text-zinc-500">No failed or retrying sync jobs.</p>
            ) : null}
            {syncInbox.length > 0 ? (
              <div className="overflow-x-auto rounded-lg border border-zinc-200 dark:border-zinc-800">
                <table className="min-w-full text-sm">
                  <thead className="border-b border-zinc-100 bg-zinc-50 text-left text-xs font-medium uppercase tracking-wide text-zinc-500 dark:border-zinc-800 dark:bg-zinc-950">
                    <tr>
                      <th className="px-3 py-2">Tenant</th>
                      <th className="px-3 py-2">Status</th>
                      <th className="px-3 py-2">Job</th>
                      <th className="px-3 py-2">When</th>
                      <th className="px-3 py-2">Error</th>
                      <th className="px-3 py-2">Dossier</th>
                    </tr>
                  </thead>
                  <tbody>
                    {syncInbox.map((job) => (
                      <tr
                        key={`${job.tenant_id}-${job.job_id}`}
                        className="border-t border-zinc-100 dark:border-zinc-800"
                      >
                        <td className="max-w-[12rem] break-words px-3 py-2">
                          {job.business_name ||
                            job.tenant_name ||
                            job.tenant_email ||
                            `#${job.tenant_id}`}
                        </td>
                        <td className="px-3 py-2">
                          <StatusBadge
                            label={String(job.status || '—')}
                            tone={String(job.status).toLowerCase() === 'failed' ? 'bad' : 'warn'}
                          />
                        </td>
                        <td className="max-w-[10rem] break-all px-3 py-2 font-mono text-xs">
                          {job.job_id}
                        </td>
                        <td className="whitespace-nowrap px-3 py-2 text-zinc-600 dark:text-zinc-300">
                          {job.created_at || '—'}
                        </td>
                        <td className="max-w-[14rem] break-words px-3 py-2 text-zinc-600 dark:text-zinc-300">
                          {job.error_message || '—'}
                        </td>
                        <td className="px-3 py-2">
                          {job.dossier_path ? (
                            <Link
                              to={job.dossier_path}
                              className="font-medium text-teal-700 underline-offset-2 hover:underline dark:text-teal-400"
                            >
                              Open →
                            </Link>
                          ) : (
                            '—'
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
            {syncInboxTotal > syncInbox.length ? (
              <p className="mt-2 text-xs text-zinc-500">
                Showing {syncInbox.length} of {syncInboxTotal}. Open tenant dossiers for the rest.
              </p>
            ) : null}
          </AdminPanel>

          <AdminPanel
            title="Analytics pipeline"
            headingAs="h2"
            description="Platform analytics gate only. Per-tenant reconciliation stays on the dossier."
            right={
              <StatusBadge
                label={analytics?.state || 'unknown'}
                tone={analyticsTone(analytics?.state || 'unknown')}
              />
            }
          >
            <div className="grid gap-3 sm:grid-cols-3">
              <MetricTile label="Enabled" value={boolLabel(analytics?.enabled)} />
              <MetricTile label="Tables available" value={boolLabel(analytics?.tables_available)} />
              <MetricTile label="State" value={analytics?.state || '—'} />
            </div>
          </AdminPanel>
        </>
      ) : null}

      <AdminPanel title="Jump to" headingAs="h2" description="Primary operator workflows.">
        <div className="grid gap-3 md:grid-cols-3">
          {destinations.map((item) => {
            const Icon = item.icon
            return (
              <Link
                key={item.to}
                to={item.to}
                className="group flex h-full flex-col rounded-lg border border-zinc-200 bg-zinc-50/60 p-4 transition hover:border-teal-400 hover:bg-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600 dark:border-zinc-800 dark:bg-zinc-950/40 dark:hover:border-teal-700 dark:hover:bg-zinc-900"
              >
                <div className="flex items-center gap-2">
                  <Icon
                    className="h-4 w-4 shrink-0 text-teal-700 dark:text-teal-400"
                    aria-hidden
                  />
                  <h3 className="font-semibold tracking-tight text-zinc-900 group-hover:text-teal-900 dark:text-zinc-50 dark:group-hover:text-teal-100">
                    {item.title}
                  </h3>
                </div>
                <p className="mt-2 flex-1 text-sm text-zinc-600 dark:text-zinc-300">
                  {item.description}
                </p>
                <span className="mt-3 text-xs font-medium text-teal-700 dark:text-teal-400">
                  Open →
                </span>
              </Link>
            )
          })}
        </div>
      </AdminPanel>
    </div>
  )
}
