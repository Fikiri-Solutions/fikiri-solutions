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
    // Do not emit sw.js.map or advertise //# sourceMappingURL in production output.
    sourcemap: false,
    globPatterns: ['**/*.{js,css,html,ico,png,svg,webp,avif}'],
    // Do not runtime-cache backend API responses (authenticated JSON, user-specific data).
    // Static assets are precached via globPatterns above; API calls always go network-only.
    runtimeCaching: []
  },
  // PWA is only enabled in production builds (see vite.config.mts)
  // No devOptions needed since plugin is conditionally included
})
