import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import {
  AdminPanel,
  FieldGrid,
  FieldItem,
  MetricTile,
  StatusBadge,
  checklistStatusLabel,
} from '../pages/admin/adminUi'

describe('adminUi primitives', () => {
  it('StatusBadge renders visible text for supported statuses', () => {
    const statuses = [
      'Healthy',
      'Attention',
      'Blocked',
      'Unknown',
      'N/A',
      'At risk',
    ] as const
    for (const label of statuses) {
      const { unmount } = render(<StatusBadge label={label} tone="ok" />)
      expect(screen.getByText(label)).toBeInTheDocument()
      unmount()
    }
    expect(checklistStatusLabel('not_applicable')).toBe('N/A')
    expect(checklistStatusLabel('at_risk')).toBe('At risk')
    expect(checklistStatusLabel('blocked')).toBe('Blocked')
  })

  it('MetricTile distinguishes unknown, unavailable, disabled, zero, and missing', () => {
    const { rerender } = render(
      <MetricTile label="Sessions" value={0} availability="ok" />,
    )
    expect(screen.getByText('0')).toBeInTheDocument()

    rerender(<MetricTile label="Sessions" value={null} availability="empty" />)
    expect(screen.getByText('—')).toBeInTheDocument()
    expect(screen.queryByText('0')).not.toBeInTheDocument()

    rerender(<MetricTile label="Sessions" availability="disabled" />)
    expect(screen.getByText('Disabled')).toBeInTheDocument()

    rerender(<MetricTile label="Sessions" availability="unavailable" />)
    expect(screen.getByText('Unavailable')).toBeInTheDocument()

    rerender(<MetricTile label="Sessions" availability="unknown" />)
    expect(screen.getByText('Unknown')).toBeInTheDocument()
  })

  it('MetricTile preserves estimate hint and wraps long values', () => {
    render(
      <MetricTile
        label="AI usage"
        value="$1.00 / $10.00"
        hint="Estimated"
      />,
    )
    expect(screen.getByText('Estimated')).toBeInTheDocument()
    expect(screen.getByText('$1.00 / $10.00')).toBeInTheDocument()
  })

  it('FieldGrid uses semantic dl/dt/dd and keeps long values', () => {
    const longUa =
      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 very-long-user-agent-string'
    render(
      <FieldGrid>
        <FieldItem label="Email" value="coding6887@gmail.com" />
        <FieldItem label="Last login UA" value={longUa} />
      </FieldGrid>,
    )
    expect(screen.getByText('Email').tagName).toBe('DT')
    expect(screen.getByText('coding6887@gmail.com').tagName).toBe('DD')
    expect(screen.getByText(longUa)).toBeInTheDocument()
  })

  it('AdminPanel heading level is configurable', () => {
    const { rerender } = render(
      <AdminPanel title="Account" headingAs="h2">
        <p>body</p>
      </AdminPanel>,
    )
    expect(screen.getByRole('heading', { level: 2, name: 'Account' })).toBeInTheDocument()

    rerender(
      <AdminPanel title="Account" headingAs="h3">
        <p>body</p>
      </AdminPanel>,
    )
    expect(screen.getByRole('heading', { level: 3, name: 'Account' })).toBeInTheDocument()
  })
})
