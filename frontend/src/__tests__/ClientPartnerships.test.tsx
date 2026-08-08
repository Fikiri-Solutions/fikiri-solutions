import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { render, screen } from '@testing-library/react'
import { ClientPartnerships } from '../components/radiant/ClientPartnerships'
import { clientPartnerships } from '../lib/clientPartnerships'

vi.mock('framer-motion', async () => {
  const actual = await vi.importActual<typeof import('framer-motion')>('framer-motion')
  return {
    ...actual,
    useReducedMotion: () => false,
  }
})

function mockMatchMedia() {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
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
    mockMatchMedia()
  })

  afterEach(() => {
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
    expect(screen.queryByText(/7-day free trial/i)).not.toBeInTheDocument()
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

  it('renders an RTL conveyor carousel region', () => {
    renderSection()

    const region = screen.getByRole('region', { name: /client partnership cards/i })
    expect(region).toBeInTheDocument()
    expect(region).toHaveAttribute('aria-roledescription', 'carousel')

    // Visible track duplicates cards for seamless looping
    expect(screen.getAllByRole('heading', { name: clientPartnerships[0].name }).length).toBeGreaterThanOrEqual(1)
    expect(document.querySelector('.fikiri-partnerships-track')).toBeTruthy()
    expect(screen.getByRole('button', { name: /pause carousel/i })).toBeInTheDocument()
  })

  it('renders local logo images for partnership cards', () => {
    renderSection()

    const first = clientPartnerships[0]
    expect(first.logoSrc).toBeTruthy()
    expect(first.logoSrc).not.toMatch(/^https?:\/\//)
    const logos = screen.getAllByRole('img', { name: first.logoAlt })
    expect(logos.length).toBeGreaterThan(0)
    expect(logos[0]).toHaveAttribute('src', first.logoSrc)
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
