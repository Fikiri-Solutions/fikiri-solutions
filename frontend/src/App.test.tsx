import React from 'react'

function App() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Fikiri Solutions
        </h1>
        <p className="text-xl text-gray-600">
          React app is loading successfully!
        </p>
        <p className="text-sm text-gray-500 mt-2">
          Test deployment - {new Date().toISOString()}
        </p>
      </div>
    </div>
  )
}

export default App