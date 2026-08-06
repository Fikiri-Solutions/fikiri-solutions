import { useState } from 'react'

interface AdminReauthModalProps {
  open: boolean
  title?: string
  busy?: boolean
  error?: string | null
  onCancel: () => void
  onConfirm: (password: string, mfaCode?: string, recoveryCode?: string) => void | Promise<void>
}

/**
 * Privileged-action reauthentication UI.
 * Authorization is never granted from frontend success alone — callers must await backend confirmation.
 * Password / MFA / recovery values stay in ephemeral component state only.
 */
export function AdminReauthModal({
  open,
  title = 'Confirm your identity',
  busy = false,
  error = null,
  onCancel,
  onConfirm,
}: AdminReauthModalProps) {
  const [password, setPassword] = useState('')
  const [mfaCode, setMfaCode] = useState('')
  const [recoveryCode, setRecoveryCode] = useState('')
  const [useRecovery, setUseRecovery] = useState(false)

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="admin-reauth-title"
        className="w-full max-w-md rounded-xl border border-amber-300 bg-white p-5 shadow-lg dark:border-amber-700 dark:bg-slate-900"
      >
        <h2 id="admin-reauth-title" className="text-lg font-semibold text-amber-950 dark:text-amber-100">
          {title}
        </h2>
        <p className="mt-1 text-sm text-amber-900 dark:text-amber-200">
          Re-enter your operator password. Privileged actions require a fresh server-side confirmation.
        </p>
        {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
        <form
          className="mt-4 space-y-3"
          onSubmit={(event) => {
            event.preventDefault()
            void onConfirm(
              password,
              useRecovery ? undefined : mfaCode || undefined,
              useRecovery ? recoveryCode || undefined : undefined
            )
            setPassword('')
            setMfaCode('')
            setRecoveryCode('')
          }}
        >
          <input
            type="password"
            autoComplete="current-password"
            name="admin-reauth-password"
            placeholder="Operator password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="w-full rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm dark:border-amber-700 dark:bg-slate-950"
          />
          {useRecovery ? (
            <input
              type="text"
              autoComplete="off"
              name="admin-reauth-recovery"
              placeholder="Recovery code"
              value={recoveryCode}
              onChange={(event) => setRecoveryCode(event.target.value)}
              className="w-full rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm dark:border-amber-700 dark:bg-slate-950"
            />
          ) : (
            <input
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              name="admin-reauth-mfa"
              placeholder="MFA code (if required)"
              value={mfaCode}
              onChange={(event) => setMfaCode(event.target.value)}
              className="w-full rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm dark:border-amber-700 dark:bg-slate-950"
            />
          )}
          <button
            type="button"
            className="text-xs text-amber-800 underline dark:text-amber-200"
            onClick={() => setUseRecovery((value) => !value)}
          >
            {useRecovery ? 'Use authenticator code instead' : 'Use a recovery code instead'}
          </button>
          <div className="flex gap-2 pt-1">
            <button
              type="submit"
              disabled={busy || !password || (useRecovery && !recoveryCode)}
              className="rounded-lg bg-amber-700 px-4 py-2 text-sm font-medium text-white hover:bg-amber-600 disabled:opacity-60"
            >
              {busy ? 'Confirming…' : 'Confirm'}
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                setPassword('')
                setMfaCode('')
                setRecoveryCode('')
                onCancel()
              }}
              className="rounded-lg border border-amber-400 px-4 py-2 text-sm"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
