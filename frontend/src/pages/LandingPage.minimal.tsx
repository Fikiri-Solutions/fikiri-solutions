import React from 'react'

const LandingPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-orange-900/30 to-red-900/30 text-white flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-6xl font-bold mb-6 bg-gradient-to-r from-orange-400 via-orange-500 to-red-600 bg-clip-text text-transparent">
          Fikiri Solutions
        </h1>
        <p className="text-2xl text-white mb-8">
          The platform for reliable automation
        </p>
        <p className="text-lg text-orange-300">
          Save time, close more leads, and automate your workflows
        </p>
        <div className="mt-8">
          <button 
            onClick={() => window.location.href = '/onboarding-flow'}
            className="px-8 py-4 bg-gradient-to-r from-orange-600 to-red-600 text-white font-semibold rounded-lg hover:from-orange-700 hover:to-red-700 transition-all duration-300 transform hover:scale-105"
          >
            Get Started Free
          </button>
        </div>
      </div>
    </div>
  )
}

export default LandingPage
