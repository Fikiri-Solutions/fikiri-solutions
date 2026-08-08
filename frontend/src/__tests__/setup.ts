import { expect, afterEach, beforeEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import * as matchers from '@testing-library/jest-dom/matchers'

// Extend Vitest's expect with jest-dom matchers
expect.extend(matchers)

// Setup localStorage mock before each test
beforeEach(() => {
  // Clear localStorage before each test
  if (typeof localStorage !== 'undefined') {
    localStorage.clear()
  }
})

// Cleanup after each test case
afterEach(() => {
  cleanup()
  if (typeof localStorage !== 'undefined') {
    localStorage.clear()
  }
})

// Mock window.matchMedia for dark mode tests
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // Deprecated
    removeListener: vi.fn(), // Deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock IntersectionObserver (must be constructable — Framer Motion uses `new`)
class MockIntersectionObserver implements IntersectionObserver {
  readonly root: Element | Document | null = null
  readonly rootMargin = ''
  readonly thresholds: ReadonlyArray<number> = []
  observe = vi.fn()
  unobserve = vi.fn()
  disconnect = vi.fn()
  takeRecords = vi.fn(() => [] as IntersectionObserverEntry[])
  constructor(_callback?: IntersectionObserverCallback, _options?: IntersectionObserverInit) {}
}
global.IntersectionObserver = MockIntersectionObserver as unknown as typeof IntersectionObserver

// Mock ResizeObserver (must be constructable)
class MockResizeObserver implements ResizeObserver {
  observe = vi.fn()
  unobserve = vi.fn()
  disconnect = vi.fn()
  constructor(_callback?: ResizeObserverCallback) {}
}
global.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver

// Mock scrollTo
global.scrollTo = vi.fn().mockImplementation((options?: ScrollToOptions | number, y?: number) => {
  if (typeof options === 'number' && typeof y === 'number') {
    // Called with x, y coordinates
    return;
  }
  // Called with options object
  return;
})
