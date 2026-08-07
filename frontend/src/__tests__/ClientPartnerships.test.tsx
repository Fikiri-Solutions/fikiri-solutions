import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { act, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ClientPartnerships } from '../components/radiant/ClientPartnerships'
import { clientPartnerships } from '../lib/clientPartnerships'

vi.mock('framer-motion', async () => {
  const actual = await vi.importActual<typeof import('framer-motion')>('framer-motion')
  return {
    ...actual,
    useReducedMotion: () => false,
  }
})

function mockMatchMedia(matchesDesktop: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: Boolean(matchesDesktop && query.includes('min-width: 768px')),
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  })
}

function renderSection() {
  return render(
    <MemoryRouter>
      <ClientPartnerships />
    </MemoryRouter>
  )
}

describe('ClientPartnerships', () => {
  beforeEach(() => {
    mockMatchMedia(false)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('renders honest partnership copy without fake testimonials', () => {
    renderSection()

    expect(screen.getByText('Client Partnerships')).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: /real client work across different industries/i })
    ).toBeInTheDocument()
    expect(
      screen.getByText(/fikiri starts with consulting and workflow discovery/i)
    ).toBeInTheDocument()

    expect(screen.queryByText(/trusted by/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/sarah m\./i)).not.toBeInTheDocument()
    expect(screen.queryByText(/james k\./i)).not.toBeInTheDocument()
    expect(screen.queryByText(/priya l\./i)).not.toBeInTheDocument()
  })

  it('exposes all four real clients with visit links and intake CTA', () => {
    renderSection()

    for (const client of clientPartnerships) {
      expect(
        screen.getByRole('link', { name: new RegExp(`${client.name} — Visit site`, 'i') })
      ).toHaveAttribute('href', client.url)
    }

    expect(screen.getByRole('link', { name: /start a workflow conversation/i })).toHaveAttribute(
      'href',
      '/intake'
    )
  })

  it('renders carousel controls and advances slides with next/previous', async () => {
    const user = userEvent.setup()
    renderSection()

    const region = screen.getByRole('region', { name: /client partnership cards/i })
    const next = screen.getByRole('button', { name: /next client partnership/i })
    const prev = screen.getByRole('button', { name: /previous client partnership/i })

    expect(within(region).getByRole('heading', { name: clientPartnerships[0].name })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: clientPartnerships[1].name })).not.toBeInTheDocument()

    await user.click(next)
    expect(await within(region).findByRole('heading', { name: clientPartnerships[1].name })).toBeInTheDocument()

    await user.click(prev)
    expect(await within(region).findByRole('heading', { name: clientPartnerships[0].name })).toBeInTheDocument()
  })

  it('autoplays to the next partnership when motion is allowed', async () => {
    const setIntervalSpy = vi.spyOn(window, 'setInterval')
    renderSection()

    const region = screen.getByRole('region', { name: /client partnership cards/i })
    expect(within(region).getByRole('heading', { name: clientPartnerships[0].name })).toBeInTheDocument()

    const autoplayCall = setIntervalSpy.mock.calls.find((call) => call[1] === 6000)
    expect(autoplayCall).toBeTruthy()

    act(() => {
      ;(autoplayCall![0] as TimerHandler as () => void)()
    })

    expect(
      await within(region).findByRole('heading', { name: clientPartnerships[1].name })
    ).toBeInTheDocument()
  })

  it('renders local logo images for the visible partnership slide', () => {
    renderSection()

    const first = clientPartnerships[0]
    expect(first.logoSrc).toBeTruthy()
    expect(first.logoSrc).not.toMatch(/^https?:\/\//)
    const logo = screen.getByRole('img', { name: first.logoAlt })
    expect(logo).toHaveAttribute('src', first.logoSrc)
  })
})

describe('clientPartnerships data', () => {
  it('contains exactly the four real partnerships with local logos', () => {
    expect(clientPartnerships.map((c) => c.name)).toEqual([
      'ColorScalez',
      'Symbolics Technology',
      'Shinkei Nettowaku Solutions',
      'Aim High Hit Higher Enterprise',
    ])
    for (const client of clientPartnerships) {
      expect(client.logoSrc).toMatch(/\/images\/clients\//)
      expect(client.fallbackMark.length).toBeGreaterThan(0)
    }
  })
})
