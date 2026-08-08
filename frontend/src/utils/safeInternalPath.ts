/**
 * Safe internal path for post-auth redirects.
 * Rejects protocol-relative URLs and absolute origins.
 */
export function safeInternalPath(
  raw: string | null | undefined,
  options?: { disallow?: string[] }
): string | null {
  if (!raw) return null
  const path = raw.trim()
  if (!path.startsWith('/') || path.startsWith('//')) return null
  if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(path)) return null
  const disallow = options?.disallow ?? ['/login', '/signup', '/forgot-password', '/reset-password']
  if (disallow.includes(path)) return null
  return path
}
