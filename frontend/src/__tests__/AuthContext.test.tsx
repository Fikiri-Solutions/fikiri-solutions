import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider, useAuth } from '../contexts/AuthContext'
import { QueryProvider } from '../providers/QueryProvider'
import { ActivityProvider } from '../contexts/ActivityContext'
import { apiClient } from '../services/apiClient'

// Mock fetch
global.fetch = vi.fn()

vi.mock('../services/apiClient', () => ({
  apiClient: {
    login: vi.fn(),
    signup: vi.fn(),
    logout: vi.fn(),
  },
}))

// Mock navigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>
    <QueryProvider>
      <ActivityProvider>
        <AuthProvider>
          {children}
        </AuthProvider>
      </ActivityProvider>
    </QueryProvider>
  </BrowserRouter>
)

// Mock config
vi.mock('../config', () => ({
  config: {
    apiUrl: 'http://localhost:5000/api',
  },
}))

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    if (typeof localStorage !== 'undefined') {
      localStorage.clear()
    }
  })

  it('should provide initial auth state', () => {
    const { result } = renderHook(() => useAuth(), { wrapper })
    
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBe(null)
    expect(result.current.isLoading).toBe(false)
  })

  it('should load user from localStorage on mount', async () => {
    const mockUser = {
      id: 1,
      email: 'test@example.com',
      name: 'Test User',
      onboarding_completed: true,
      onboarding_step: 1,
    }
    
    localStorage.setItem('fikiri-user', JSON.stringify(mockUser))
    localStorage.setItem('fikiri-user-id', '1')
    
    const { result } = renderHook(() => useAuth(), { wrapper })
    
    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true)
      expect(result.current.user).toEqual(mockUser)
    })
  })

  it('should handle successful login', async () => {
    const mockResponse = {
      success: true,
      data: {
        user: {
          id: 1,
          email: 'test@example.com',
          name: 'Test User',
          onboarding_completed: false,
          onboarding_step: 1,
        },
        access_token: 'mock-token',
      },
    }

    vi.mocked(apiClient.login).mockResolvedValueOnce(mockResponse as any)

    const { result } = renderHook(() => useAuth(), { wrapper })
    
    await act(async () => {
      const loginResult = await result.current.login('test@example.com', 'password123')
      expect(loginResult.success).toBe(true)
      expect(loginResult.user).toBeDefined()
    })
    
    expect(localStorage.getItem('fikiri-user')).toBeTruthy()
  })

  it('should handle login failure', async () => {
    const mockResponse = {
      success: false,
      error: 'Invalid credentials',
    }

    vi.mocked(apiClient.login).mockResolvedValueOnce(mockResponse as any)

    const { result } = renderHook(() => useAuth(), { wrapper })
    
    const loginResult = await result.current.login('test@example.com', 'wrongpassword')
    
    expect(loginResult.success).toBe(false)
    expect(loginResult.error).toBe('Invalid credentials')
  })

  it('should handle rate limiting', async () => {
    vi.mocked(apiClient.login).mockRejectedValueOnce({
      response: {
        status: 429,
        data: { retry_after: 900 },
      },
    })

    const { result } = renderHook(() => useAuth(), { wrapper })
    
    const loginResult = await result.current.login('test@example.com', 'password123')
    
    expect(loginResult.success).toBe(false)
    expect(loginResult.error).toContain('Too many login attempts')
  })

  it('should handle network errors', async () => {
    vi.mocked(apiClient.login).mockRejectedValueOnce(new Error('Network error. Please try again.'))

    const { result } = renderHook(() => useAuth(), { wrapper })
    
    const loginResult = await result.current.login('test@example.com', 'password123')
    
    expect(loginResult.success).toBe(false)
    expect(loginResult.error).toBe('Network error. Please try again.')
  })

  it('should get correct redirect path for unauthenticated user', () => {
    const { result } = renderHook(() => useAuth(), { wrapper })
    
    expect(result.current.getRedirectPath()).toBe('/login')
  })

  it('should get correct redirect path for authenticated user without onboarding', async () => {
    const mockUser = {
      id: 1,
      email: 'test@example.com',
      name: 'Test User',
      onboarding_completed: false,
      onboarding_step: 1,
    }
    
    localStorage.setItem('fikiri-user', JSON.stringify(mockUser))
    localStorage.setItem('fikiri-user-id', '1')
    
    const { result } = renderHook(() => useAuth(), { wrapper })
    
    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true)
      expect(result.current.getRedirectPath()).toBe('/onboarding')
    })
  })

  it('should get correct redirect path for authenticated user with onboarding', async () => {
    const mockUser = {
      id: 1,
      email: 'test@example.com',
      name: 'Test User',
      onboarding_completed: true,
      onboarding_step: 4,
    }
    
    localStorage.setItem('fikiri-user', JSON.stringify(mockUser))
    localStorage.setItem('fikiri-user-id', '1')
    
    const { result } = renderHook(() => useAuth(), { wrapper })
    
    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true)
      expect(result.current.getRedirectPath()).toBe('/dashboard')
    })
  })

  it('should clear auth data on logout', async () => {
    const mockUser = {
      id: 1,
      email: 'test@example.com',
      name: 'Test User',
      onboarding_completed: true,
      onboarding_step: 4,
    }
    
    localStorage.setItem('fikiri-user', JSON.stringify(mockUser))
    localStorage.setItem('fikiri-user-id', '1')
    
    ;(global.fetch as any).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ success: true }),
    })

    const { result } = renderHook(() => useAuth(), { wrapper })
    
    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true)
    })
    
    await act(async () => {
      await result.current.logout()
    })
    
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBe(null)
    expect(localStorage.getItem('fikiri-user')).toBeNull()
    expect(mockNavigate).toHaveBeenCalledWith('/')
  })
})
