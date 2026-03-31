/**
 * Progressive Web App (PWA) Configuration
 * Service worker, manifest, and offline capabilities
 */

import { VitePWA } from 'vite-plugin-pwa'

export const pwaConfig = VitePWA({
  registerType: 'autoUpdate',
  // Emit /manifest.json so the browser finds a single canonical web app manifest (no Rollup conflict).
  manifestFilename: 'manifest.json',
  includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'masked-icon.png'],
  // Disable automatic prefetch/preload generation to prevent wildcard issues
  injectRegister: 'script',
  strategies: 'generateSW',
  manifest: {
    name: 'Fikiri Solutions - AI Email Automation',
    short_name: 'Fikiri Solutions',
    description: 'Industry-specific AI automation for emails, leads, and workflows',
    theme_color: '#2563eb',
    background_color: '#ffffff',
    display: 'standalone',
    orientation: 'portrait',
    scope: '/',
    start_url: '/',
    icons: [
      {
        src: 'pwa-192x192.png',
        sizes: '192x192',
        type: 'image/png'
      },
      {
        src: 'pwa-512x512.png',
        sizes: '512x512',
        type: 'image/png'
      },
      {
        src: 'pwa-512x512.png',
        sizes: '512x512',
        type: 'image/png',
        purpose: 'any maskable'
      }
    ],
    categories: ['business', 'productivity', 'utilities'],
    lang: 'en-US',
    dir: 'ltr'
  },
  workbox: {
    globPatterns: ['**/*.{js,css,html,ico,png,svg,webp,avif}'],
    runtimeCaching: [
      {
        urlPattern: /^https:\/\/fikirisolutions\.onrender\.com\/.*/i,
        handler: 'NetworkFirst',
        options: {
          cacheName: 'api-cache',
          expiration: {
            maxEntries: 100,
            maxAgeSeconds: 60 * 5 // 5 minutes for API calls
          },
          cacheableResponse: {
            statuses: [0, 200]
          }
        }
      },
      // Fonts are loaded via <link> in the document; do not intercept in the SW.
      // Intercepting with Workbox fetch() requires connect-src to allow fonts.googleapis.com/gstatic
      // for the service worker scope, which is brittle across CSP updates.
    ]
  },
  // PWA is only enabled in production builds (see vite.config.mts)
  // No devOptions needed since plugin is conditionally included
})
