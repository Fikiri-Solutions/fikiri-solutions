/**
 * Vite Plugin to Remove Invalid Prefetch Links
 * Removes prefetch links with wildcards (e.g., EnhancedDashboard-*.js) that browsers can't resolve
 */

import type { Plugin } from 'vite'

export function removeInvalidPrefetch(): Plugin {
  return {
    name: 'remove-invalid-prefetch',
    transformIndexHtml(html: string) {
      // Remove prefetch/preload links with wildcards
      return html.replace(
        /<link\s+rel="(prefetch|preload)"[^>]*href="[^"]*\*[^"]*"[^>]*>/gi,
        ''
      )
    },
  }
}

