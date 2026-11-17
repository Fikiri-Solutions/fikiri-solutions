import { describe, expect, it } from 'vitest'
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

/**
 * Regression: /work must not be swallowed by the SPA 404 middleware or miss
 * directory-index rewrites. Relative lookbook assets require the trailing slash.
 */
describe('work lookbook routing', () => {
  const root = resolve(__dirname, '../..')
  const vercel = JSON.parse(readFileSync(resolve(root, 'vercel.json'), 'utf8')) as {
    redirects: Array<{ source: string; destination: string }>
    rewrites: Array<{ source: string; destination: string }>
  }
  const middleware = readFileSync(resolve(root, 'middleware.ts'), 'utf8')
  const dataJs = readFileSync(resolve(root, 'public/work/data.js'), 'utf8')

  it('redirects /work → /work/ and rewrites /work/ → index.html', () => {
    expect(vercel.redirects.some((r) => r.source === '/work' && r.destination === '/work/')).toBe(
      true
    )
    expect(
      vercel.rewrites.some((r) => r.source === '/work/' && r.destination === '/work/index.html')
    ).toBe(true)
    const spa = vercel.rewrites.find((r) => r.destination === '/index.html')
    expect(spa?.source).toContain('work(?:/|$)')
  })

  it('excludes /work from the edge middleware matcher', () => {
    expect(middleware).toMatch(/work\(\?:\/\|\$\)/)
  })

  it('ships seven mockup thumbs referenced by data.js', () => {
    const thumbs = [...dataJs.matchAll(/thumbSrc:\s*"([^"]+)"/g)].map((m) => m[1].split('?')[0])
    expect(thumbs).toHaveLength(7)
    for (const rel of thumbs) {
      expect(existsSync(resolve(root, 'public/work', rel))).toBe(true)
    }
    expect(dataJs).toContain('voluble-khapse-43b88e.netlify.app')
  })
})
