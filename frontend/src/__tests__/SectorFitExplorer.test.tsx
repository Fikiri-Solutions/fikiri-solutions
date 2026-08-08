import { describe, expect, it, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SectorFitExplorer } from '../components/SectorFitExplorer'
import { MAX_RAW_INPUT_CHARS } from '../lib/aboutSectorMatch'
import {
  _resetSectorFitAnalyticsForTests,
  _setSectorFitAnalyticsTrackForTests,
} from '../lib/sectorFitAnalytics'

function renderExplorer() {
  return render(
    <MemoryRouter>
      <SectorFitExplorer />
    </MemoryRouter>
  )
}

describe('SectorFitExplorer', () => {
  beforeEach(() => {
    _resetSectorFitAnalyticsForTests()
    _setSectorFitAnalyticsTrackForTests(() => {})
  })
  it('shows idle invitation copy', () => {
    renderExplorer()
    expect(screen.getByRole('textbox', { name: /tell us what your business does/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /talk to us/i })).toHaveAttribute('href', '/contact')
    expect(screen.getByText(/enter a business type/i)).toBeInTheDocument()
  })

  it('matches an example chip and shows sector features', async () => {
    const user = userEvent.setup()
    renderExplorer()
    await user.click(screen.getByRole('button', { name: /use example: landscaping and seasonal cleanup/i }))
    expect(await screen.findByText(/strong match/i)).toBeInTheDocument()
    expect(screen.getByText('Email Automation')).toBeInTheDocument()
    expect(screen.getByText('CRM Management')).toBeInTheDocument()
    expect(screen.getByText('AI Assistant')).toBeInTheDocument()
  })

  it('shows invalid guidance for keyboard mash without features', async () => {
    const user = userEvent.setup()
    renderExplorer()
    await user.type(screen.getByRole('textbox', { name: /tell us what your business does/i }), 'asdfghjkl')
    expect(await screen.findAllByText(/clearer business description/i)).not.toHaveLength(0)
    expect(screen.queryByText('Email Automation')).not.toBeInTheDocument()
  })

  it('shows follow-up for insufficient detail', async () => {
    const user = userEvent.setup()
    renderExplorer()
    await user.type(screen.getByRole('textbox', { name: /tell us what your business does/i }), 'my company')
    expect(await screen.findByText(/tell us a bit more/i)).toBeInTheDocument()
  })

  it('clears input with the clear button', async () => {
    const user = userEvent.setup()
    renderExplorer()
    const input = screen.getByRole('textbox', { name: /tell us what your business does/i })
    await user.type(input, 'HVAC')
    expect(await screen.findByText(/strong match/i)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /clear business description/i }))
    expect(input).toHaveValue('')
    expect(screen.getByText(/enter a business type/i)).toBeInTheDocument()
  })

  it('enforces max length on paste', async () => {
    const user = userEvent.setup()
    renderExplorer()
    const input = screen.getByRole('textbox', { name: /tell us what your business does/i })
    const oversized = `HVAC ${'x'.repeat(MAX_RAW_INPUT_CHARS)}`
    await user.click(input)
    await user.paste(oversized)
    expect((input as HTMLTextAreaElement).value.length).toBeLessThanOrEqual(MAX_RAW_INPUT_CHARS)
  })

  it('handles unicode café input', async () => {
    const user = userEvent.setup()
    renderExplorer()
    const input = screen.getByRole('textbox', { name: /tell us what your business does/i })
    await user.click(input)
    await user.paste('Café bakery')
    expect(await screen.findAllByText(/restaurants, catering/i)).not.toHaveLength(0)
  })
})
