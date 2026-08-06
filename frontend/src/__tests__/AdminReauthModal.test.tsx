import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AdminReauthModal } from '../components/AdminReauthModal'

describe('AdminReauthModal', () => {
  it('does not persist password to storage and clears inputs after confirm', async () => {
    const onConfirm = vi.fn(async () => undefined)
    const setItem = vi.spyOn(Storage.prototype, 'setItem')

    render(
      <AdminReauthModal
        open
        onCancel={() => undefined}
        onConfirm={(password, mfaCode, recoveryCode) => {
          void onConfirm(password, mfaCode, recoveryCode)
        }}
      />
    )

    const password = screen.getByPlaceholderText('Operator password')
    fireEvent.change(password, { target: { value: 'SecretPass123!' } })
    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))

    expect(onConfirm).toHaveBeenCalledWith('SecretPass123!', undefined, undefined)
    expect(setItem).not.toHaveBeenCalledWith(
      expect.anything(),
      expect.stringContaining('SecretPass123!')
    )
    // Input cleared after submit (ephemeral only).
    expect((password as HTMLInputElement).value).toBe('')
  })

  it('shows backend error without treating frontend state as authorization', () => {
    render(
      <AdminReauthModal
        open
        error="Step-up authentication required"
        onCancel={() => undefined}
        onConfirm={() => undefined}
      />
    )
    expect(screen.getByText('Step-up authentication required')).toBeInTheDocument()
  })
})
