import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { render, screen, waitFor } from '@testing-library/react'
import { VerifyEmail } from '../pages/VerifyEmail'

const mockVerifyEmail = vi.fn()
const mockWhoami = vi.fn()
const mockResend = vi.fn()
const mockUpdateUser = vi.fn()

vi.mock('../services/apiClient', () => ({
  apiClient: {
    verifyEmail: (...args: unknown[]) => mockVerifyEmail(...args),
    whoami: (...args: unknown[]) => mockWhoami(...args),
    resendEmailVerification: (...args: unknown[]) => mockResend(...args),
  },
}))

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: null,
    isAuthenticated: false,
    updateUser: mockUpdateUser,
  }),
}))

vi.mock('react-hot-toast', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

vi.mock('../components/radiant', () => ({
  RadiantLayout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="radiant-layout">{children}</div>
  ),
}))

vi.mock('framer-motion', async () => {
  const actual = await vi.importActual<typeof import('framer-motion')>('framer-motion')
  return {
    ...actual,
    useReducedMotion: () => true,
  }
})

function renderVerify(search: string) {
  return render(
    <MemoryRouter initialEntries={[`/verify-email${search}`]}>
      <Routes>
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route path="/login" element={<div>Login page</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('VerifyEmail continuity', { timeout: 15_000 }, () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows clear expired/invalid state for bad tokens', async () => {
    mockVerifyEmail.mockRejectedValue({
      response: { data: { error: 'Token expired' } },
    })

    renderVerify('?token=bad-token')

    await waitFor(
      () => {
        expect(screen.getByRole('heading', { name: /verification link expired/i })).toBeInTheDocument()
      },
      { timeout: 5000 }
    )
    expect(screen.getByRole('link', { name: /^sign in$/i })).toHaveAttribute('href', '/login')
    expect(screen.queryByRole('link', { name: /sign in to continue/i })).not.toBeInTheDocument()
  })

  it('shows success + sign in CTA when verified without a session', async () => {
    mockVerifyEmail.mockResolvedValue({
      success: true,
      data: { onboarding_completed: false, email_verified: true },
    })
    mockWhoami.mockRejectedValue(new Error('unauthorized'))

    renderVerify('?token=good-token')

    await waitFor(
      () => {
        expect(screen.getByRole('heading', { name: /^email verified$/i })).toBeInTheDocument()
      },
      { timeout: 5000 }
    )
    expect(
      screen.getByText(/please sign in to continue setting up your account/i)
    ).toBeInTheDocument()
    const cta = screen.getByRole('link', { name: /sign in to continue/i })
    expect(cta).toHaveAttribute('href', '/login?redirect=%2Fonboarding')
  })

  it('shows missing-token error without calling the API', async () => {
    renderVerify('')

    expect(await screen.findByRole('heading', { name: /verification link expired/i })).toBeInTheDocument()
    expect(mockVerifyEmail).not.toHaveBeenCalled()
  })
})
