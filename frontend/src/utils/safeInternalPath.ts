/**
 * Safe internal path for post-auth redirects.
 * Rejects protocol-relative URLs, absolute origins, and backslash open-redirect tricks.
 */
export function safeInternalPath(
  raw: string | null | undefined,
  options?: { disallow?: string[] }
): string | null {
  if (!raw) return null
  const path = raw.trim()
  if (!path.startsWith('/') || path.startsWith('//')) return null
  // Backslashes can become open redirects in some browsers / React Router versions.
  if (path.includes('\\')) return null
  if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(path)) return null
  const disallow = options?.disallow ?? ['/login', '/signup', '/forgot-password', '/reset-password']
  if (disallow.includes(path.split(/[?#]/, 1)[0] ?? path)) return null
  return path
}
