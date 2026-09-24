import { isKnownSpaPath, isStaticAssetPath, normalizePathname } from './src/lib/spaKnownPaths'

const APEX_HOST = 'fikirisolutions.com'
const WWW_HOST = `www.${APEX_HOST}`

/**
 * Edge middleware (Vercel):
 * 1) Permanent www → apex redirect
 * 2) Unknown SPA paths: serve index.html body with HTTP 404 so crawlers see 404
 *    while React still mounts NotFoundPage.
 */
export default async function middleware(request: Request): Promise<Response | undefined> {
  const url = new URL(request.url)

  if (url.hostname === WWW_HOST) {
    url.hostname = APEX_HOST
    return Response.redirect(url.toString(), 308)
  }

  // Only enforce SPA 404 semantics on the production apex (and preview hosts).
  const path = normalizePathname(url.pathname)
  if (isStaticAssetPath(path) || isKnownSpaPath(path)) {
    return undefined
  }

  try {
    const indexUrl = new URL('/index.html', url.origin)
    const indexRes = await fetch(indexUrl, {
      headers: { Accept: 'text/html' },
    })
    if (!indexRes.ok) {
      return undefined
    }
    const body = await indexRes.text()
    const headers = new Headers(indexRes.headers)
    headers.set('content-type', 'text/html; charset=utf-8')
    headers.set('cache-control', 'no-cache')
    // Avoid caching unknown routes as soft-200 SPA shells at the edge.
    headers.delete('etag')
    return new Response(body, { status: 404, headers })
  } catch {
    return undefined
  }
}

export const config = {
  matcher: [
    // Skip internals, static dirs, and any path with a file extension (*.js, *.webp, index.html, …)
    '/((?!_vercel|assets/|fonts/|icons/|img/|images/|optimized/|media/|brand/|.*\\..*).*)',
  ],
}
