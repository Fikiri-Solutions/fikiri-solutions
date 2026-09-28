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
  // Do NOT use injectRegister: 'script' — that path never enables skipWaiting/clientsClaim
  // in vite-plugin-pwa, so new deploys sat in "waiting" and users kept stale UI.
  // Registration happens from main.tsx via virtual:pwa-register.
  injectRegister: false,
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
    // Explicit: injectRegister false skips the plugin's autoUpdate skipWaiting wiring.
    skipWaiting: true,
    clientsClaim: true,
    cleanupOutdatedCaches: true,
    // Serve document navigations from the network so new deploys are not stuck
    // behind a precached index.html (hashed asset refs update with the HTML).
    navigateFallback: null,
    // Keep hashed static assets in the precache; omit html so shells stay fresh.
    globPatterns: ['**/*.{js,css,ico,png,svg,webp,avif}'],
    // Reload open tabs when this SW activates (covers browsers still on the old
    // bare registerSW.js that never messaged SKIP_WAITING).
    importScripts: ['sw-claim-reload.js'],
    // Do not runtime-cache backend API responses (authenticated JSON, user-specific data).
    runtimeCaching: []
  },
  // PWA is only enabled in production builds (see vite.config.mts)
})
