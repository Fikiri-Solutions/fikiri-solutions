import { useEffect, useLayoutEffect } from 'react'
import { useLocation } from 'react-router-dom'

/** Paths that are always forced to light mode (no dark mode option). */
const LANDING_PATHS = [
  '/',
  '/landing-classic',
  '/pricing',
  '/services-landing',
  '/ai-landing',
  '/industries',
  '/about',
  '/terms',
  '/privacy',
  '/error',
  '/login',
  '/signup',
  '/forgot-password',
  '/reset-password',
  // In-app /automations and /integrations use the user's theme (not listed here).
  // If you add a public landing route (e.g. /automations-landing), add it above.
]

function isLandingPath(pathname: string): boolean {
  return LANDING_PATHS.some(
    (p) => pathname === p || (p !== '/' && pathname.startsWith(p + '/'))
  )
}

function getResolvedTheme(): 'light' | 'dark' {
  const saved = localStorage.getItem('fikiri-theme')
  if (saved === 'dark') return 'dark'
  if (saved === 'light') return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyLandingLight() {
  const root = document.documentElement
  root.classList.remove('dark')
  root.classList.add('light')
  root.setAttribute('data-theme', 'light')
}

/**
 * When the current route is a landing path, forces the document to light mode.
 * When leaving a landing path, restores the user's saved (or system) theme.
 * Listens for theme-change so we re-apply light after ThemeProvider runs (e.g. after localStorage load).
 * Renders nothing.
 */
export function LandingThemeGuard() {
  const { pathname } = useLocation()
  const isLanding = isLandingPath(pathname)

  // Run before paint so landing never flashes dark
  useLayoutEffect(() => {
    const root = document.documentElement
    if (isLanding) {
      applyLandingLight()
    } else {
      const resolved = getResolvedTheme()
      root.classList.remove('light', 'dark')
      root.classList.add(resolved)
      root.setAttribute('data-theme', resolved)
    }
  }, [isLanding])

  // Re-apply light when ThemeProvider updates the document (e.g. after loading theme from localStorage)
  useEffect(() => {
    if (!isLanding) return
    const handler = () => applyLandingLight()
    window.addEventListener('theme-change', handler)
    return () => window.removeEventListener('theme-change', handler)
  }, [isLanding])

  return null
}
