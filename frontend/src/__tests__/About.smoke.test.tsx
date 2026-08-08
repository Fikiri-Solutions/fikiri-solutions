import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { About } from '../pages/About'

vi.mock('../components/MarketingChatWidget', () => ({
  MarketingChatWidget: () => null,
}))

vi.mock('../components/radiant/Navbar', () => ({
  Navbar: () => <nav data-testid="navbar">Navbar</nav>,
}))

vi.mock('../components/radiant', async () => {
  const actual = await vi.importActual<typeof import('../components/radiant')>('../components/radiant')
  return {
    ...actual,
    Navbar: () => <nav data-testid="navbar">Navbar</nav>,
    AnimatedBackground: () => null,
    MarketingBackdrop: () => null,
  }
})

function renderAbout() {
  return render(
    <MemoryRouter initialEntries={['/about']}>
      <Routes>
        <Route path="/about" element={<About />} />
        <Route path="/intake" element={<div>Intake page</div>} />
        <Route path="/pricing" element={<div>Pricing page</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('About page narrative smoke', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the why-Fikiri hero', () => {
    renderAbout()
    expect(
      screen.getByRole('heading', {
        name: /we build systems around how your business actually works/i,
      })
    ).toBeInTheDocument()
    expect(
      screen.getByText(/fikiri solutions starts with the workflow, not the software/i)
    ).toBeInTheDocument()
  })

  it('renders how we work process steps', () => {
    renderAbout()
    expect(screen.getByRole('heading', { name: /how we work/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /understand the workflow/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /find the friction/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /build around the business/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /refine and hand off/i })).toBeInTheDocument()
  })

  it('keeps capability cards after the process section', async () => {
    const user = userEvent.setup()
    renderAbout()
    expect(
      screen.getByRole('heading', { name: /the systems we build around that process/i })
    ).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /email automation/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /crm management/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /ai assistant/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /email automation/i }))
    expect(screen.getByText(/classify and route messages/i)).toBeInTheDocument()
  })

  it('renders principles and practice flows', () => {
    renderAbout()
    expect(screen.getByRole('heading', { name: /what makes fikiri different/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /consulting before software/i })).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: /what this looks like in practice/i })
    ).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /lead follow-up/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /customer operations/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /ai-assisted work/i })).toBeInTheDocument()
  })

  it('keeps the footer CTA and does not host Sector Fit', () => {
    renderAbout()
    expect(screen.getByRole('heading', { name: /ready to map your workflow/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /start a workflow conversation/i })).toHaveAttribute(
      'href',
      '/intake'
    )
    expect(screen.getByRole('link', { name: /see pricing/i })).toHaveAttribute('href', '/pricing')

    expect(
      screen.queryByRole('heading', { name: /see how fikiri fits your sector/i })
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('textbox', { name: /tell us what your business does/i })
    ).not.toBeInTheDocument()
    expect(screen.queryByText(/business information/i)).not.toBeInTheDocument()
  })
})
