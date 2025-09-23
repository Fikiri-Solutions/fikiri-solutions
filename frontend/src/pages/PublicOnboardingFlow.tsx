import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle, ArrowRight, ArrowLeft, Loader2 } from 'lucide-react'
import { useToast } from '../components/Toast'

interface OnboardingData {
  businessName: string
  businessEmail: string
  industry: string
  teamSize: string
  services: string[]
  privacyConsent: boolean
  termsAccepted: boolean
  marketingConsent: boolean
}

interface ValidationErrors {
  businessName?: string
  businessEmail?: string
  industry?: string
  teamSize?: string
  privacyConsent?: string
  termsAccepted?: string
}

export const PublicOnboardingFlow: React.FC = () => {
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(1)
  const { addToast } = useToast()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({})
  const [formData, setFormData] = useState<OnboardingData>({
    businessName: '',
    businessEmail: '',
    industry: '',
    teamSize: '',
    services: [],
    privacyConsent: false,
    termsAccepted: false,
    marketingConsent: false
  })

  // Security: Input sanitization
  const sanitizeInput = (input: string): string => {
    return input.trim().replace(/[<>]/g, '')
  }

  // Validation functions
  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return emailRegex.test(email)
  }

  const validateBusinessName = (name: string): boolean => {
    return name.length >= 2 && name.length <= 100 && /^[a-zA-Z0-9\s\-&.,'()]+$/.test(name)
  }

  const validateStep = (step: number): boolean => {
    const errors: ValidationErrors = {}

    switch (step) {
      case 1:
        if (!formData.businessName || !validateBusinessName(formData.businessName)) {
          errors.businessName = 'Please enter a valid business name (2-100 characters)'
        }
        if (!formData.businessEmail || !validateEmail(formData.businessEmail)) {
          errors.businessEmail = 'Please enter a valid business email address'
        }
        if (!formData.industry) {
          errors.industry = 'Please select your industry'
        }
        if (!formData.teamSize) {
          errors.teamSize = 'Please select your team size'
        }
        if (!formData.privacyConsent) {
          errors.privacyConsent = 'You must accept the privacy policy to continue'
        }
        if (!formData.termsAccepted) {
          errors.termsAccepted = 'You must accept the terms of service to continue'
        }
        break
    }

    setValidationErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleNext = async () => {
    if (!validateStep(currentStep)) {
      addToast('Please fix the errors below before continuing.', 'error')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      if (currentStep === 1) {
        // Sanitize inputs before sending
        const sanitizedData = {
          ...formData,
          businessName: sanitizeInput(formData.businessName),
          businessEmail: sanitizeInput(formData.businessEmail)
        }
        
        // Store data in localStorage for later use
        localStorage.setItem('fikiri-onboarding-data', JSON.stringify(sanitizedData))
        
        // Move to next step
        setCurrentStep(2)
        addToast('Business information saved!', 'success')
      } else if (currentStep === 2) {
        // Move to services selection
        setCurrentStep(3)
      } else if (currentStep === 3) {
        // Complete onboarding and redirect to signup
        localStorage.setItem('fikiri-onboarding-completed', 'true')
        addToast('Welcome to Fikiri! Please create your account to continue.', 'success')
        navigate('/signup')
      }
    } catch (error) {
      console.error('Onboarding error:', error)
      setError(error instanceof Error ? error.message : 'An unexpected error occurred')
      addToast('Something went wrong. Please try again.', 'error')
    } finally {
      setIsLoading(false)
    }
  }

  const handlePrevious = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleInputChange = (field: keyof OnboardingData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    // Clear validation error for this field
    if (validationErrors[field as keyof ValidationErrors]) {
      setValidationErrors(prev => ({ ...prev, [field]: undefined }))
    }
  }

  const renderStep1 = () => (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Welcome to Fikiri Solutions
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          Let's get your business set up for success
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Business Name *
          </label>
          <input
            type="text"
            value={formData.businessName}
            onChange={(e) => handleInputChange('businessName', e.target.value)}
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              validationErrors.businessName ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
            } dark:bg-gray-800 dark:text-white`}
            placeholder="Enter your business name"
          />
          {validationErrors.businessName && (
            <p className="text-red-500 text-sm mt-1">{validationErrors.businessName}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Business Email *
          </label>
          <input
            type="email"
            value={formData.businessEmail}
            onChange={(e) => handleInputChange('businessEmail', e.target.value)}
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              validationErrors.businessEmail ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
            } dark:bg-gray-800 dark:text-white`}
            placeholder="Enter your business email"
          />
          {validationErrors.businessEmail && (
            <p className="text-red-500 text-sm mt-1">{validationErrors.businessEmail}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Industry *
          </label>
          <select
            value={formData.industry}
            onChange={(e) => handleInputChange('industry', e.target.value)}
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              validationErrors.industry ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
            } dark:bg-gray-800 dark:text-white`}
          >
            <option value="">Select your industry</option>
            <option value="landscaping">Landscaping & Lawn Care</option>
            <option value="restaurant">Restaurant & Food Service</option>
            <option value="medical">Medical & Healthcare</option>
            <option value="retail">Retail & E-commerce</option>
            <option value="professional">Professional Services</option>
            <option value="other">Other</option>
          </select>
          {validationErrors.industry && (
            <p className="text-red-500 text-sm mt-1">{validationErrors.industry}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Team Size *
          </label>
          <select
            value={formData.teamSize}
            onChange={(e) => handleInputChange('teamSize', e.target.value)}
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              validationErrors.teamSize ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
            } dark:bg-gray-800 dark:text-white`}
          >
            <option value="">Select team size</option>
            <option value="1">Just me</option>
            <option value="2-5">2-5 people</option>
            <option value="6-20">6-20 people</option>
            <option value="21-50">21-50 people</option>
            <option value="50+">50+ people</option>
          </select>
          {validationErrors.teamSize && (
            <p className="text-red-500 text-sm mt-1">{validationErrors.teamSize}</p>
          )}
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-start">
          <input
            type="checkbox"
            id="privacyConsent"
            checked={formData.privacyConsent}
            onChange={(e) => handleInputChange('privacyConsent', e.target.checked)}
            className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <label htmlFor="privacyConsent" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
            I agree to the{' '}
            <a href="/privacy" target="_blank" className="text-blue-600 hover:underline">
              Privacy Policy
            </a>{' '}
            *
          </label>
        </div>
        {validationErrors.privacyConsent && (
          <p className="text-red-500 text-sm">{validationErrors.privacyConsent}</p>
        )}

        <div className="flex items-start">
          <input
            type="checkbox"
            id="termsAccepted"
            checked={formData.termsAccepted}
            onChange={(e) => handleInputChange('termsAccepted', e.target.checked)}
            className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <label htmlFor="termsAccepted" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
            I agree to the{' '}
            <a href="/terms" target="_blank" className="text-blue-600 hover:underline">
              Terms of Service
            </a>{' '}
            *
          </label>
        </div>
        {validationErrors.termsAccepted && (
          <p className="text-red-500 text-sm">{validationErrors.termsAccepted}</p>
        )}

        <div className="flex items-start">
          <input
            type="checkbox"
            id="marketingConsent"
            checked={formData.marketingConsent}
            onChange={(e) => handleInputChange('marketingConsent', e.target.checked)}
            className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <label htmlFor="marketingConsent" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
            I'd like to receive marketing emails and updates
          </label>
        </div>
      </div>
    </div>
  )

  const renderStep2 = () => (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          What would you like to automate?
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          Select the services that interest you most
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[
          { id: 'email_automation', name: 'Email Automation', description: 'Automate customer communications' },
          { id: 'lead_management', name: 'Lead Management', description: 'Track and nurture leads' },
          { id: 'crm_integration', name: 'CRM Integration', description: 'Connect with your existing CRM' },
          { id: 'ai_assistant', name: 'AI Assistant', description: 'Get help with customer inquiries' },
          { id: 'analytics', name: 'Analytics', description: 'Track performance and insights' },
          { id: 'scheduling', name: 'Scheduling', description: 'Automate appointment booking' }
        ].map((service) => (
          <div
            key={service.id}
            className={`p-4 border rounded-lg cursor-pointer transition-colors ${
              formData.services.includes(service.id)
                ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                : 'border-gray-300 dark:border-gray-600 hover:border-gray-400'
            }`}
            onClick={() => {
              const newServices = formData.services.includes(service.id)
                ? formData.services.filter(s => s !== service.id)
                : [...formData.services, service.id]
              handleInputChange('services', newServices)
            }}
          >
            <h3 className="font-medium text-gray-900 dark:text-white">{service.name}</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">{service.description}</p>
          </div>
        ))}
      </div>
    </div>
  )

  const renderStep3 = () => (
    <div className="space-y-6 text-center">
      <div className="w-16 h-16 bg-green-100 dark:bg-green-900/20 rounded-full flex items-center justify-center mx-auto">
        <CheckCircle className="w-8 h-8 text-green-600 dark:text-green-400" />
      </div>
      
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          You're all set!
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mb-6">
          We've saved your preferences. Now let's create your account to get started.
        </p>
      </div>

      <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 text-left">
        <h3 className="font-medium text-gray-900 dark:text-white mb-2">What's next?</h3>
        <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
          <li>• Create your Fikiri account</li>
          <li>• Connect your Gmail for email automation</li>
          <li>• Set up your first automation workflows</li>
          <li>• Start growing your business with AI</li>
        </ul>
      </div>
    </div>
  )

  const renderCurrentStep = () => {
    switch (currentStep) {
      case 1:
        return renderStep1()
      case 2:
        return renderStep2()
      case 3:
        return renderStep3()
      default:
        return renderStep1()
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Progress indicator */}
        <div className="flex justify-center">
          <div className="flex space-x-2">
            {[1, 2, 3].map((step) => (
              <div
                key={step}
                className={`w-3 h-3 rounded-full ${
                  step <= currentStep ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'
                }`}
              />
            ))}
          </div>
        </div>

        {/* Main content */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8">
          {renderCurrentStep()}

          {/* Error message */}
          {error && (
            <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <p className="text-red-600 dark:text-red-400 text-sm">{error}</p>
            </div>
          )}

          {/* Navigation buttons */}
          <div className="mt-8 flex justify-between">
            <button
              onClick={handlePrevious}
              disabled={currentStep === 1}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                currentStep === 1
                  ? 'text-gray-400 cursor-not-allowed'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              <ArrowLeft className="w-4 h-4 inline mr-1" />
              Previous
            </button>

            <button
              onClick={handleNext}
              disabled={isLoading}
              className="px-6 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : currentStep === 3 ? (
                'Create Account'
              ) : (
                <>
                  Next
                  <ArrowRight className="w-4 h-4 ml-1" />
                </>
              )}
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center text-sm text-gray-500 dark:text-gray-400">
          <p>
            Already have an account?{' '}
            <a href="/login" className="text-blue-600 hover:underline">
              Sign in
            </a>
          </p>
        </div>
      </div>
    </div>
  )
}
