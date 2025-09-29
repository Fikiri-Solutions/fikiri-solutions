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

const root = ReactDOM.createRoot(document.getElementById('root')!)
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)

