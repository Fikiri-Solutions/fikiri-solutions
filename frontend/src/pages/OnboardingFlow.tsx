import React, { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { CheckCircle, ArrowRight, ArrowLeft, Mail, Users, Brain, Settings, Loader2, AlertCircle, Zap, Database, Shield } from 'lucide-react'
import { GmailConnection } from '../components/GmailConnection'
import { SyncProgress } from '../components/SyncProgress'
// import { useUserActivityTracking } from '../contexts/ActivityContext'

interface OnboardingData {
  businessName: string
  businessEmail: string
  industry: string
  teamSize: string
  services: string[]
}

interface User {
  id: number
  email: string
  name: string
  onboarding_completed: boolean
  onboarding_step: number
}

interface OnboardingJob {
  status: string
  current_step: string
  progress: number
  started_at: string
  completed_at?: string
  error_message?: string
}

export const OnboardingFlow: React.FC = () => {
  const navigate = useNavigate()
  const { step } = useParams<{ step: string }>()
  const [currentStep, setCurrentStep] = useState(parseInt(step || '1'))
  // const { trackOnboardingStart, trackOnboardingComplete, trackServiceConfiguration } = useUserActivityTracking()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [gmailConnected, setGmailConnected] = useState(false)
  const [onboardingJob, setOnboardingJob] = useState<OnboardingJob | null>(null)
  const [formData, setFormData] = useState<OnboardingData>({
    businessName: '',
    businessEmail: '',
    industry: '',
    teamSize: '',
    services: []
  })

  // Load user data and onboarding status on component mount
  useEffect(() => {
    loadOnboardingStatus()
  }, [])

  // Poll for onboarding job status
  useEffect(() => {
    if (currentStep >= 3 && user) {
      const interval = setInterval(() => {
        pollOnboardingStatus()
      }, 2000)
      return () => clearInterval(interval)
    }
  }, [currentStep, user])

  const loadOnboardingStatus = async () => {
    try {
      const userId = localStorage.getItem('fikiri-user-id')
      if (!userId) {
        navigate('/login')
        return
      }

      // Load onboarding summary
      const response = await fetch(`https://fikirisolutions.onrender.com/api/onboarding/summary?user_id=${userId}`)
      const data = await response.json()
      
      if (data.success) {
        setUser(data.data.user)
        setGmailConnected(data.data.gmail_connected)
        
        // Track onboarding start
        // trackOnboardingStart(data.data.user.email, `Step ${data.data.user.onboarding_step || 1}`)
        
        // If user has completed onboarding, redirect to dashboard
        if (data.data.user.onboarding_completed) {
          // trackOnboardingComplete(data.data.user.email, data.data.user.onboarding_step)
          navigate('/')
          return
        }
        
        // Set current step based on user's progress
        setCurrentStep(data.data.user.onboarding_step || 1)
      }
    } catch (error) {
      setError('Failed to load onboarding status')
    }
  }

  const pollOnboardingStatus = async () => {
    if (!user) return

    try {
      const response = await fetch(`https://fikirisolutions.onrender.com/api/onboarding/status?user_id=${user.id}`)
      const data = await response.json()
      
      if (data.success) {
        setOnboardingJob(data.data)
        
        // If job is completed, move to next step
        if (data.data.status === 'completed' && currentStep === 3) {
          setCurrentStep(4)
          navigate('/onboarding/4')
        } else if (data.data.status === 'failed') {
          setError(data.data.error_message || 'Onboarding failed')
        }
      }
    } catch (error) {
      console.error('Error polling onboarding status:', error)
    }
  }

  const updateOnboardingStep = async (step: number) => {
    if (!user) return

    try {
      const response = await fetch('https://fikirisolutions.onrender.com/api/onboarding/update', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: user.id,
          step: step,
          completed: step === 5
        })
      })

      const data = await response.json()
      if (data.success) {
        setCurrentStep(step)
        setUser(data.data.user)
      }
    } catch (error) {
      setError('Failed to update onboarding progress')
    }
  }

  const startOnboardingJob = async () => {
    if (!user) return

    try {
      setIsLoading(true)
      const response = await fetch('https://fikirisolutions.onrender.com/api/onboarding/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: user.id
        })
      })

      const data = await response.json()
      if (data.success) {
        // Start polling for job status
        pollOnboardingStatus()
      } else {
        throw new Error(data.error || 'Failed to start onboarding job')
      }
    } catch (error) {
      setError('Failed to start onboarding process')
    } finally {
      setIsLoading(false)
    }
  }

  const handleNext = async () => {
    if (currentStep === 1) {
      // Update business information
      await updateBusinessInfo()
      updateOnboardingStep(2)
      navigate('/onboarding/2')
    } else if (currentStep === 2) {
      // Gmail connection is handled by GmailConnection component
      // This will be called when Gmail is connected
    } else if (currentStep === 3) {
      // Start onboarding job
      await startOnboardingJob()
    } else if (currentStep === 4) {
      // Update services
      await updateServices()
      updateOnboardingStep(5)
      navigate('/onboarding/5')
    } else if (currentStep === 5) {
      // Complete onboarding
      navigate('/')
    }
  }

  const handlePrevious = () => {
    if (currentStep > 1) {
      const prevStep = currentStep - 1
      setCurrentStep(prevStep)
      navigate(`/onboarding/${prevStep}`)
    }
  }

  const updateBusinessInfo = async () => {
    if (!user) return

    try {
      const response = await fetch('https://fikirisolutions.onrender.com/api/user/profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: user.id,
          business_name: formData.businessName,
          business_email: formData.businessEmail,
          industry: formData.industry,
          team_size: formData.teamSize
        })
      })

      const data = await response.json()
      if (!data.success) {
        throw new Error(data.error || 'Failed to update business information')
      }
    } catch (error) {
      throw new Error('Failed to update business information')
    }
  }

  const updateServices = async () => {
    if (!user) return

    try {
      // Record privacy consent for data processing
      await fetch('https://fikirisolutions.onrender.com/api/privacy/consent', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: user.id,
          consent_type: 'data_processing',
          granted: true,
          consent_text: 'I consent to Fikiri Solutions processing my business data for AI-powered automation, lead management, and service improvement purposes.'
        })
      })

      // Record analytics consent
      await fetch('https://fikirisolutions.onrender.com/api/privacy/consent', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: user.id,
          consent_type: 'analytics',
          granted: true,
          consent_text: 'I consent to Fikiri Solutions collecting usage analytics to improve service quality and develop new features.'
        })
      })

      // Store selected services in user metadata
      const response = await fetch('https://fikirisolutions.onrender.com/api/user/profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: user.id,
          metadata: JSON.stringify({ selected_services: formData.services })
        })
      })

      const data = await response.json()
      if (!data.success) {
        throw new Error(data.error || 'Failed to update services')
      }
    } catch (error) {
      throw new Error('Failed to update services and privacy consents')
    }
  }

  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="space-y-6">
            <div className="text-center">
              <div className="mx-auto w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
                <Users className="h-8 w-8 text-blue-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Tell us about your business</h2>
              <p className="text-gray-600">Help us customize Fikiri for your industry</p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Business Name
                </label>
                <input
                  type="text"
                  value={formData.businessName}
                  onChange={(e) => setFormData({ ...formData, businessName: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Acme Corporation"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Business Email
                </label>
                <input
                  type="email"
                  value={formData.businessEmail}
                  onChange={(e) => setFormData({ ...formData, businessEmail: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="hello@acme.com"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Industry
                </label>
                <select
                  value={formData.industry}
                  onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">Select your industry</option>
                  <option value="landscaping">Landscaping</option>
                  <option value="restaurant">Restaurant</option>
                  <option value="medical">Medical</option>
                  <option value="consulting">Consulting</option>
                  <option value="real-estate">Real Estate</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Team Size
                </label>
                <select
                  value={formData.teamSize}
                  onChange={(e) => setFormData({ ...formData, teamSize: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">Select team size</option>
                  <option value="1-5">1-5 people</option>
                  <option value="6-20">6-20 people</option>
                  <option value="21-50">21-50 people</option>
                  <option value="50+">50+ people</option>
                </select>
              </div>
            </div>
          </div>
        )

      case 2:
        return (
          <GmailConnection 
            userId={user?.id || 0} 
            onConnected={() => {
              setGmailConnected(true)
              updateOnboardingStep(3)
              navigate('/onboarding/3')
            }} 
          />
        )

      case 3:
        return (
          <div className="space-y-6">
            <div className="text-center">
              <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
                <Database className="h-8 w-8 text-green-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Setting up your workspace</h2>
              <p className="text-gray-600">We're preparing your dashboard with your data</p>
            </div>

            {onboardingJob ? (
              <div className="space-y-4">
                {/* Progress Bar */}
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className="bg-blue-600 h-3 rounded-full transition-all duration-500"
                    style={{ width: `${onboardingJob.progress}%` }}
                  />
                </div>
                
                <div className="text-center">
                  <p className="text-sm text-gray-600">
                    {onboardingJob.progress}% complete - {onboardingJob.current_step}
                  </p>
                </div>

                {/* Step Indicators */}
                <div className="space-y-3">
                  <div className="flex items-center">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center mr-3 ${
                      onboardingJob.progress >= 25 ? 'bg-green-100' : 'bg-gray-100'
                    }`}>
                      {onboardingJob.progress >= 25 ? (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      ) : (
                        <Database className="h-4 w-4 text-gray-400" />
                      )}
                    </div>
                    <span className="text-sm text-gray-700">Syncing Gmail emails</span>
                  </div>

                  <div className="flex items-center">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center mr-3 ${
                      onboardingJob.progress >= 50 ? 'bg-green-100' : 'bg-gray-100'
                    }`}>
                      {onboardingJob.progress >= 50 ? (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      ) : (
                        <Users className="h-4 w-4 text-gray-400" />
                      )}
                    </div>
                    <span className="text-sm text-gray-700">Extracting leads and contacts</span>
                  </div>

                  <div className="flex items-center">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center mr-3 ${
                      onboardingJob.progress >= 75 ? 'bg-green-100' : 'bg-gray-100'
                    }`}>
                      {onboardingJob.progress >= 75 ? (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      ) : (
                        <Zap className="h-4 w-4 text-gray-400" />
                      )}
                    </div>
                    <span className="text-sm text-gray-700">Creating starter automations</span>
                  </div>

                  <div className="flex items-center">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center mr-3 ${
                      onboardingJob.progress >= 100 ? 'bg-green-100' : 'bg-gray-100'
                    }`}>
                      {onboardingJob.progress >= 100 ? (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      ) : (
                        <Settings className="h-4 w-4 text-gray-400" />
                      )}
                    </div>
                    <span className="text-sm text-gray-700">Preparing your dashboard</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center">
                <button
                  onClick={startOnboardingJob}
                  disabled={isLoading}
                  className="bg-blue-600 text-white px-8 py-4 rounded-lg font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center mx-auto"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="animate-spin h-5 w-5 mr-2" />
                      Starting...
                    </>
                  ) : (
                    <>
                      Start Setup
                      <ArrowRight className="h-5 w-5 ml-2" />
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        )

      case 4:
        return (
          <div className="space-y-6">
            <div className="text-center">
              <div className="mx-auto w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mb-4">
                <Settings className="h-8 w-8 text-purple-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Choose your services</h2>
              <p className="text-gray-600">Select the features you'd like to use</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                { id: 'ai-assistant', name: 'AI Assistant', description: 'Natural language email management', icon: Brain },
                { id: 'crm', name: 'CRM', description: 'Lead and contact management', icon: Users },
                { id: 'automation', name: 'Automation', description: 'Automated email responses', icon: Zap },
                { id: 'analytics', name: 'Analytics', description: 'Email performance insights', icon: Settings }
              ].map((service) => (
                <div
                  key={service.id}
                  className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                    formData.services.includes(service.id)
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => {
                    const newServices = formData.services.includes(service.id)
                      ? formData.services.filter(s => s !== service.id)
                      : [...formData.services, service.id]
                    setFormData({ ...formData, services: newServices })
                  }}
                >
                  <div className="flex items-center">
                    <div className={`w-4 h-4 rounded border-2 mr-3 ${
                      formData.services.includes(service.id)
                        ? 'border-blue-500 bg-blue-500'
                        : 'border-gray-300'
                    }`}>
                      {formData.services.includes(service.id) && (
                        <CheckCircle className="h-4 w-4 text-white" />
                      )}
                    </div>
                    <div className="flex items-center">
                      <service.icon className="h-5 w-5 text-gray-400 mr-3" />
                      <div>
                        <h3 className="font-medium text-gray-900">{service.name}</h3>
                        <p className="text-sm text-gray-600">{service.description}</p>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )

      case 5:
        return (
          <div className="space-y-6">
            <div className="text-center">
              <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
                <CheckCircle className="h-8 w-8 text-green-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">You're all set!</h2>
              <p className="text-gray-600">Welcome to Fikiri Solutions</p>
            </div>

            <div className="bg-green-50 border border-green-200 rounded-lg p-6">
              <h3 className="font-semibold text-green-900 mb-2">What's next?</h3>
              <ul className="text-sm text-green-800 space-y-2">
                <li>• Explore your dashboard</li>
                <li>• Try asking the AI Assistant: "Who emailed me last?"</li>
                <li>• Review your leads in the CRM</li>
                <li>• Set up your first automation</li>
              </ul>
            </div>
          </div>
        )

      default:
        return null
    }
  }

  const getStepTitle = () => {
    switch (currentStep) {
      case 1: return 'Business Information'
      case 2: return 'Connect Gmail'
      case 3: return 'Setting Up Workspace'
      case 4: return 'Choose Services'
      case 5: return 'Complete'
      default: return 'Onboarding'
    }
  }

  const canProceed = () => {
    switch (currentStep) {
      case 1:
        return formData.businessName && formData.businessEmail && formData.industry && formData.teamSize
      case 2:
        return gmailConnected
      case 3:
        return onboardingJob?.status === 'completed'
      case 4:
        return formData.services.length > 0
      case 5:
        return true
      default:
        return false
    }
  }

  if (isLoading && !onboardingJob) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Welcome to Fikiri</h1>
              <p className="text-gray-600">Let's get you set up</p>
            </div>
            <div className="text-sm text-gray-500">
              Step {currentStep} of 5
            </div>
          </div>
          
          {/* Progress Bar */}
          <div className="mt-4">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                style={{ width: `${(currentStep / 5) * 100}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Error Message */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center">
              <AlertCircle className="h-5 w-5 text-red-400 mr-3" />
              <p className="text-sm text-red-800">{error}</p>
            </div>
          </div>
        )}

        {/* Step Content */}
        <div className="bg-white rounded-lg border border-gray-200 p-8">
          {renderStepContent()}
        </div>

        {/* Navigation */}
        {currentStep < 5 && (
          <div className="flex justify-between mt-8">
            <button
              onClick={handlePrevious}
              disabled={currentStep === 1}
              className="px-6 py-3 border border-gray-300 rounded-lg font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Previous
            </button>

            <button
              onClick={handleNext}
              disabled={!canProceed() || isLoading}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              {isLoading ? (
                <>
                  <Loader2 className="animate-spin h-4 w-4 mr-2" />
                  Loading...
                </>
              ) : (
                <>
                  {currentStep === 5 ? 'Complete' : 'Next'}
                  <ArrowRight className="h-4 w-4 ml-2" />
                </>
              )}
            </button>
          </div>
        )}

        {/* Support Link */}
        <div className="text-center mt-6">
          <a
            href="mailto:support@fikirisolutions.com"
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            Need help? Contact Support
          </a>
        </div>
      </div>
    </div>
  )
}
