import React from 'react'
import { BrowserRouter as Router } from 'react-router-dom'
import { ErrorBoundary } from './components/ErrorBoundary'
import { ThemeProvider } from './contexts/ThemeContext'
import { CustomizationProvider } from './contexts/CustomizationContext'
import { ActivityProvider } from './contexts/ActivityContext'
import { AuthProvider } from './contexts/AuthContext'

function App() {
  try {
    return (
      <ErrorBoundary>
        <Router>
          <ThemeProvider>
            <CustomizationProvider>
              <ActivityProvider>
                <AuthProvider>
                  <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                    <div className="text-center">
                      <h1 className="text-4xl font-bold text-gray-900 mb-4">
                        Fikiri Solutions
                      </h1>
                      <p className="text-xl text-gray-600 mb-4">
                        Added AuthProvider - testing incrementally
                      </p>
                      <p className="text-sm text-gray-500">
                        Test deployment - {new Date().toISOString()}
                      </p>
                    </div>
                  </div>
                </AuthProvider>
              </ActivityProvider>
            </CustomizationProvider>
          </ThemeProvider>
        </Router>
      </ErrorBoundary>
    )
  } catch (error) {
    console.error('App component error:', error)
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center p-8">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Application Error</h1>
          <p className="text-gray-600 mb-4">Failed to initialize the application</p>
          <p className="text-sm text-gray-500">Error: {error.message}</p>
          <button 
            onClick={() => window.location.reload()} 
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Reload Page
          </button>
        </div>
      </div>
    )
  }
}

export default App
