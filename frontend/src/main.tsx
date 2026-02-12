import React from 'react'
import ReactDOM from 'react-dom/client'
// import * as Sentry from '@sentry/react'
import App from './App'
import './index.css'
// import { initializeCacheInvalidation } from './utils/cacheInvalidation'

// Initialize Sentry before anything else
// Sentry.init({
//   dsn: "https://873129f9208963cbc42cfff06ed073e4@o4510053728845824.ingest.us.sentry.io/4510053804802048",
//   // Setting this option to true will send default PII data to Sentry.
//   // For example, automatic IP address collection on events
//   sendDefaultPii: true,
//   // Performance monitoring
//   tracesSampleRate: 0.1, // 10% of transactions for performance monitoring
//   // Environment
//   environment: import.meta.env.MODE || 'production',
//   // Enable logging
//   enableLogs: true,
//   // Integrations
//   integrations: [
//     // Send console.log, console.warn, and console.error calls as logs to Sentry
//     Sentry.consoleLoggingIntegration({ levels: ["log", "warn", "error"] }),
//   ],
// })

// Initialize cache invalidation before app starts
// initializeCacheInvalidation()

// Immediately unregister service workers in development mode to prevent caching issues
// This must run before React renders to prevent workbox from intercepting requests
if (import.meta.env.DEV || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
  if ('serviceWorker' in navigator) {
    // Unregister all service workers immediately
    navigator.serviceWorker.getRegistrations().then((registrations) => {
      Promise.all(
        registrations.map((registration) => {
          console.log(`[Dev] Unregistering service worker: ${registration.scope}`)
          return registration.unregister()
        })
      ).then(() => {
        console.log(`[Dev] Unregistered ${registrations.length} service worker(s)`)
      })
    })
    
    // Clear all caches
    if ('caches' in window) {
      caches.keys().then((cacheNames) => {
        Promise.all(
          cacheNames.map((cacheName) => {
            console.log(`[Dev] Deleting cache: ${cacheName}`)
            return caches.delete(cacheName)
          })
        ).then(() => {
          console.log(`[Dev] Cleared ${cacheNames.length} cache(s)`)
        })
      })
    }
    
    // Prevent new service workers from registering
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (navigator.serviceWorker.controller) {
        console.log('[Dev] Service worker controller changed, unregistering...')
        navigator.serviceWorker.controller.postMessage({ type: 'SKIP_WAITING' })
        navigator.serviceWorker.getRegistrations().then((registrations) => {
          registrations.forEach(reg => reg.unregister())
        })
      }
    })
    
    // Also listen for new service worker registrations and immediately unregister them
    navigator.serviceWorker.addEventListener('message', (event) => {
      console.log('[Dev] Service worker message received, unregistering...')
      navigator.serviceWorker.getRegistrations().then((registrations) => {
        registrations.forEach(reg => reg.unregister())
      })
    })
  }
}

const root = ReactDOM.createRoot(document.getElementById('root')!)
root.render(
  <App />
)

