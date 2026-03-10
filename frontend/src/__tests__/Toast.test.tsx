import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { renderHook, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ToastProvider, useToast } from '../components/Toast'

// Mock react-hot-toast - must define mocks inside factory
vi.mock('react-hot-toast', () => {
  const mockToast = vi.fn()
  const mockToastSuccess = vi.fn()
  const mockToastError = vi.fn()
  
  const defaultExport = Object.assign(mockToast, {
    success: mockToastSuccess,
    error: mockToastError,
  })
  
  return {
    default: defaultExport,
    Toaster: () => <div data-testid="toaster">Toaster</div>,
  }
})

// Import after mock to get the mocked version
import toast from 'react-hot-toast'

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <MemoryRouter>
    <ToastProvider>{children}</ToastProvider>
  </MemoryRouter>
)

describe('Toast Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should provide useToast hook', () => {
    const { result } = renderHook(() => useToast(), { wrapper })

    expect(result.current).toBeDefined()
    expect(result.current.addToast).toBeInstanceOf(Function)
  })

  it('should throw error when useToast is used outside provider', () => {
    // Suppress console.error for this test
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    expect(() => {
      renderHook(() => useToast())
    }).toThrow('useToast must be used within a ToastProvider')

    consoleSpy.mockRestore()
  })

  it('should show success toast', async () => {
    const { result } = renderHook(() => useToast(), { wrapper })

    await act(async () => {
      result.current.addToast({
        type: 'success',
        title: 'Success!',
        message: 'Operation completed',
      })
    })

    expect(toast).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        duration: 4000,
        position: 'top-right',
      })
    )
  })

  it('should show error toast', async () => {
    const { result } = renderHook(() => useToast(), { wrapper })

    await act(async () => {
      result.current.addToast({
        type: 'error',
        title: 'Error!',
        message: 'Something went wrong',
      })
    })

    expect(toast).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        duration: 4000,
        position: 'top-right',
      })
    )
  })

  it('should show warning toast', async () => {
    const { result } = renderHook(() => useToast(), { wrapper })

    await act(async () => {
      result.current.addToast({
        type: 'warning',
        title: 'Warning!',
        message: 'Please be careful',
      })
    })

    expect(toast).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        duration: 4000,
        position: 'top-right',
      })
    )
  })

  it('should show info toast', async () => {
    const { result } = renderHook(() => useToast(), { wrapper })

    await act(async () => {
      result.current.addToast({
        type: 'info',
        title: 'Info',
        message: 'Here is some information',
      })
    })

    expect(toast).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        duration: 4000,
        position: 'top-right',
      })
    )
  })

  it('should use custom duration when provided', async () => {
    const { result } = renderHook(() => useToast(), { wrapper })

    await act(async () => {
      result.current.addToast({
        type: 'success',
        title: 'Success!',
        duration: 5000,
      })
    })

    expect(toast).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        duration: 5000,
      })
    )
  })

  it('should handle toast without message', async () => {
    const { result } = renderHook(() => useToast(), { wrapper })

    await act(async () => {
      result.current.addToast({
        type: 'success',
        title: 'Success!',
      })
    })

    expect(toast).toHaveBeenCalledWith(
      expect.anything(),
      expect.any(Object)
    )
  })

  it('should render Toaster component', () => {
    render(
      <MemoryRouter>
        <ToastProvider>
          <div>Test</div>
        </ToastProvider>
      </MemoryRouter>
    )

    // The Toaster is mocked, but we can check if ToastProvider renders children
    expect(screen.getByText('Test')).toBeInTheDocument()
  })
})
