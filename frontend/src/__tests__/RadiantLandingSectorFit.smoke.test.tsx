import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { HelmetProvider } from 'react-helmet-async'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import RadiantLandingPage from '../pages/RadiantLandingPage'
import { About } from '../pages/About'
import {
  _resetSectorFitAnalyticsForTests,
  _setSectorFitAnalyticsTrackForTests,
} from '../lib/sectorFitAnalytics'

vi.mock('../components/MarketingChatWidget', () => ({
  MarketingChatWidget: () => null,
}))

vi.mock('../components/radiant/Navbar', () => ({
  Navbar: () => <nav data-testid="navbar">Navbar</nav>,
}))

/** Hero entrance is covered by FikiriHeroEntrance tests — keep this suite on Sector Fit only. */
vi.mock('../components/radiant/FikiriHeroVisual', () => ({
  HERO_SEEN_SESSION_KEY: 'fikiri-hero-seen',
  useHeroEntrance: () => ({ entered: true, instant: true }),
  FikiriHeroVisual: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="fikiri-hero-visual">{children}</div>
  ),
  FikiriHeroBrandBlock: () => <div data-testid="fikiri-hero-brand">FIKIRI</div>,
  FikiriHeroSectorSettle: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="fikiri-hero-sector">{children}</div>
  ),
}))

vi.mock('../components/radiant', async () => {
  const actual = await vi.importActual<typeof import('../components/radiant')>('../components/radiant')
  return {
    ...actual,
    Navbar: () => <nav data-testid="navbar">Navbar</nav>,
    AnimatedBackground: () => null,
    MarketingBackdrop: () => null,
    Testimonials: () => <div data-testid="testimonials">Testimonials</div>,
    ClientPartnerships: () => <div data-testid="client-partnerships">Client Partnerships</div>,
    FikiriHeroVisual: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="fikiri-hero-visual">{children}</div>
    ),
    FikiriHeroBrandBlock: () => <div data-testid="fikiri-hero-brand">FIKIRI</div>,
    FikiriHeroSectorSettle: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="fikiri-hero-sector">{children}</div>
    ),
  }
})

function renderAt(path: string) {
  return render(
    <HelmetProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/" element={<RadiantLandingPage />} />
          <Route path="/about" element={<About />} />
          <Route path="/signup" element={<div>Signup page</div>} />
          <Route path="/pricing" element={<div>Pricing page</div>} />
          <Route path="/intake" element={<div>Intake page</div>} />
          <Route path="/contact" element={<div>Contact page</div>} />
        </Routes>
      </MemoryRouter>
    </HelmetProvider>
  )
}

function expectCta(name: RegExp, href: string) {
  const matches = screen.getAllByRole('link', { name })
  expect(matches.some((el) => el.getAttribute('href') === href)).toBe(true)
}

async function waitForExplorer() {
  return screen.findByRole(
    'textbox',
    { name: /tell us what your business does/i },
    { timeout: 8000 }
  )
}

describe('Homepage Sector Fit Explorer smoke', { timeout: 30_000 }, () => {
  beforeEach(() => {
    vi.clearAllMocks()
    _resetSectorFitAnalyticsForTests()
    _setSectorFitAnalyticsTrackForTests(() => {})
  })

  it('renders the explorer on / with signup and workflow CTAs', async () => {
    renderAt('/')
    expect(
      await screen.findByRole('heading', { name: /see how fikiri fits your sector/i })
    ).toBeInTheDocument()
    expect(await waitForExplorer()).toBeInTheDocument()
    expectCta(/^get started$/i, '/signup')
    expectCta(/start a workflow conversation/i, '/intake')
    expectCta(/see plans/i, '/pricing')
    expect(screen.getByRole('link', { name: /talk to us/i })).toHaveAttribute('href', '/contact')
  })

  it('does not render the explorer on /about', async () => {
    renderAt('/about')
    expect(
      await screen.findByRole('heading', {
        name: /we build systems around how your business actually works/i,
      })
    ).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /see how fikiri fits your sector/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('textbox', { name: /tell us what your business does/i })).not.toBeInTheDocument()
  })

  it('keeps the hero usable after invalid input', async () => {
    const user = userEvent.setup()
    const { container } = renderAt('/')
    const input = await waitForExplorer()
    await user.clear(input)
    await user.paste('asdfghjkl')
    expect(await screen.findAllByText(/clearer business description/i)).not.toHaveLength(0)
    expectCta(/^get started$/i, '/signup')
    expectCta(/start a workflow conversation/i, '/intake')
    expect(container.querySelector('.overflow-x-hidden')).toBeTruthy()
  })

  it('shows matched results without dropping surrounding CTAs', async () => {
    const user = userEvent.setup()
    renderAt('/')
    await waitForExplorer()
    await user.click(screen.getByRole('button', { name: /use example: landscaping and seasonal cleanup/i }))
    expect(await screen.findByText(/strong match/i)).toBeInTheDocument()
    expect(screen.getByText('Email Automation')).toBeInTheDocument()
    expectCta(/^get started$/i, '/signup')
    expectCta(/start a workflow conversation/i, '/intake')
  })

  it('clears the explorer without affecting page chrome', async () => {
    const user = userEvent.setup()
    renderAt('/')
    const input = await waitForExplorer()
    await user.clear(input)
    await user.paste('HVAC')
    expect(await screen.findByText(/strong match/i)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /clear business description/i }))
    expect(input).toHaveValue('')
    expect(screen.getByRole('heading', { name: /see how fikiri fits your sector/i })).toBeInTheDocument()
    expectCta(/^get started$/i, '/signup')
  })

  it('keeps Talk to us routed to /contact inside the explorer', async () => {
    renderAt('/')
    expect(await screen.findByRole('link', { name: /talk to us/i })).toHaveAttribute('href', '/contact')
  })
})
