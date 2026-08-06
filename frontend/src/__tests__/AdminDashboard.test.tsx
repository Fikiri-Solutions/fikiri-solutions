import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AdminDashboard } from '../pages/admin/AdminDashboard'
import type { PlatformAdminStatus } from '../types/admin'

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getPlatformAdminStatus: vi.fn(),
    listPlatformSyncJobs: vi.fn(),
  },
}))

import { apiClient } from '../services/apiClient'

const sampleStatus: PlatformAdminStatus = {
  generated_at: '2026-08-03T01:00:00Z',
  operator: {
    actor_user_id: 9,
    effective_user_id: 9,
    capabilities: ['platform.tenants.read', 'platform.audit.read'],
    security: {
      mfa_required: true,
      mfa_enrolled: true,
      step_up_active: false,
      step_up_mfa_completed: false,
      step_up_expires_at: null,
      impersonating: false,
      impersonation_disabled: false,
    },
  },
  gates: {
    lockdown: false,
    destructive_enabled: false,
  },
  audit: {
    denied_available: true,
    denied_count: 12,
    window_hours: 24,
    since: '2026-08-02T01:00:00Z',
    investigate_path: '/admin/audit?outcome=denied',
  },
  sync_jobs: {
    available: true,
    failed: 3,
    retrying: 1,
    pending: 2,
    processing: 0,
    actionable: 4,
    investigate_path: '/admin/tenants',
  },
  analytics: {
    available: true,
    enabled: false,
    tables_available: false,
    state: 'disabled',
  },
}

describe('AdminDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders platform status pulse and named capabilities', async () => {
    ;(apiClient.getPlatformAdminStatus as any).mockResolvedValue(sampleStatus)
    ;(apiClient.listPlatformSyncJobs as any).mockResolvedValue({
      available: true,
      items: [
        {
          job_id: 'job-1',
          tenant_id: 2,
          tenant_email: 'a@example.com',
          status: 'failed',
          error_message: 'token expired',
          dossier_path: '/admin/tenants/2#sync-jobs',
        },
      ],
      total: 1,
    })

    render(
      <MemoryRouter>
        <AdminDashboard />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Operator Console')).toBeInTheDocument()
    expect(screen.getAllByText('12').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('4').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('platform.tenants.read')).toBeInTheDocument()
    expect(screen.getByText('Failed sync inbox')).toBeInTheDocument()
    expect(screen.getByText('a@example.com')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open denied in Audit/i })).toHaveAttribute(
      'href',
      '/admin/audit?outcome=denied',
    )
    expect(screen.queryByRole('button', { name: /delete|archive/i })).not.toBeInTheDocument()
  })

  it('shows unavailable states without inventing zeros', async () => {
    ;(apiClient.getPlatformAdminStatus as any).mockResolvedValue({
      ...sampleStatus,
      audit: {
        ...sampleStatus.audit,
        denied_available: false,
        denied_count: null,
        reason: 'AUDIT_COUNT_UNAVAILABLE',
      },
      sync_jobs: {
        ...sampleStatus.sync_jobs,
        available: false,
        failed: null,
        retrying: null,
        pending: null,
        processing: null,
        actionable: null,
        reason: 'SYNC_JOBS_TABLE_UNAVAILABLE',
      },
    })
    ;(apiClient.listPlatformSyncJobs as any).mockResolvedValue({
      available: false,
      items: [],
      total: 0,
      reason: 'SYNC_JOBS_TABLE_UNAVAILABLE',
    })

    render(
      <MemoryRouter>
        <AdminDashboard />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Operator Console')).toBeInTheDocument()
    expect(screen.getAllByText('Unavailable').length).toBeGreaterThan(0)
    expect(screen.getAllByText('AUDIT_COUNT_UNAVAILABLE').length).toBeGreaterThan(0)
  })

  it('surfaces load failure safely', async () => {
    ;(apiClient.getPlatformAdminStatus as any).mockRejectedValue(new Error('boom'))
    ;(apiClient.listPlatformSyncJobs as any).mockResolvedValue({
      available: true,
      items: [],
      total: 0,
    })

    render(
      <MemoryRouter>
        <AdminDashboard />
      </MemoryRouter>,
    )

    expect(await screen.findByText('boom')).toBeInTheDocument()
    expect(screen.getByText('Jump to')).toBeInTheDocument()
  })
})
