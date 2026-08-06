import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { TenantDetail } from '../pages/admin/TenantDetail'

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getAdminTenant: vi.fn(),
    listAdminTenantSyncJobs: vi.fn(),
    reauthenticateAdmin: vi.fn(),
    retryAdminTenantSyncJob: vi.fn(),
  },
}))

vi.mock('../hooks/usePlatformAdmin', () => ({
  usePlatformAdmin: () => ({
    startImpersonation: vi.fn(),
    showAdminNav: true,
  }),
}))

import { apiClient } from '../services/apiClient'

const baseTenant = {
  id: 9,
  email: 'tenant@example.com',
  name: 'Tenant Nine',
  is_active: true,
  email_verified: true,
  onboarding_completed: false,
  onboarding_step: 2,
  business_name: 'Acme',
  industry: 'services',
  role: 'owner',
  created_at: '2026-01-01',
  last_login: '2026-01-02',
}

describe('TenantDetail support dossier', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(apiClient.listAdminTenantSyncJobs as any).mockResolvedValue({ items: [] })
  })

  it('renders dossier sections from a complete response', async () => {
    ;(apiClient.getAdminTenant as any).mockResolvedValue({
      tenant: baseTenant,
      infrastructure: {
        gmail_connected: true,
        outlook_connected: false,
        sync_status: { sync_status: 'idle' },
        subscription: { tier: 'growth', status: 'active' },
        pending_gmail_jobs: 0,
      },
      account: { ...baseTenant, onboarding_completed: false },
      access: {
        is_active: true,
        email_verified: true,
        active_session_count: 1,
        last_login_ip: '1.2.3.4',
        last_login_user_agent: 'TestAgent',
      },
      integrations: {
        gmail: { provider: 'gmail', connected: true, state: 'connected' },
        outlook: { provider: 'outlook', connected: false, state: 'disconnected' },
        pending_job_count: 0,
        processing_job_count: 0,
        failed_job_count: 1,
        latest_sanitized_error: 'sync timeout',
        has_retryable_failed_job: true,
      },
      product_health: {
        onboarding_complete: false,
        onboarding_blockers: ['onboarding_incomplete_step_2'],
        entitlements_enabled: ['email'],
        entitlements_disabled: [],
        ai_budget: { status: 'ok', estimated_cost_usd: 1, budget_cap_usd: 10 },
        background_jobs: { failed: 1 },
      },
      commercial: { tier: 'growth', status: 'active', past_due: false },
      support_activity: [
        {
          action: 'platform.impersonate.start',
          outcome: 'success',
          timestamp: '2026-01-03',
          actor_user_id: 1,
          target_id: '9',
          correlation_id: 'abc123',
        },
      ],
      support_checklist: [
        {
          id: 'account_usable',
          label: 'Account usable',
          status: 'healthy',
          section: 'account-access',
          explanation: 'Account active and verified',
        },
        {
          id: 'email_verified',
          label: 'Email verified',
          status: 'healthy',
          section: 'account-access',
          explanation: 'Verified',
        },
      ],
      impersonation_eligibility: {
        eligible: true,
        reason_code: 'AVAILABLE',
        reason_label: 'Available after operator step-up and MFA',
      },
    })

    render(
      <MemoryRouter initialEntries={['/admin/tenants/9']}>
        <Routes>
          <Route path="/admin/tenants/:tenantId" element={<TenantDetail />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText('Support checklist')).toBeInTheDocument()
    expect(screen.getByText('Account usable')).toBeInTheDocument()
    expect(screen.getAllByText('Healthy').length).toBeGreaterThan(0)
    expect(screen.queryByText(/^pass$/i)).not.toBeInTheDocument()
    expect(screen.getByText('Account & Access')).toBeInTheDocument()
    expect(screen.getByText('Integration Health')).toBeInTheDocument()
    expect(screen.getByText('Product Health')).toBeInTheDocument()
    expect(screen.getByText('Commercial Summary')).toBeInTheDocument()
    expect(screen.getByText('Recent Support Activity')).toBeInTheDocument()
    expect(screen.getByText('View as this user')).toBeInTheDocument()
    expect(screen.getByText('platform.impersonate.start')).toBeInTheDocument()
    expect(screen.queryByText(/Suspend|Disconnect OAuth|Change plan|Refund/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/access_token|refresh_token/i)).not.toBeInTheDocument()
  })

  it('renders one canonical status per checklist item and never pass for failures present', async () => {
    ;(apiClient.getAdminTenant as any).mockResolvedValue({
      tenant: baseTenant,
      infrastructure: {
        gmail_connected: false,
        outlook_connected: false,
        sync_status: null,
        subscription: null,
        pending_gmail_jobs: 0,
      },
      integrations: {
        gmail: { provider: 'gmail', connected: false, state: 'expired' },
        outlook: { provider: 'outlook', connected: false, state: 'disconnected' },
        failed_job_count: 0,
        has_retryable_failed_job: false,
        pending_job_count: 0,
        processing_job_count: 0,
      },
      support_checklist: [
        {
          id: 'no_recent_failures',
          label: 'No recent failures',
          status: 'healthy',
          section: 'integration-health',
          explanation: 'No recent failed sync jobs',
        },
        {
          id: 'no_retryable_failed_jobs',
          label: 'No retryable failed jobs',
          status: 'not_applicable',
          section: 'sync-jobs',
          explanation: 'No retryable failed jobs',
        },
        {
          id: 'email_integration_usable',
          label: 'Email integration usable',
          status: 'blocked',
          section: 'integration-health',
          explanation: 'Gmail authorization expired',
        },
        {
          id: 'sync_job_health',
          label: 'Sync job health',
          status: 'unknown',
          section: 'sync-jobs',
          explanation: 'placeholder',
        },
      ],
    })

    render(
      <MemoryRouter initialEntries={['/admin/tenants/9']}>
        <Routes>
          <Route path="/admin/tenants/:tenantId" element={<TenantDetail />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText('No recent failures')).toBeInTheDocument()
    expect(screen.queryByText(/Recent failures present/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/^pass$/i)).not.toBeInTheDocument()
    expect(screen.getAllByText('Blocked').length).toBeGreaterThan(0)
    expect(screen.getAllByText('N/A').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Unknown').length).toBeGreaterThan(0)
    expect(screen.getByText('Gmail authorization expired')).toBeInTheDocument()
    expect(screen.queryByText(/Retryable failed jobs present/i)).not.toBeInTheDocument()
  })

  it('disables View as this user for inactive tenants with server reason', async () => {
    ;(apiClient.getAdminTenant as any).mockResolvedValue({
      tenant: { ...baseTenant, is_active: false, email_verified: false },
      infrastructure: {
        gmail_connected: false,
        outlook_connected: false,
        sync_status: null,
        subscription: null,
        pending_gmail_jobs: 0,
      },
      impersonation_eligibility: {
        eligible: false,
        reason_code: 'USER_INACTIVE',
        reason_label: 'Account inactive',
      },
      support_checklist: [
        {
          id: 'impersonation_available',
          label: 'Impersonation available',
          status: 'blocked',
          section: 'support-actions',
          explanation: 'Account inactive',
        },
      ],
    })

    render(
      <MemoryRouter initialEntries={['/admin/tenants/9']}>
        <Routes>
          <Route path="/admin/tenants/:tenantId" element={<TenantDetail />} />
        </Routes>
      </MemoryRouter>,
    )

    const button = await screen.findByRole('button', { name: /View as this user unavailable/i })
    expect(button).toBeDisabled()
    expect(screen.getAllByText('Account inactive').length).toBeGreaterThan(0)
  })

  it('checklist anchors navigate to dossier sections', async () => {
    const user = userEvent.setup()
    const scrollIntoView = vi.fn()
    Element.prototype.scrollIntoView = scrollIntoView

    ;(apiClient.getAdminTenant as any).mockResolvedValue({
      tenant: baseTenant,
      infrastructure: {
        gmail_connected: true,
        outlook_connected: false,
        sync_status: null,
        subscription: null,
        pending_gmail_jobs: 0,
      },
      support_checklist: [
        {
          id: 'email_integration_usable',
          label: 'Email integration usable',
          status: 'blocked',
          section: 'integration-health',
          explanation: 'Gmail authorization expired',
        },
      ],
    })

    render(
      <MemoryRouter initialEntries={['/admin/tenants/9']}>
        <Routes>
          <Route path="/admin/tenants/:tenantId" element={<TenantDetail />} />
        </Routes>
      </MemoryRouter>,
    )

    await user.click(await screen.findByRole('button', { name: /Email integration usable/i }))
    expect(scrollIntoView).toHaveBeenCalled()
  })

  it('renders partial data and unknown values without crashing', async () => {
    ;(apiClient.getAdminTenant as any).mockResolvedValue({
      tenant: baseTenant,
      infrastructure: {
        gmail_connected: false,
        outlook_connected: false,
        sync_status: null,
        subscription: null,
        pending_gmail_jobs: 0,
      },
    })

    render(
      <MemoryRouter initialEntries={['/admin/tenants/9']}>
        <Routes>
          <Route path="/admin/tenants/:tenantId" element={<TenantDetail />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText('Account & Access')).toBeInTheDocument()
    expect(screen.getAllByText('Unknown').length).toBeGreaterThan(0)
    expect(screen.getByText('View as this user')).toBeInTheDocument()
  })

  it('keeps failed sync retry affordance when jobs are retryable', async () => {
    ;(apiClient.getAdminTenant as any).mockResolvedValue({
      tenant: baseTenant,
      infrastructure: {
        gmail_connected: true,
        outlook_connected: false,
        sync_status: null,
        subscription: null,
        pending_gmail_jobs: 0,
      },
    })
    ;(apiClient.listAdminTenantSyncJobs as any).mockResolvedValue({
      items: [{ job_id: 'job-1', status: 'failed', error_message: 'boom', retryable: true }],
    })

    render(
      <MemoryRouter initialEntries={['/admin/tenants/9']}>
        <Routes>
          <Route path="/admin/tenants/:tenantId" element={<TenantDetail />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText('Retry failed sync')).toBeInTheDocument()
  })

  it('renders customer success sections and disabled analytics copy', async () => {
    ;(apiClient.getAdminTenant as any).mockResolvedValue({
      tenant: baseTenant,
      infrastructure: {
        gmail_connected: true,
        outlook_connected: false,
        sync_status: null,
        subscription: null,
        pending_gmail_jobs: 0,
      },
      analytics_state: { status: 'disabled', coverage: 'none' },
      customer_health: {
        status: 'unknown',
        reasons: [{ code: 'ANALYTICS_DISABLED', detail: 'Product analytics disabled — not zero usage' }],
        recommended_focus: 'Enable analytics to collect adoption evidence',
      },
      usage_adoption: {
        lookback_days: 30,
        sessions: null,
        analytics_state: { status: 'disabled' },
      },
      friction_experience: { signals: [] },
      customer_outcomes: { leads_captured: 2, notes: 'Counts from authoritative CRM/sync tables; not estimated.' },
    })

    render(
      <MemoryRouter initialEntries={['/admin/tenants/9']}>
        <Routes>
          <Route path="/admin/tenants/:tenantId" element={<TenantDetail />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText('Customer Success')).toBeInTheDocument()
    expect(screen.getByText(/not the same as zero/i)).toBeInTheDocument()
    expect(screen.getByText(/ANALYTICS_DISABLED/)).toBeInTheDocument()
    expect(screen.getByText('Customer outcomes')).toBeInTheDocument()
    expect(screen.getByText('Disabled')).toBeInTheDocument()
    // Glance omits duplicate CRM counts when Customer outcomes is present
    expect(screen.getAllByText('Leads captured').length).toBeGreaterThan(0)
    expect(screen.getAllByText('2').length).toBeGreaterThan(0)
    expect(screen.queryByText(/Suspend|Disconnect OAuth|Change plan|Refund/i)).not.toBeInTheDocument()
  })

  it('does not offer retry for non-retryable jobs', async () => {
    ;(apiClient.getAdminTenant as any).mockResolvedValue({
      tenant: baseTenant,
      infrastructure: {
        gmail_connected: true,
        outlook_connected: false,
        sync_status: null,
        subscription: null,
        pending_gmail_jobs: 0,
      },
    })
    ;(apiClient.listAdminTenantSyncJobs as any).mockResolvedValue({
      items: [{ job_id: 'job-ok', status: 'completed', retryable: false }],
    })

    render(
      <MemoryRouter initialEntries={['/admin/tenants/9']}>
        <Routes>
          <Route path="/admin/tenants/:tenantId" element={<TenantDetail />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText('job-ok')).toBeInTheDocument()
    expect(screen.queryByText('Retry failed sync')).not.toBeInTheDocument()
  })
})
