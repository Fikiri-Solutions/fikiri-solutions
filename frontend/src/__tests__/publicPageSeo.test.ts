import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import {
  absoluteUrl,
  getPublicPageSeo,
  getSitemapEntries,
  PUBLIC_PAGE_SEO,
  SITE_ORIGIN,
} from '../lib/publicPageSeo'

const AUTH_OR_APP_PATHS = [
  '/services',
  '/ai',
  '/crm',
  '/dashboard',
  '/admin',
  '/login',
  '/signup',
  '/inbox',
]

describe('publicPageSeo', () => {
  it('has unique titles and descriptions for sitemap entries', () => {
    const entries = getSitemapEntries()
    const titles = new Set(entries.map((e) => e.title))
    const descriptions = new Set(entries.map((e) => e.description))
    expect(titles.size).toBe(entries.length)
    expect(descriptions.size).toBe(entries.length)
    for (const entry of entries) {
      expect(entry.title.length).toBeGreaterThan(10)
      expect(entry.description.length).toBeGreaterThan(40)
      expect(absoluteUrl(entry.path).startsWith(SITE_ORIGIN)).toBe(true)
    }
  })

  it('looks up routes used by PageMeta', () => {
    expect(getPublicPageSeo('/contact')?.title).toMatch(/Contact/i)
    expect(getPublicPageSeo('/about/')?.path).toBe('/about')
    expect(getPublicPageSeo('/nope')).toBeUndefined()
  })

  it('excludes legacy landing from sitemap and marks noindex', () => {
    const classic = getPublicPageSeo('/landing-classic')
    expect(classic?.sitemap).toBe(false)
    expect(classic?.robots).toMatch(/noindex/i)
    expect(getSitemapEntries().some((e) => e.path === '/landing-classic')).toBe(false)
  })
})

describe('public sitemap.xml + robots.txt', () => {
  const sitemap = readFileSync(resolve(__dirname, '../../public/sitemap.xml'), 'utf8')
  const robots = readFileSync(resolve(__dirname, '../../public/robots.txt'), 'utf8')

  it('lists exactly the public sitemap catalog URLs on the apex host', () => {
    const locs = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1])
    const expected = getSitemapEntries().map((e) => absoluteUrl(e.path))
    expect(locs.sort()).toEqual([...expected].sort())
    expect(locs.every((u) => u.startsWith(SITE_ORIGIN))).toBe(true)
  })

  it('does not include auth or app-shell routes', () => {
    for (const path of AUTH_OR_APP_PATHS) {
      expect(sitemap).not.toContain(`${SITE_ORIGIN}${path}<`)
      expect(PUBLIC_PAGE_SEO.some((e) => e.path === path && e.sitemap !== false)).toBe(false)
    }
  })

  it('references the production sitemap and disallows app surfaces', () => {
    expect(robots).toContain(`Sitemap: ${SITE_ORIGIN}/sitemap.xml`)
    expect(robots).toContain('Disallow: /admin')
    expect(robots).toContain('Disallow: /dashboard')
    expect(robots).toContain('Disallow: /crm')
    expect(robots).not.toContain('Disallow: /_next/')
    expect(robots).not.toMatch(/^Allow: \/services$/m)
  })
})
