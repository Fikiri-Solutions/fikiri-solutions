import { useEffect, useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { apiClient } from '../../services/apiClient'
import { AdminReauthModal } from '../../components/AdminReauthModal'
import { getAdminApiErrorCode, getAdminApiErrorMessage } from '../../utils/adminApiError'

/** Group Base32 secret for reading; authenticators need the compact form when typing. */
export function formatTotpSecretForDisplay(secret: string): string {
  const compact = secret.replace(/\s+/g, '').toUpperCase()
  return compact.replace(/(.{4})(?=.)/g, '$1 ')
}

/**
 * Operator MFA management. Sensitive values stay in component state only and are cleared on leave.
 * Frontend never treats local state as authorization proof.
 */
export function AdminMfaSecurity() {
  const [status, setStatus] = useState<{
    enrolled: boolean
    recovery_codes_remaining: number
    verifier_enabled: boolean
  } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [showReauth, setShowReauth] = useState(false)
  const [pendingAction, setPendingAction] = useState<'enroll' | 'regenerate' | 'confirm' | null>(
    null
  )
  const [enrollment, setEnrollment] = useState<{ secret: string; provisioning_uri: string } | null>(
    null
  )
  const [confirmCode, setConfirmCode] = useState('')
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null)

  const refreshStatus = async () => {
    const next = await apiClient.getAdminMfaStatus()
    setStatus({
      enrolled: Boolean(next.enrolled),
      recovery_codes_remaining: Number(next.recovery_codes_remaining || 0),
      verifier_enabled: Boolean(next.verifier_enabled),
    })
  }

  useEffect(() => {
    let cancelled = false
    void refreshStatus().catch((err: unknown) => {
      if (!cancelled) setError(getAdminApiErrorMessage(err, 'Failed to load MFA status'))
    })
    return () => {
      cancelled = true
      setEnrollment(null)
      setRecoveryCodes(null)
      setConfirmCode('')
    }
  }, [])

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-xl font-semibold">Operator MFA</h2>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Enroll an authenticator app for privileged admin actions. Secrets and recovery codes are
          shown once and are never stored in the browser.
        </p>
        {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
        <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-slate-500">Enrolled</dt>
            <dd className="font-medium">{status?.enrolled ? 'Yes' : 'No'}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Recovery codes left</dt>
            <dd className="font-medium">{status?.recovery_codes_remaining ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Verifier</dt>
            <dd className="font-medium">{status?.verifier_enabled ? 'Enabled' : 'Disabled'}</dd>
          </div>
        </dl>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={() => {
              setPendingAction('enroll')
              setShowReauth(true)
              setError(null)
            }}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-60"
          >
            {status?.enrolled ? 'Replace authenticator' : 'Enroll authenticator'}
          </button>
          {status?.enrolled ? (
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                setPendingAction('regenerate')
                setShowReauth(true)
                setError(null)
              }}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm dark:border-slate-700"
            >
              Regenerate recovery codes
            </button>
          ) : null}
        </div>
      </section>

      {enrollment ? (
        <section className="rounded-xl border border-amber-300 bg-amber-50 p-6 dark:border-amber-700 dark:bg-amber-950/40">
          <h3 className="font-semibold text-amber-950 dark:text-amber-100">Confirm enrollment</h3>
          <p className="mt-2 text-sm text-amber-900 dark:text-amber-200">
            Scan this QR code with your authenticator app (Google Authenticator, Microsoft
            Authenticator, 1Password, Authy, etc.), then enter the 6-digit code it shows. The QR and
            secret are shown only during this step.
          </p>
          <div className="mt-5 flex flex-col items-start gap-4 sm:flex-row sm:items-center">
            <div
              className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
              data-testid="admin-mfa-qr"
              aria-label="Authenticator QR code"
            >
              <QRCodeSVG
                value={enrollment.provisioning_uri}
                size={256}
                level="H"
                marginSize={4}
                bgColor="#ffffff"
                fgColor="#0f172a"
              />
            </div>
            <div className="max-w-sm space-y-2 text-sm text-amber-900 dark:text-amber-200">
              <p className="font-medium text-amber-950 dark:text-amber-100">Can&apos;t scan?</p>
              <p>
                In your app choose &quot;Enter setup key&quot; / &quot;Manual entry&quot;. Use only
                the secret below — not the full <code className="text-xs">otpauth://</code> link.
              </p>
              <p className="font-mono text-base tracking-wider text-amber-950 dark:text-amber-100">
                {formatTotpSecretForDisplay(enrollment.secret)}
              </p>
              <button
                type="button"
                className="rounded-lg border border-amber-500 px-3 py-1.5 text-xs font-medium"
                onClick={() => {
                  const compact = enrollment.secret.replace(/\s+/g, '').toUpperCase()
                  void navigator.clipboard?.writeText(compact).catch(() => undefined)
                }}
              >
                Copy secret (no spaces)
              </button>
            </div>
          </div>
          <details className="mt-4 text-xs text-amber-900 dark:text-amber-300">
            <summary className="cursor-pointer select-none">Advanced: provisioning URI</summary>
            <p className="mt-2 break-all font-mono">{enrollment.provisioning_uri}</p>
          </details>
          <form
            className="mt-4 flex flex-wrap items-end gap-2"
            onSubmit={(event) => {
              event.preventDefault()
              setBusy(true)
              setError(null)
              void apiClient
                .confirmAdminMfaEnrollment(confirmCode)
                .then((result) => {
                  setEnrollment(null)
                  setConfirmCode('')
                  setRecoveryCodes(result.recovery_codes)
                  return refreshStatus()
                })
                .catch((err: unknown) => {
                  const code = getAdminApiErrorCode(err)
                  if (code === 'STEP_UP_REQUIRED') {
                    // Keep secret on screen; reauth then retry confirm without restarting enroll.
                    setPendingAction('confirm')
                    setShowReauth(true)
                    setError(
                      'Confirmation window expired. Re-enter your password, then submit the authenticator code again.'
                    )
                  } else {
                    setError(getAdminApiErrorMessage(err, 'Confirmation failed'))
                  }
                })
                .finally(() => setBusy(false))
            }}
          >
            <input
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="Authenticator code"
              value={confirmCode}
              onChange={(event) => setConfirmCode(event.target.value)}
              className="rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm dark:border-amber-700 dark:bg-slate-950"
            />
            <button
              type="submit"
              disabled={busy || !confirmCode}
              className="rounded-lg bg-amber-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
            >
              Confirm
            </button>
            <button
              type="button"
              onClick={() => {
                setEnrollment(null)
                setConfirmCode('')
              }}
              className="rounded-lg border border-amber-400 px-4 py-2 text-sm"
            >
              Cancel
            </button>
          </form>
        </section>
      ) : null}

      {recoveryCodes ? (
        <section className="rounded-xl border border-emerald-300 bg-emerald-50 p-6 dark:border-emerald-800 dark:bg-emerald-950/30">
          <h3 className="font-semibold text-emerald-950 dark:text-emerald-100">
            Save these recovery codes now
          </h3>
          <p className="mt-2 text-sm text-emerald-900 dark:text-emerald-200">
            They will not be shown again. Store them offline in a secure place.
          </p>
          <ul className="mt-3 grid gap-1 font-mono text-sm sm:grid-cols-2">
            {recoveryCodes.map((code) => (
              <li key={code}>{code}</li>
            ))}
          </ul>
          <button
            type="button"
            className="mt-4 rounded-lg border border-emerald-500 px-4 py-2 text-sm"
            onClick={() => setRecoveryCodes(null)}
          >
            I saved them — clear from screen
          </button>
        </section>
      ) : null}

      <AdminReauthModal
        open={showReauth}
        title="Confirm identity for MFA change"
        busy={busy}
        error={error}
        onCancel={() => {
          setShowReauth(false)
          setPendingAction(null)
          setError(null)
        }}
        onConfirm={async (password, mfaCode, recoveryCode) => {
          setBusy(true)
          setError(null)
          try {
            const stepUp = await apiClient.reauthenticateAdmin({
              password,
              mfa_code: mfaCode,
              recovery_code: recoveryCode,
            })
            if (!stepUp?.step_up_confirmed) {
              throw new Error('Step-up authentication required')
            }
            if (pendingAction === 'enroll') {
              const started = await apiClient.startAdminMfaEnrollment()
              setEnrollment({
                secret: started.secret,
                provisioning_uri: started.provisioning_uri,
              })
              setRecoveryCodes(null)
            } else if (pendingAction === 'regenerate') {
              const regenerated = await apiClient.regenerateAdminRecoveryCodes()
              setRecoveryCodes(regenerated.recovery_codes)
              await refreshStatus()
            } else if (pendingAction === 'confirm') {
              if (!confirmCode.trim()) {
                setShowReauth(false)
                setPendingAction(null)
                setError('Re-enter the authenticator code below to finish enrollment.')
                return
              }
              const result = await apiClient.confirmAdminMfaEnrollment(confirmCode)
              setEnrollment(null)
              setConfirmCode('')
              setRecoveryCodes(result.recovery_codes)
              await refreshStatus()
            }
            setShowReauth(false)
            setPendingAction(null)
          } catch (err: unknown) {
            setError(getAdminApiErrorMessage(err, 'Request failed'))
          } finally {
            setBusy(false)
          }
        }}
      />
    </div>
  )
}
