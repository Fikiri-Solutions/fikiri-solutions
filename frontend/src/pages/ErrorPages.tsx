import React from 'react'
import { Link } from 'react-router-dom'
import { Home, RefreshCw, AlertTriangle, Search } from 'lucide-react'

export const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="text-center">
          <Search className="mx-auto h-24 w-24 text-gray-400" />
          <h1 className="mt-6 text-3xl font-bold text-gray-900">Page Not Found</h1>
          <p className="mt-2 text-sm text-gray-600">
            Sorry, we couldn't find the page you're looking for.
          </p>
          <div className="mt-6">
            <Link
              to="/"
              className="fikiri-button inline-flex items-center"
            >
              <Home className="h-4 w-4 mr-2" />
              Back to Dashboard
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

export const ErrorPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="text-center">
          <AlertTriangle className="mx-auto h-24 w-24 text-red-400" />
          <h1 className="mt-6 text-3xl font-bold text-gray-900">Something went wrong</h1>
          <p className="mt-2 text-sm text-gray-600">
            We're experiencing some technical difficulties. Please try again.
          </p>
          <div className="mt-6 space-y-3">
            <button
              onClick={() => window.location.reload()}
              className="fikiri-button inline-flex items-center mr-3"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Try Again
            </button>
            <Link
              to="/"
              className="btn-secondary inline-flex items-center"
            >
              <Home className="h-4 w-4 mr-2" />
              Back to Dashboard
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
