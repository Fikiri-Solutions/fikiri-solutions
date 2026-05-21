import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { LiveMailLocalBadges } from '../components/LiveMailLocalBadges'

describe('LiveMailLocalBadges', () => {
  it('renders Opportunity badge for business_lead', () => {
    render(
      <LiveMailLocalBadges
        email={{ classification_category: 'business_lead', lead_score: 70 }}
      />
    )
    expect(screen.getByText('Opportunity')).toBeInTheDocument()
    expect(screen.queryByText('Lead')).not.toBeInTheDocument()
  })

  it('renders Filed in Gmail when archived', () => {
    render(
      <LiveMailLocalBadges
        email={{
          workflow_status: 'archived',
          is_locally_archived: true,
          is_locally_handled: true,
        }}
      />
    )
    expect(screen.getByText('Filed in Gmail')).toBeInTheDocument()
  })

  it('renders Done for dismissed workflow', () => {
    render(
      <LiveMailLocalBadges
        email={{ workflow_status: 'dismissed', is_locally_handled: true }}
      />
    )
    expect(screen.getByText('Done')).toBeInTheDocument()
    expect(screen.queryByText('Dismissed')).not.toBeInTheDocument()
  })

  it('renders Needs reply for action_needed', () => {
    render(<LiveMailLocalBadges email={{ classification_category: 'action_needed' }} />)
    expect(screen.getByText('Needs reply')).toBeInTheDocument()
  })

  it('renders at most one badge', () => {
    render(
      <LiveMailLocalBadges
        email={{
          classification_category: 'business_lead',
          workflow_status: 'dismissed',
          is_locally_handled: true,
        }}
      />
    )
    expect(screen.getAllByText(/Opportunity|Done|Filed/).length).toBe(1)
  })

  it('renders nothing when no local state', () => {
    const { container } = render(<LiveMailLocalBadges email={{}} />)
    expect(container.firstChild).toBeNull()
  })
})
