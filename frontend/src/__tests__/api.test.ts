import { describe, it, expect, vi, beforeEach } from 'vitest'
import { authApi } from '../lib/api'

// Mock fetch
global.fetch = vi.fn()

// Mock config
vi.mock('../config', () => ({
  config: {
    apiUrl: 'http://localhost:5000/api',
  },
}))

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    if (typeof localStorage !== 'undefined') {
      localStorage.clear()
    }
  })

  describe('authApi.login', () => {
    it('should successfully login with valid credentials', async () => {
      const mockResponse = {
        success: true,
        data: {
          user: {
            id: 1,
            email: 'test@example.com',
            name: 'Test User',
            onboarding_completed: true,
            onboarding_step: 1,
            role: 'user',
          },
          access_token: 'mock-token',
          expires_in: 3600,
          token_type: 'Bearer',
        },
      }

      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      })

      const result = await authApi.login('test@example.com', 'password123')

      expect(result.user).toBeDefined()
      expect(result.user.email).toBe('test@example.com')
      expect(result.access_token).toBe('mock-token')
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/auth/login'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
          credentials: 'include',
        })
      )
    })

    it('should handle login failure', async () => {
      const mockResponse = {
        success: false,
        error: 'Invalid credentials',
      }

      ;(global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => mockResponse,
      })

      await expect(authApi.login('test@example.com', 'wrongpassword')).rejects.toThrow()
    })

    it('should handle rate limiting', async () => {
      ;(global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 429,
        json: async () => ({ error: 'Rate limit exceeded' }),
      })

      await expect(authApi.login('test@example.com', 'password123')).rejects.toThrow()
    })
  })

  describe('authApi.signup', () => {
    it('should successfully signup with valid data', async () => {
      const mockResponse = {
        success: true,
        data: {
          user: {
            id: 1,
            email: 'newuser@example.com',
            name: 'New User',
            onboarding_completed: false,
            onboarding_step: 1,
            role: 'user',
          },
          access_token: 'mock-token',
          expires_in: 3600,
          token_type: 'Bearer',
        },
      }

      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      })

      const result = await authApi.signup({
        email: 'newuser@example.com',
        password: 'password123',
        name: 'New User',
      })

      expect(result.user).toBeDefined()
      expect(result.user.email).toBe('newuser@example.com')
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/auth/signup'),
        expect.objectContaining({
          method: 'POST',
          credentials: 'include',
        })
      )
    })

    it('should handle signup failure', async () => {
      const mockResponse = {
        success: false,
        error: 'Email already exists',
      }

      ;(global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => mockResponse,
      })

      await expect(
        authApi.signup({
          email: 'existing@example.com',
          password: 'password123',
          name: 'User',
        })
      ).rejects.toThrow()
    })
  })

  describe('API error handling', () => {
    it('should handle network errors', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('Network error'))

      await expect(authApi.login('test@example.com', 'password123')).rejects.toThrow()
    })

    it('should include credentials in requests', async () => {
      const mockResponse = {
        success: true,
        data: {
          user: {
            id: 1,
            email: 'test@example.com',
            name: 'Test User',
            onboarding_completed: true,
            onboarding_step: 1,
            role: 'user',
          },
          access_token: 'mock-token',
          expires_in: 3600,
          token_type: 'Bearer',
        },
      }

      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      })

      await authApi.login('test@example.com', 'password123')

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          credentials: 'include',
        })
      )
    })
  })
})

