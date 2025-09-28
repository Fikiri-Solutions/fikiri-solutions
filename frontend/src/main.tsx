import React from 'react'
import ReactDOM from 'react-dom/client'
// import * as Sentry from '@sentry/react'
import App from './App.incremental'
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

// Add error handling for React rendering
try {
  const rootElement = document.getElementById('root')
  if (!rootElement) {
    throw new Error('Root element not found')
  }
  
  const root = ReactDOM.createRoot(rootElement)
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  )
} catch (error) {
  console.error('React rendering error:', error)
  // Fallback: show error message in the DOM
  const rootElement = document.getElementById('root')
  if (rootElement) {
    rootElement.innerHTML = `
      <div style="padding: 20px; text-align: center; font-family: Arial, sans-serif;">
        <h1>Application Error</h1>
        <p>Failed to load the application: ${error.message}</p>
        <p>Please check the console for more details.</p>
      </div>
    `
  }
}

