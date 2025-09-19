import React from 'react'
import { Layout } from '../components/Layout'

export const About: React.FC = () => {
  return (
    <Layout>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Header */}
          <div className="text-center mb-12">
            <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
              About Fikiri Solutions
            </h1>
            <p className="text-xl text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
              AI-Powered Business Automation Platform
            </p>
          </div>

          {/* Business Information */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8 mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-6">
              Business Information
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                  Company Details
                </h3>
                <div className="space-y-3">
                  <div>
                    <span className="font-medium text-gray-700 dark:text-gray-300">Business Name:</span>
                    <p className="text-gray-900 dark:text-white">Fikiri Solutions</p>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700 dark:text-gray-300">Industry:</span>
                    <p className="text-gray-900 dark:text-white">AI-Powered Business Automation</p>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700 dark:text-gray-300">Website:</span>
                    <p className="text-gray-900 dark:text-white">https://fikirisolutions.com</p>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                  Contact Information
                </h3>
                <div className="space-y-3">
                  <div>
                    <span className="font-medium text-gray-700 dark:text-gray-300">Business Address:</span>
                    <p className="text-gray-900 dark:text-white">
                      4521 Northwest 25th Street<br />
                      Lauderhill, FL 33313<br />
                      United States
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Services */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8 mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-6">
              Our Services
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center">
                <div className="bg-blue-100 dark:bg-blue-900 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl">📧</span>
                </div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  Email Automation
                </h3>
                <p className="text-gray-600 dark:text-gray-300">
                  AI-powered email processing and response automation
                </p>
              </div>
              
              <div className="text-center">
                <div className="bg-green-100 dark:bg-green-900 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl">👥</span>
                </div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  CRM Management
                </h3>
                <p className="text-gray-600 dark:text-gray-300">
                  Customer relationship management and lead tracking
                </p>
              </div>
              
              <div className="text-center">
                <div className="bg-purple-100 dark:bg-purple-900 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl">🤖</span>
                </div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  AI Assistant
                </h3>
                <p className="text-gray-600 dark:text-gray-300">
                  Intelligent business automation and analytics
                </p>
              </div>
            </div>
          </div>

          {/* Specializations */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8">
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-6">
              Industry Specializations
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  Landscaping
                </h3>
                <p className="text-gray-600 dark:text-gray-300">
                  Automated client communication and project management
                </p>
              </div>
              
              <div className="text-center p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  Restaurants
                </h3>
                <p className="text-gray-600 dark:text-gray-300">
                  Order management and customer service automation
                </p>
              </div>
              
              <div className="text-center p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  Medical Practices
                </h3>
                <p className="text-gray-600 dark:text-gray-300">
                  Patient communication and appointment scheduling
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  )
}
