import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  FikiriHeroBrandBlock,
  FikiriHeroSectorSettle,
  FikiriHeroVisual,
  HERO_SEEN_SESSION_KEY,
} from '../components/radiant/FikiriHeroVisual'

type ObserverInstance = {
  callback: IntersectionObserverCallback
  disconnect: ReturnType<typeof vi.fn>
  observe: ReturnType<typeof vi.fn>
}

let observers: ObserverInstance[] = []

function installIntersectionObserverMock() {
  observers = []
  class ControlledIntersectionObserver implements IntersectionObserver {
    readonly root: Element | Document | null = null
    readonly rootMargin = ''
    readonly thresholds: ReadonlyArray<number> = []
    observe = vi.fn()
    unobserve = vi.fn()
    disconnect = vi.fn()
    takeRecords = vi.fn(() => [] as IntersectionObserverEntry[])
    constructor(callback: IntersectionObserverCallback, _options?: IntersectionObserverInit) {
      observers.push({
        callback,
        disconnect: this.disconnect,
        observe: this.observe,
      })
    }
  }
  global.IntersectionObserver =
    ControlledIntersectionObserver as unknown as typeof IntersectionObserver
}

function fireIntersect(isIntersecting = true) {
  const entry = {
    isIntersecting,
    intersectionRatio: isIntersecting ? 0.25 : 0,
    target: document.createElement('section'),
    boundingClientRect: {} as DOMRectReadOnly,
    intersectionRect: {} as DOMRectReadOnly,
    rootBounds: null,
    time: 0,
  } as IntersectionObserverEntry

  act(() => {
    for (const observer of observers) {
      observer.callback([entry], observer as unknown as IntersectionObserver)
    }
  })
}

function setReducedMotion(matches: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: query.includes('prefers-reduced-motion') ? matches : false,
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

function renderHero() {
  return render(
    <FikiriHeroVisual>
      <FikiriHeroBrandBlock />
      <FikiriHeroSectorSettle>
        <label htmlFor="sector-fit-input">Tell us what your business does</label>
        <input id="sector-fit-input" />
      </FikiriHeroSectorSettle>
    </FikiriHeroVisual>
  )
}

describe('Fikiri hero entrance motion', { timeout: 15_000 }, () => {
  beforeEach(() => {
    sessionStorage.clear()
    setReducedMotion(false)
    installIntersectionObserverMock()
  })

  afterEach(() => {
    sessionStorage.clear()
  })

  it('renders final brand + Sector Fit after IntersectionObserver entry without scroll', () => {
    renderHero()
    const hero = screen.getByRole('region', { name: /fikiri solutions brand hero/i })
    expect(hero).toHaveAttribute('data-hero-entered', 'false')
    expect(observers).toHaveLength(1)
    expect(observers[0].observe).toHaveBeenCalled()

    fireIntersect(true)

    expect(hero).toHaveAttribute('data-hero-entered', 'true')
    expect(sessionStorage.getItem(HERO_SEEN_SESSION_KEY)).toBe('1')
    expect(screen.getByText('FIKIRI')).toBeInTheDocument()
    expect(screen.getByText(/intelligent systems for the way/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/tell us what your business does/i)).toBeEnabled()
  })

  it('disconnects the observer so entry only fires once per mount', () => {
    renderHero()
    expect(observers).toHaveLength(1)
    fireIntersect(true)
    expect(observers[0].disconnect).toHaveBeenCalled()
    expect(screen.getByRole('region', { name: /fikiri solutions brand hero/i })).toHaveAttribute(
      'data-hero-entered',
      'true'
    )
    // Still a single observer for this mount — no re-subscribe after entry
    expect(observers).toHaveLength(1)
  })

  it('skips full intro when sessionStorage already marks hero as seen', () => {
    sessionStorage.setItem(HERO_SEEN_SESSION_KEY, '1')
    renderHero()
    const hero = screen.getByRole('region', { name: /fikiri solutions brand hero/i })
    expect(hero).toHaveAttribute('data-hero-entered', 'true')
    expect(hero).toHaveAttribute('data-hero-instant', 'true')
    expect(observers).toHaveLength(0)
  })

  it('renders final state immediately when prefers-reduced-motion is set', async () => {
    setReducedMotion(true)
    renderHero()
    const hero = screen.getByRole('region', { name: /fikiri solutions brand hero/i })
    await waitFor(() => {
      expect(hero).toHaveAttribute('data-hero-entered', 'true')
      expect(hero).toHaveAttribute('data-hero-instant', 'true')
    })
    expect(observers).toHaveLength(0)
    expect(screen.getByText('FIKIRI')).toBeInTheDocument()
  })

  it('keeps Sector Fit interactive before and during the entrance sequence', async () => {
    const user = userEvent.setup()
    renderHero()
    const input = screen.getByLabelText(/tell us what your business does/i)
    expect(input).toBeEnabled()
    await user.type(input, 'cafe')
    expect(input).toHaveValue('cafe')

    fireIntersect(true)
    await user.type(input, 's')
    expect(input).toHaveValue('cafes')
  })
})
