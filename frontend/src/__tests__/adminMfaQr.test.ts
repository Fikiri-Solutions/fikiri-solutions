import { describe, expect, it } from 'vitest'
import { formatTotpSecretForDisplay } from '../pages/admin/AdminMfaSecurity'

describe('formatTotpSecretForDisplay', () => {
  it('groups Base32 secret in fours without changing characters', () => {
    expect(formatTotpSecretForDisplay('JBSWY3DPEHPK3PXP')).toBe('JBSW Y3DP EHPK 3PXP')
  })

  it('strips existing spaces and uppercases for display', () => {
    expect(formatTotpSecretForDisplay('jbsw y3dp')).toBe('JBSW Y3DP')
  })
})
