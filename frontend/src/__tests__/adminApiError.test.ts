import { describe, expect, it } from 'vitest'
import { getAdminApiErrorCode, getAdminApiErrorMessage } from '../utils/adminApiError'

describe('adminApiError', () => {
  it('prefers API error text over axios status message', () => {
    const err = {
      message: 'Request failed with status code 403',
      response: { data: { error: 'Authentication failed', error_code: 'REAUTH_FAILED' } },
    }
    expect(getAdminApiErrorMessage(err, 'fallback')).toBe('Authentication failed')
    expect(getAdminApiErrorCode(err)).toBe('REAUTH_FAILED')
  })

  it('falls back when response body is empty', () => {
    const err = new Error('Request failed with status code 403')
    expect(getAdminApiErrorMessage(err, 'fallback')).toBe('Request failed with status code 403')
    expect(getAdminApiErrorCode(err)).toBeNull()
  })
})
