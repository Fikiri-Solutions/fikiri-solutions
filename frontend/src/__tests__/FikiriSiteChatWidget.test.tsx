import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { FikiriSiteChatWidget } from '../components/FikiriSiteChatWidget'
import * as siteChatApi from '../services/siteChatApi'

vi.mock('../services/siteChatApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../services/siteChatApi')>()
  return {
    ...actual,
    startSiteChatSession: vi.fn(),
    sendSiteChatMessage: vi.fn(),
  }
})

function renderWidget() {
  return render(
    <MemoryRouter>
      <FikiriSiteChatWidget />
    </MemoryRouter>
  )
}

describe('FikiriSiteChatWidget', () => {
  beforeEach(() => {
    vi.mocked(siteChatApi.startSiteChatSession).mockResolvedValue({
      schema_version: 'v1',
      session_id: 'site_test',
      welcome: 'Welcome from Fikiri.',
    })
    vi.mocked(siteChatApi.sendSiteChatMessage).mockResolvedValue({
      schema_version: 'v1',
      session_id: 'site_test',
      mode: 'answer',
      response: 'Starter is $49 per month.',
      handoff: { applicable: true, secondary: '/contact', handoff_type: 'contact' },
      lead_intent: { signals: ['product_interest'], capture_ready: false },
      lead_assessment: {
        score: 1,
        tier: 'casual',
        signals: ['pricing_interest'],
        synopsis: 'Visitor asked about pricing; business context not yet captured.',
        recommended_handoff: '/contact',
      },
      turn_count: 1,
      grounded: true,
      confidence: 0.8,
      sources: [{ id: 'pricing_starter', source_url: 'https://fikirisolutions.com/pricing' }],
    })
  })

  it('renders launcher button', () => {
    renderWidget()
    expect(screen.getByLabelText('Open Fikiri assistant')).toBeInTheDocument()
  })

  it('shows copy transcript control in dev', async () => {
    renderWidget()
    fireEvent.click(screen.getByLabelText('Open Fikiri assistant'))
    await waitFor(() => {
      expect(screen.getByLabelText('Copy chat transcript')).toBeInTheDocument()
    })
  })

  it('starts session and sends a message', async () => {
    renderWidget()
    fireEvent.click(screen.getByLabelText('Open Fikiri assistant'))

    await waitFor(() => {
      expect(siteChatApi.startSiteChatSession).toHaveBeenCalled()
      expect(screen.getByText('Welcome from Fikiri.')).toBeInTheDocument()
      expect(screen.getByText('Pricing')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: 'Pricing' }))

    await waitFor(() => {
      expect(siteChatApi.sendSiteChatMessage).toHaveBeenCalledWith('site_test', 'What does Fikiri cost?')
      expect(screen.getByText('Starter is $49 per month.')).toBeInTheDocument()
      expect(screen.getByText('Grounded in site content')).toBeInTheDocument()
      expect(screen.getByRole('link', { name: 'Contact us' })).toHaveAttribute('href', '/contact')
    })
  })

  it('copy transcript includes lead assessment metadata', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText } })

    renderWidget()
    fireEvent.click(screen.getByLabelText('Open Fikiri assistant'))
    await waitFor(() => screen.getByText('Welcome from Fikiri.'))

    fireEvent.click(screen.getByRole('button', { name: 'Pricing' }))
    await waitFor(() => screen.getByText('Starter is $49 per month.'))

    fireEvent.click(screen.getByLabelText('Copy chat transcript'))
    await waitFor(() => {
      expect(writeText).toHaveBeenCalled()
      const copied = String(writeText.mock.calls[0][0])
      expect(copied).toContain('lead_assessment:')
      expect(copied).toContain('lead_synopsis:')
    })
  })
})
