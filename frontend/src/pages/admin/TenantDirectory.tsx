import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiClient } from '../../services/apiClient'
import type { AdminTenant } from '../../types/admin'
import { StatusBadge } from './adminUi'

export function TenantDirectory() {
  const [search, setSearch] = useState('')
  const [tenants, setTenants] = useState<AdminTenant[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    void apiClient
      .listAdminTenants({ search: search.trim() || undefined, limit: 50 })
      .then((result) => {
        if (!cancelled) setTenants(result.items as AdminTenant[])
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load tenants')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [search])

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Tenants</h2>
          <p className="text-sm text-zinc-600 dark:text-zinc-300">
            All client accounts on the platform.
          </p>
        </div>
        <input
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search email, name, business..."
          className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600 dark:border-zinc-700 dark:bg-zinc-900 sm:max-w-sm"
        />
      </div>

      {loading ? <p className="text-sm text-zinc-500">Loading tenants…</p> : null}
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <div className="overflow-x-auto rounded-xl border border-zinc-200/90 bg-white dark:border-zinc-800 dark:bg-zinc-900">
        <table className="min-w-full text-sm">
          <thead className="border-b border-zinc-100 bg-zinc-50 text-left text-xs font-medium uppercase tracking-wide text-zinc-500 dark:border-zinc-800 dark:bg-zinc-950">
            <tr>
              <th className="px-4 py-2.5">Account</th>
              <th className="px-4 py-2.5">Business</th>
              <th className="px-4 py-2.5">Status</th>
              <th className="px-4 py-2.5">Actions</th>
            </tr>
          </thead>
          <tbody>
            {tenants.map((tenant) => (
              <tr
                key={tenant.id}
                className="border-t border-zinc-100 hover:bg-zinc-50/80 dark:border-zinc-800 dark:hover:bg-zinc-950/50"
              >
                <td className="px-4 py-2.5">
                  <div className="font-medium text-zinc-900 dark:text-zinc-100">{tenant.name}</div>
                  <div className="break-all text-zinc-500">{tenant.email}</div>
                </td>
                <td className="px-4 py-2.5 text-zinc-700 dark:text-zinc-300">
                  {tenant.business_name || '—'}
                </td>
                <td className="px-4 py-2.5">
                  <StatusBadge
                    label={tenant.is_active ? 'Active' : 'Inactive'}
                    tone={tenant.is_active ? 'ok' : 'bad'}
                  />
                </td>
                <td className="px-4 py-2.5">
                  <Link
                    to={`/admin/tenants/${tenant.id}`}
                    className="font-medium text-teal-700 underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600 dark:text-teal-400"
                  >
                    Open
                  </Link>
                </td>
              </tr>
            ))}
            {!loading && tenants.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-zinc-500">
                  No tenants found.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  )
}
