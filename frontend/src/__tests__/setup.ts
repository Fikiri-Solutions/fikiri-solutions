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

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock scrollTo
global.scrollTo = vi.fn().mockImplementation((options?: ScrollToOptions | number, y?: number) => {
  if (typeof options === 'number' && typeof y === 'number') {
    // Called with x, y coordinates
    return;
  }
  // Called with options object
  return;
})
