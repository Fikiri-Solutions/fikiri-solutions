import { describe, expect, it, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { AdminAuditLog } from '../pages/admin/AdminAuditLog'
import {
  auditCopySummaryLine,
  buildAuditCopySummary,
  buildAuditDetailFields,
  controlledReasonCode,
} from '../pages/admin/adminAuditSanitize'

vi.mock('../services/apiClient', () => ({
  apiClient: {
    listAdminAudit: vi.fn(),
  },
}))

import { apiClient } from '../services/apiClient'

const sampleItem = {
  id: 1,
  actor_user_id: 9,
  action: 'admin.session.revoked',
  target_type: 'user',
  target_id: '5',
  outcome: 'success',
  capability: 'platform.audit.read',
  correlation_id: 'corr-abcdefghijklmnop',
  ip_address: '203.0.113.10',
  metadata: {
    reason: 'USER_INACTIVE',
    secret_blob: 'should-not-render',
  },
  before: { access_token: 'nope', status: 'active' },
  after: { refresh_token: 'nope', status: 'revoked' },
  created_at: '2026-08-02T21:00:35Z',
}

function renderAudit(path = '/admin/audit') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/admin/audit" element={<AdminAuditLog />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('adminAuditSanitize', () => {
  it('extracts controlled reason codes only', () => {
    expect(controlledReasonCode(sampleItem as any)).toBe('USER_INACTIVE')
    expect(controlledReasonCode({ metadata: { reason: 'raw prose' } } as any)).toBeNull()
  })

  it('builds detail fields without raw metadata or secret keys', () => {
    const fields = buildAuditDetailFields(sampleItem as any)
    const joined = fields.map((f) => `${f.label}:${f.value}`).join('\n')
    expect(joined).toContain('USER_INACTIVE')
    expect(joined).toContain('status=active')
    expect(joined).toContain('status=revoked')
    expect(joined).toContain('203.0.113.10')
    expect(joined).not.toContain('should-not-render')
    expect(joined).not.toContain('access_token')
    expect(joined).not.toContain('refresh_token')
    expect(joined).not.toContain('secret_blob')
  })

  it('copy summary allowlists stable fields only', () => {
    const summary = buildAuditCopySummary(sampleItem as any)
    expect(summary).toEqual({
      timestamp: '2026-08-02T21:00:35Z',
      action: 'admin.session.revoked',
      outcome: 'success',
      reason: 'USER_INACTIVE',
      actor_id: 9,
      target_type: 'user',
      target_id: '5',
      correlation_id: 'corr-abcdefghijklmnop',
      capability: 'platform.audit.read',
    })
    const line = auditCopySummaryLine(sampleItem as any)
    expect(line).not.toContain('secret_blob')
    expect(line).not.toContain('access_token')
    expect(line).not.toContain('203.0.113.10')
  })
})

describe('AdminAuditLog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    })
  })

  it('renders outcome, reason, and abbreviated correlation without raw metadata', async () => {
    ;(apiClient.listAdminAudit as any).mockResolvedValue({
      items: [sampleItem],
      total: 1,
    })

    renderAudit()

    expect(
      await screen.findByText(/Investigate platform operator and security actions/i),
    ).toBeInTheDocument()
    const table = screen.getByRole('table')
    expect(within(table).getByText('success')).toBeInTheDocument()
    expect(within(table).getByText('USER_INACTIVE')).toBeInTheDocument()
    expect(within(table).getByText('user:5')).toBeInTheDocument()
    expect(within(table).getByText(/corr-abcdefg/)).toBeInTheDocument()
    expect(screen.queryByText('should-not-render')).not.toBeInTheDocument()
    expect(screen.queryByText(/access_token|refresh_token/i)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Export filtered page/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /edit|delete|archive|move/i })).not.toBeInTheDocument()
  })

  it('does not render free-text metadata as reason codes', async () => {
    ;(apiClient.listAdminAudit as any).mockResolvedValue({
      items: [
        {
          id: 2,
          actor_user_id: 1,
          action: 'platform.x',
          outcome: 'denied',
          metadata: { reason: 'raw prose leak' },
          created_at: '2026-08-02',
        },
      ],
      total: 1,
    })

    renderAudit()
    expect(await screen.findByText('denied')).toBeInTheDocument()
    expect(screen.queryByText('raw prose leak')).not.toBeInTheDocument()
  })

  it('sends server filter params and resets offset when applying filters', async () => {
    ;(apiClient.listAdminAudit as any).mockResolvedValue({ items: [], total: 0 })

    renderAudit('/admin/audit?offset=50')

    await screen.findByText(/No audit events match these filters/i)

    fireEvent.change(screen.getByLabelText('Outcome'), { target: { value: 'denied' } })
    fireEvent.change(screen.getByLabelText('Actor user ID'), { target: { value: '9' } })
    fireEvent.change(screen.getByLabelText('Target type'), { target: { value: 'user' } })
    fireEvent.change(screen.getByLabelText('Target ID'), { target: { value: '5' } })
    fireEvent.click(screen.getByRole('button', { name: 'Apply filters' }))

    await waitFor(() => {
      expect(apiClient.listAdminAudit).toHaveBeenCalledWith(
        expect.objectContaining({
          limit: 50,
          offset: 0,
          outcome: 'denied',
          actor_user_id: 9,
          target_type: 'user',
          target_id: '5',
        }),
      )
    })
  })

  it('restores safe filters from the URL', async () => {
    ;(apiClient.listAdminAudit as any).mockResolvedValue({ items: [], total: 0 })

    renderAudit('/admin/audit?outcome=error&actor=3&target_type=tenant&target_id=12')

    await waitFor(() => {
      expect(apiClient.listAdminAudit).toHaveBeenCalledWith(
        expect.objectContaining({
          outcome: 'error',
          actor_user_id: 3,
          target_type: 'tenant',
          target_id: '12',
          offset: 0,
        }),
      )
    })
    expect(screen.getByLabelText('Outcome')).toHaveValue('error')
    expect(screen.getByLabelText('Actor user ID')).toHaveValue('3')
  })

  it('opens a sanitized detail drawer and copies allowlisted values', async () => {
    ;(apiClient.listAdminAudit as any).mockResolvedValue({
      items: [sampleItem],
      total: 1,
    })

    renderAudit()
    fireEvent.click(await screen.findByRole('button', { name: 'View' }))

    const dialog = await screen.findByRole('dialog', { name: /Event details/i })
    expect(within(dialog).getByText('corr-abcdefghijklmnop')).toBeInTheDocument()
    expect(within(dialog).getByText('USER_INACTIVE')).toBeInTheDocument()
    expect(within(dialog).queryByText('should-not-render')).not.toBeInTheDocument()
    expect(within(dialog).queryByText(/access_token/i)).not.toBeInTheDocument()

    fireEvent.click(within(dialog).getByRole('button', { name: 'Copy correlation ID' }))
    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('corr-abcdefghijklmnop')
    })
    expect(await screen.findByText('Correlation ID copied')).toBeInTheDocument()

    fireEvent.click(within(dialog).getByRole('button', { name: 'Copy sanitized summary' }))
    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        expect.stringContaining('"correlation_id":"corr-abcdefghijklmnop"'),
      )
    })
    const copied = (navigator.clipboard.writeText as any).mock.calls.at(-1)[0] as string
    expect(copied).not.toContain('secret_blob')
    expect(copied).not.toContain('203.0.113.10')
  })

  it('hides correlation copy when ID is missing and handles clipboard failure', async () => {
    ;(apiClient.listAdminAudit as any).mockResolvedValue({
      items: [{ ...sampleItem, correlation_id: null }],
      total: 1,
    })
    ;(navigator.clipboard.writeText as any).mockRejectedValue(new Error('denied'))

    renderAudit()
    fireEvent.click(await screen.findByRole('button', { name: 'View' }))
    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).queryByRole('button', { name: 'Copy correlation ID' })).not.toBeInTheDocument()

    fireEvent.click(within(dialog).getByRole('button', { name: 'Copy sanitized summary' }))
    expect(await screen.findByText(/Could not copy event summary/i)).toBeInTheDocument()
  })

  it('closes the drawer with Escape and preserves filters', async () => {
    ;(apiClient.listAdminAudit as any).mockResolvedValue({
      items: [sampleItem],
      total: 1,
    })

    renderAudit('/admin/audit?outcome=success&actor=9')
    fireEvent.click(await screen.findByRole('button', { name: 'View' }))
    expect(await screen.findByRole('dialog')).toBeInTheDocument()

    fireEvent.keyDown(window, { key: 'Escape' })
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
    expect(screen.getByLabelText('Outcome')).toHaveValue('success')
    expect(screen.getByLabelText('Actor user ID')).toHaveValue('9')
  })
})
