import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { LiveMailLocalBadges } from '../components/LiveMailLocalBadges'

describe('LiveMailLocalBadges', () => {
  it('renders Lead badge when classification_category is business_lead', () => {
    render(
      <LiveMailLocalBadges
        email={{ classification_category: 'business_lead', lead_score: 70 }}
      />
    )
    expect(screen.getByText('Lead')).toBeInTheDocument()
  })

  it('renders archived locally when workflow_status is archived', () => {
    render(
      <LiveMailLocalBadges
        email={{
          workflow_status: 'archived',
          is_locally_archived: true,
          is_locally_handled: true,
        }}
      />
    )
    expect(screen.getByText('Archived locally')).toBeInTheDocument()
  })

  it('renders Done and Dismissed workflow badges', () => {
    const { rerender } = render(
      <LiveMailLocalBadges email={{ workflow_status: 'done', is_locally_handled: true }} />
    )
    expect(screen.getByText('Done')).toBeInTheDocument()

    rerender(
      <LiveMailLocalBadges
        email={{ workflow_status: 'dismissed', is_locally_handled: true }}
      />
    )
    expect(screen.getByText('Dismissed')).toBeInTheDocument()
  })

  it('renders Newsletter and Action Needed category badges', () => {
    const { rerender } = render(
      <LiveMailLocalBadges email={{ classification_category: 'newsletter' }} />
    )
    expect(screen.getByText('Newsletter')).toBeInTheDocument()

    rerender(
      <LiveMailLocalBadges email={{ classification_category: 'action_needed' }} />
    )
    expect(screen.getByText('Action Needed')).toBeInTheDocument()
  })

  it('renders Handled badge when is_locally_handled without specific workflow label', () => {
    render(
      <LiveMailLocalBadges
        email={{
          workflow_status: 'converted_to_lead',
          is_locally_handled: true,
        }}
      />
    )
    expect(screen.getByText('Converted')).toBeInTheDocument()
  })

  it('renders nothing when no local state', () => {
    const { container } = render(<LiveMailLocalBadges email={{}} />)
    expect(container.firstChild).toBeNull()
  })
})
