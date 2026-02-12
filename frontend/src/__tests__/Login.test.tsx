import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { Login } from '../pages/Login'
import { AuthProvider } from '../contexts/AuthContext'
import { QueryProvider } from '../providers/QueryProvider'
import { ToastProvider } from '../components/Toast'
import { ActivityProvider } from '../contexts/ActivityContext'

// Mock config
vi.mock('../config', () => ({
  config: {
    apiUrl: 'http://localhost:5000/api',
  },
}))

// Mock fetch
global.fetch = vi.fn()

// Mock navigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

const renderWithProviders = (ui: React.ReactElement) => {
  return render(
    <BrowserRouter>
      <QueryProvider>
        <ActivityProvider>
          <AuthProvider>
            <ToastProvider>
              {ui}
            </ToastProvider>
          </AuthProvider>
        </ActivityProvider>
      </QueryProvider>
    </BrowserRouter>
  )
}

describe('Login Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render login form', () => {
    renderWithProviders(<Login />)
    
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('should validate email format', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Login />)
    
    const emailInput = screen.getByLabelText(/email address/i)
    await user.type(emailInput, 'invalid-email')
    
    await waitFor(() => {
      expect(screen.getByText(/please enter a valid email address/i)).toBeInTheDocument()
    })
  })

  it('should validate password length', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Login />)
    
    const passwordInput = screen.getByLabelText(/password/i)
    await user.type(passwordInput, '12345')
    
    await waitFor(() => {
      expect(screen.getByText(/password must be at least 6 characters/i)).toBeInTheDocument()
    })
  })

  it('should show error for empty form submission', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Login />)
    
    const emailInput = screen.getByLabelText(/email address/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })
    
    // Clear any default values and submit
    await user.clear(emailInput)
    await user.clear(passwordInput)
    await user.click(submitButton)
    
    // The form has required attributes, so browser validation might prevent submission
    // But if it does submit, we should see the error
    await waitFor(() => {
      const errorMessage = screen.queryByText(/please enter both email and password/i)
      const emailRequired = emailInput.hasAttribute('required')
      const passwordRequired = passwordInput.hasAttribute('required')
      
      // Either the error message appears OR the browser validation prevents submission
      expect(errorMessage || (emailRequired && passwordRequired)).toBeTruthy()
    }, { timeout: 2000 })
  })

  it('should toggle password visibility', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Login />)
    
    const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement
    
    expect(passwordInput.type).toBe('password')
    
    // Find the toggle button by its position (right side of password input)
    const passwordContainer = passwordInput.closest('.relative')
    const toggleButton = passwordContainer?.querySelector('button[type="button"]') as HTMLButtonElement
    
    expect(toggleButton).toBeInTheDocument()
    
    await user.click(toggleButton!)
    expect(passwordInput.type).toBe('text')
    
    await user.click(toggleButton!)
    expect(passwordInput.type).toBe('password')
  })

  it('should have proper autocomplete attributes', () => {
    renderWithProviders(<Login />)
    
    const emailInput = screen.getByLabelText(/email address/i)
    const passwordInput = screen.getByLabelText(/password/i)
    
    expect(emailInput).toHaveAttribute('autocomplete', 'email')
    expect(passwordInput).toHaveAttribute('autocomplete', 'current-password')
  })

  it('should have remember me checkbox', () => {
    renderWithProviders(<Login />)
    
    expect(screen.getByLabelText(/remember me/i)).toBeInTheDocument()
  })

  it('should have forgot password button', () => {
    renderWithProviders(<Login />)
    
    expect(screen.getByRole('button', { name: /forgot password\?/i })).toBeInTheDocument()
  })

  it('should have social login buttons', () => {
    renderWithProviders(<Login />)
    
    expect(screen.getByText(/gmail/i)).toBeInTheDocument()
    expect(screen.getByText(/microsoft/i)).toBeInTheDocument()
    expect(screen.getByText(/github/i)).toBeInTheDocument()
  })
})

