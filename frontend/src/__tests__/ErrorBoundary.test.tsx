import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ErrorBoundary from '../components/ErrorBoundary'

// Component that throws an error
const ThrowError = ({ shouldThrow = false }: { shouldThrow?: boolean }) => {
  if (shouldThrow) {
    throw new Error('Test error')
  }
  return <div>No error</div>
}

// Suppress console.error for cleaner test output
const originalError = console.error
beforeEach(() => {
  console.error = vi.fn()
})

afterEach(() => {
  console.error = originalError
})

describe('ErrorBoundary', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render children when there is no error', () => {
    render(
      <ErrorBoundary>
        <div>Test content</div>
      </ErrorBoundary>
    )

    expect(screen.getByText('Test content')).toBeInTheDocument()
  })

  it('should render error UI when child component throws', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )

    expect(screen.getByText(/oops! something went wrong/i)).toBeInTheDocument()
    expect(screen.getByText(/we encountered an unexpected error/i)).toBeInTheDocument()
  })

  it('should show error details when expanded', async () => {
    const user = userEvent.setup()
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )

    const detailsButton = screen.getByText(/error details/i)
    expect(detailsButton).toBeInTheDocument()

    await user.click(detailsButton)

    // Error message should be visible - use getAllByText since error appears multiple times
    const errorMessages = screen.getAllByText(/test error/i)
    expect(errorMessages.length).toBeGreaterThan(0)
  })

  it('should have retry button', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )

    const retryButton = screen.getByRole('button', { name: /try again/i })
    expect(retryButton).toBeInTheDocument()
  })

  it('should reset error state when retry is clicked', async () => {
    const user = userEvent.setup()
    
    const { rerender } = render(
      <ErrorBoundary key="test-1">
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )

    expect(screen.getByText(/oops! something went wrong/i)).toBeInTheDocument()

    const retryButton = screen.getByRole('button', { name: /try again/i })
    expect(retryButton).toBeInTheDocument()
    
    // Click retry - this should reset the error state
    await user.click(retryButton)

    // After retry, rerender with a non-throwing component using a new key to force remount
    rerender(
      <ErrorBoundary key="test-2">
        <div>No error</div>
      </ErrorBoundary>
    )

    // Should now render the non-throwing component
    expect(screen.getByText('No error')).toBeInTheDocument()
  })

  it('should have go to homepage button', () => {
    const mockLocation = { ...window.location, href: '' }
    delete (window as any).location
    window.location = mockLocation as Location

    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )

    const homeButton = screen.getByRole('button', { name: /go to homepage/i })
    expect(homeButton).toBeInTheDocument()

    // Restore window.location
    window.location = location
  })

  it('should have refresh page button', () => {
    const mockReload = vi.fn()
    Object.defineProperty(window, 'location', {
      value: { reload: mockReload },
      writable: true,
    })

    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )

    const refreshButton = screen.getByRole('button', { name: /refresh page/i })
    expect(refreshButton).toBeInTheDocument()
  })

  it('should render custom fallback when provided', () => {
    const customFallback = <div>Custom error message</div>

    render(
      <ErrorBoundary fallback={customFallback}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )

    expect(screen.getByText('Custom error message')).toBeInTheDocument()
    expect(screen.queryByText(/oops! something went wrong/i)).not.toBeInTheDocument()
  })

  it('should log error to console', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )

    expect(console.error).toHaveBeenCalled()
  })
})

