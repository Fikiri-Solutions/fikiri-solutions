import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient, authApi } from '../lib/api'
import { useAuth } from '../store/auth'

const authUser = {
  id: 7,
  email: 'user@example.com',
  name: 'Test User',
  role: 'user',
  onboarding_completed: true,
  onboarding_step: 4,
}

function mockJsonResponse(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    })
  )
}

describe('frontend auth consolidation phase 1', () => {
  beforeEach(() => {
    localStorage.clear()
    useAuth.setState({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    })
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('apiClient attaches bearer token from Zustand first', async () => {
    useAuth.getState().login(authUser, 'zustand-access', 'zustand-refresh')
    localStorage.setItem('fikiri-token', 'legacy-access')
    vi.mocked(fetch).mockResolvedValueOnce(await mockJsonResponse({
      success: true,
      data: {
        status: 'healthy',
        timestamp: 'now',
        version: 'test',
        services: {},
      },
    }))

    await apiClient.getHealth()

    const headers = vi.mocked(fetch).mock.calls[0][1]?.headers as Headers
    expect(headers.get('Authorization')).toBe('Bearer zustand-access')
  })

  it('apiClient falls back to fikiri-token while legacy support remains', async () => {
    localStorage.setItem('fikiri-token', 'legacy-access')
    vi.mocked(fetch).mockResolvedValueOnce(await mockJsonResponse({
      success: true,
      data: {
        status: 'healthy',
        timestamp: 'now',
        version: 'test',
        services: {},
      },
    }))

    await apiClient.getHealth()

    const headers = vi.mocked(fetch).mock.calls[0][1]?.headers as Headers
    expect(headers.get('Authorization')).toBe('Bearer legacy-access')
  })

  it('authApi.refresh sends the refresh token in the request body', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(await mockJsonResponse({
      success: true,
      data: {
        access_token: 'new-access',
        refresh_token: 'new-refresh',
        expires_in: 3600,
        token_type: 'Bearer',
      },
    }))

    await authApi.refresh('refresh-token')

    expect(vi.mocked(fetch).mock.calls[0][1]?.body).toBe(JSON.stringify({
      refresh_token: 'refresh-token',
    }))
  })

  it('Login updates Zustand and AuthContext exposes it to route guards', async () => {
    const loginSource = await import('../pages/Login.tsx?raw')
    const authContextSource = await import('../contexts/AuthContext.tsx?raw')
    const routeGuardSource = await import('../components/RouteGuard.tsx?raw')

    expect(loginSource.default).toContain('useAuthActions')
    expect(loginSource.default).toContain('login(result.user, result.access_token, result.refresh_token)')
    expect(authContextSource.default).toContain("import { useAuth as useAuthStore } from '../store/auth'")
    expect(authContextSource.default).toContain('zustandIsAuthenticated')
    expect(authContextSource.default).toContain('zustandAccessToken')
    expect(authContextSource.default).toContain('isAuthenticated: true')
    expect(routeGuardSource.default).toContain("import { useAuth } from '../contexts/AuthContext'")
    expect(routeGuardSource.default).toContain('requireAuth && !isAuthenticated')
  })

  it('logout path clears Zustand tokens and legacy localStorage auth keys', async () => {
    const authContextSource = await import('../contexts/AuthContext.tsx?raw')
    localStorage.setItem('fikiri-token', 'legacy-access')
    localStorage.setItem('fikiri-user', JSON.stringify(authUser))
    localStorage.setItem('fikiri-user-id', String(authUser.id))
    localStorage.setItem('fikiri-remember-password', 'plaintext')
    useAuth.getState().login(authUser, 'zustand-access', 'zustand-refresh')

    useAuth.getState().logout()

    expect(useAuth.getState().accessToken).toBeNull()
    expect(useAuth.getState().refreshToken).toBeNull()
    expect(localStorage.getItem('fikiri-token')).toBeNull()
    expect(localStorage.getItem('fikiri-user')).toBeNull()
    expect(localStorage.getItem('fikiri-user-id')).toBeNull()
    expect(localStorage.getItem('fikiri-remember-password')).toBeNull()
    expect(authContextSource.default).toContain("localStorage.removeItem('fikiri-token')")
    expect(authContextSource.default).toContain("localStorage.removeItem('fikiri-user')")
    expect(authContextSource.default).toContain("localStorage.removeItem('fikiri-user-id')")
    expect(authContextSource.default).toContain("localStorage.removeItem('fikiri-remember-password')")
    expect(authContextSource.default).toContain('zustandLogout()')
  })

  it('does not reintroduce plaintext password storage', async () => {
    const source = await import('../pages/Login.tsx?raw')
    expect(source.default).not.toContain("setItem('fikiri-remember-password'")
    expect(source.default).not.toContain('setItem("fikiri-remember-password"')
  })
})
