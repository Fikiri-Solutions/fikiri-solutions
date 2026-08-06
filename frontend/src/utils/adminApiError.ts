/** Extract human-readable API error text from axios-style failures. */
export function getAdminApiErrorMessage(err: unknown, fallback: string): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const data = (err as { response?: { data?: Record<string, unknown> } }).response?.data
    if (data) {
      const error = data.error
      const message = data.message
      const code = data.error_code || data.code
      if (typeof error === 'string' && error.trim()) return error
      if (typeof message === 'string' && message.trim()) return message
      if (typeof code === 'string' && code.trim()) return code
    }
  }
  if (err instanceof Error && err.message) return err.message
  return fallback
}

export function getAdminApiErrorCode(err: unknown): string | null {
  if (err && typeof err === 'object' && 'response' in err) {
    const data = (err as { response?: { data?: Record<string, unknown> } }).response?.data
    const code = data?.error_code || data?.code
    return typeof code === 'string' ? code : null
  }
  return null
}
