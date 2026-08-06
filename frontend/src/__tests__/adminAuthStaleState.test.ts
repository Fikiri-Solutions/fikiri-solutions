import { describe, expect, it } from 'vitest'
import { getAdminApiErrorCode, getAdminApiErrorMessage } from '../utils/adminApiError'

describe('admin auth stale-state messaging', () => {
  it('surfaces TOKEN_REVOKED without exposing session version', () => {
    const err = {
      message: 'Request failed with status code 401',
      response: {
        data: {
          error: 'Token has been revoked',
          error_code: 'TOKEN_REVOKED',
          asv: 99,
          auth_session_version: 99,
        },
      },
    }
    expect(getAdminApiErrorCode(err)).toBe('TOKEN_REVOKED')
    expect(getAdminApiErrorMessage(err, 'fallback')).toBe('Token has been revoked')
    expect(getAdminApiErrorMessage(err, 'fallback')).not.toMatch(/asv|session_version/i)
  })

  it('surfaces recoverable step-up message after MFA confirm without privilege', () => {
    const err = {
      response: {
        data: {
          error: 'Step-up authentication required',
          error_code: 'MFA_REQUIRED',
        },
      },
    }
    expect(getAdminApiErrorCode(err)).toBe('MFA_REQUIRED')
    expect(getAdminApiErrorMessage(err, 'fallback')).toBe('Step-up authentication required')
  })
})
