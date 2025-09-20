import React from 'react'
import * as Sentry from '@sentry/react'

// Sentry Test Component for error tracking
export const SentryTestButton: React.FC = () => {
  const handleErrorTest = () => {
    // This will trigger a Sentry error for testing
    throw new Error('This is your first React error!')
  }

  const handlePerformanceTest = () => {
    // Test performance monitoring
    Sentry.startSpan(
      {
        op: "ui.click",
        name: "Sentry Performance Test",
      },
      (span) => {
        span.setAttribute("test_type", "performance")
        span.setAttribute("component", "SentryTestButton")
        
        // Simulate some work
        setTimeout(() => {
          console.log('Performance test completed')
        }, 100)
      },
    )
  }

  const handleLogTest = () => {
    // Test logging
    const { logger } = Sentry
    logger.info("Sentry log test", { 
      component: "SentryTestButton",
      timestamp: new Date().toISOString()
    })
    console.log('Log test completed - check Sentry logs')
  }

  return (
    <div className="p-6 bg-white rounded-lg shadow-md border border-gray-200">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        🎯 Sentry Integration Test
      </h3>
      
      <div className="space-y-3">
        <button
          onClick={handleErrorTest}
          className="w-full px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
        >
          🚨 Test Error Tracking
        </button>
        
        <button
          onClick={handlePerformanceTest}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          ⚡ Test Performance Monitoring
        </button>
        
        <button
          onClick={handleLogTest}
          className="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
        >
          📝 Test Logging
        </button>
      </div>
      
      <div className="mt-4 p-3 bg-gray-50 rounded-md">
        <p className="text-sm text-gray-600">
          <strong>Instructions:</strong> Click each button to test different Sentry features. 
          Check your Sentry dashboard to see the results.
        </p>
      </div>
    </div>
  )
}

// Sentry Error Boundary Component
export const SentryErrorBoundary: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <Sentry.ErrorBoundary
      fallback={({ error, resetError }) => (
        <div className="p-6 bg-red-50 border border-red-200 rounded-lg">
          <h2 className="text-lg font-semibold text-red-800 mb-2">
            🚨 Something went wrong
          </h2>
          <p className="text-red-600 mb-4">
            An error occurred: {error?.message}
          </p>
          <button
            onClick={resetError}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
          >
            Try again
          </button>
        </div>
      )}
      beforeCapture={(scope, error, errorInfo) => {
        scope.setTag("errorBoundary", true)
        scope.setContext("errorInfo", errorInfo)
      }}
    >
      {children}
    </Sentry.ErrorBoundary>
  )
}

export default SentryTestButton
