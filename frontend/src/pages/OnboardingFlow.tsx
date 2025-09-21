import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { CheckCircle, ArrowRight, ArrowLeft, Mail, Users, Brain, Settings, Loader2, AlertCircle, Zap, Database, Shield, Eye, EyeOff, Lock, AlertTriangle, Info, ExternalLink } from 'lucide-react'
import { GmailConnection } from '../components/GmailConnection'
import { SyncProgress } from '../components/SyncProgress'
import { useUserActivityTracking } from '../contexts/ActivityContext'
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

interface ValidationErrors {
  businessName?: string
  businessEmail?: string
  industry?: string
  teamSize?: string
  privacyConsent?: string
  termsAccepted?: string
}

export const OnboardingFlow: React.FC = () => {
  const navigate = useNavigate()
  const { step } = useParams<{ step: string }>()
  const [currentStep, setCurrentStep] = useState(parseInt(step || '1'))
  const { trackOnboardingStart, trackOnboardingComplete, trackServiceConfiguration } = useUserActivityTracking()
  const { addToast } = useToast()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [gmailConnected, setGmailConnected] = useState(false)
  const [onboardingJob, setOnboardingJob] = useState<OnboardingJob | null>(null)
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({})
  const [showPassword, setShowPassword] = useState(false)
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
        if (!validateBusinessName(formData.businessName)) {
          errors.businessName = 'Business name must be 2-100 characters and contain only letters, numbers, spaces, and common punctuation'
        }
        if (!validateEmail(formData.businessEmail)) {
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

  // Load user data and onboarding status on component mount
  useEffect(() => {
    loadOnboardingStatus()
  }, [])

  // Poll for onboarding job status with error handling
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

      // Security: Validate user ID format
      if (!/^\d+$/.test(userId)) {
        addToast('Invalid user session. Please log in again.', 'error')
        navigate('/login')
        return
      }

      // Load onboarding summary with timeout
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 10000) // 10 second timeout

      const response = await fetch(`https://fikirisolutions.onrender.com/api/onboarding/summary?user_id=${userId}`, {
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
        }
      })
      
      clearTimeout(timeoutId)
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      
      if (data.success) {
        setUser(data.data.user)
        setGmailConnected(data.data.gmail_connected)
        
        // Track onboarding start
        trackOnboardingStart(data.data.user.email, `Step ${data.data.user.onboarding_step || 1}`)
        
        // If user has completed onboarding, redirect to dashboard
        if (data.data.user.onboarding_completed) {
          trackOnboardingComplete(data.data.user.email, data.data.user.onboarding_step)
          navigate('/')
          return
        }
        
        // Set current step based on user's progress
        setCurrentStep(data.data.user.onboarding_step || 1)
      } else {
        throw new Error(data.error || 'Failed to load onboarding status')
      }
    } catch (error) {
      console.error('Error loading onboarding status:', error)
      if (error.name === 'AbortError') {
        addToast('Request timed out. Please check your connection and try again.', 'error')
      } else {
        addToast('Failed to load onboarding status. Please try again.', 'error')
      }
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
        
        if (data.data.status === 'completed') {
          updateOnboardingStep(4)
          navigate('/onboarding/4')
        } else if (data.data.status === 'failed') {
          setError(data.data.error_message || 'Onboarding job failed')
          addToast('Setup failed. Please try again or contact support.', 'error')
        }
      }
    } catch (error) {
      console.error('Error polling onboarding status:', error)
    }
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
        
        // Update business information
        await updateBusinessInfo(sanitizedData)
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
        localStorage.setItem('fikiri-onboarding-completed', 'true')
        trackOnboardingComplete(user?.email || 'unknown', currentStep)
        addToast('Welcome to Fikiri! Your workspace is ready.', 'success')
        navigate('/')
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
      const prevStep = currentStep - 1
      setCurrentStep(prevStep)
      navigate(`/onboarding/${prevStep}`)
    }
  }

  const updateBusinessInfo = async (data: OnboardingData) => {
    if (!user) return

    try {
      const response = await fetch('https://fikirisolutions.onrender.com/api/user/profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: user.id,
          business_name: data.businessName,
          business_email: data.businessEmail,
          industry: data.industry,
          team_size: data.teamSize
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const result = await response.json()
      if (!result.success) {
        throw new Error(result.error || 'Failed to update business information')
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
          consent_text: 'User consented to data processing during onboarding',
          marketing_consent: formData.marketingConsent
        })
      })

      // Update user services
      await fetch('https://fikirisolutions.onrender.com/api/user/services', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: user.id,
          services: formData.services
        })
      })

      trackServiceConfiguration(user.email, formData.services)
    } catch (error) {
      throw new Error('Failed to update services')
    }
  }

  const startOnboardingJob = async () => {
    if (!user) return

    try {
      const response = await fetch('https://fikirisolutions.onrender.com/api/onboarding/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: user.id
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      if (!data.success) {
        throw new Error(data.error || 'Failed to start onboarding job')
      }

      setOnboardingJob(data.data)
    } catch (error) {
      throw new Error('Failed to start onboarding job')
    }
  }

  const updateOnboardingStep = async (step: number) => {
    if (!user) return

    try {
      await fetch('https://fikirisolutions.onrender.com/api/user/onboarding-step', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: user.id,
          onboarding_step: step
        })
      })
    } catch (error) {
      console.error('Failed to update onboarding step:', error)
    }
  }

  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="space-y-6">
            <div className="text-center">
              <div className="mx-auto w-16 h-16 bg-brand-accent/10 rounded-full flex items-center justify-center mb-4">
                <Users className="h-8 w-8 text-brand-accent" />
              </div>
              <h2 className="text-2xl font-bold text-brand-text dark:text-white mb-2">Tell us about your business</h2>
              <p className="text-gray-600 dark:text-gray-400">Help us customize Fikiri for your industry and team size</p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-brand-text dark:text-white mb-2">
                  Business Name *
                </label>
                <input
                  type="text"
                  value={formData.businessName}
                  onChange={(e) => setFormData({ ...formData, businessName: sanitizeInput(e.target.value) })}
                  className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-brand-accent focus:border-brand-accent transition-colors ${
                    validationErrors.businessName 
                      ? 'border-red-500 bg-red-50 dark:bg-red-900/20' 
                      : 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700'
                  }`}
                  placeholder="Acme Corporation"
                  maxLength={100}
                />
                {validationErrors.businessName && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400">{validationErrors.businessName}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-brand-text dark:text-white mb-2">
                  Business Email *
                </label>
                <input
                  type="email"
                  value={formData.businessEmail}
                  onChange={(e) => setFormData({ ...formData, businessEmail: sanitizeInput(e.target.value) })}
                  className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-brand-accent focus:border-brand-accent transition-colors ${
                    validationErrors.businessEmail 
                      ? 'border-red-500 bg-red-50 dark:bg-red-900/20' 
                      : 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700'
                  }`}
                  placeholder="hello@acme.com"
                />
                {validationErrors.businessEmail && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400">{validationErrors.businessEmail}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-brand-text dark:text-white mb-2">
                  Industry *
                </label>
                <select
                  value={formData.industry}
                  onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
                  className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-brand-accent focus:border-brand-accent transition-colors ${
                    validationErrors.industry 
                      ? 'border-red-500 bg-red-50 dark:bg-red-900/20' 
                      : 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700'
                  }`}
                >
                  <option value="">Select your industry</option>
                  <option value="landscaping">Landscaping & Lawn Care</option>
                  <option value="restaurant">Restaurant & Food Service</option>
                  <option value="medical">Medical & Healthcare</option>
                  <option value="consulting">Consulting & Professional Services</option>
                  <option value="real-estate">Real Estate</option>
                  <option value="retail">Retail & E-commerce</option>
                  <option value="construction">Construction & Contracting</option>
                  <option value="automotive">Automotive Services</option>
                  <option value="beauty">Beauty & Wellness</option>
                  <option value="education">Education & Training</option>
                  <option value="technology">Technology & Software</option>
                  <option value="other">Other</option>
                </select>
                {validationErrors.industry && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400">{validationErrors.industry}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-brand-text dark:text-white mb-2">
                  Team Size *
                </label>
                <select
                  value={formData.teamSize}
                  onChange={(e) => setFormData({ ...formData, teamSize: e.target.value })}
                  className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-brand-accent focus:border-brand-accent transition-colors ${
                    validationErrors.teamSize 
                      ? 'border-red-500 bg-red-50 dark:bg-red-900/20' 
                      : 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700'
                  }`}
                >
                  <option value="">Select team size</option>
                  <option value="1-5">1-5 people</option>
                  <option value="6-20">6-20 people</option>
                  <option value="21-50">21-50 people</option>
                  <option value="51-200">51-200 people</option>
                  <option value="200+">200+ people</option>
                </select>
                {validationErrors.teamSize && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400">{validationErrors.teamSize}</p>
                )}
              </div>

              {/* Privacy and Terms Consent */}
              <div className="space-y-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                <div className="flex items-start space-x-3">
                  <input
                    type="checkbox"
                    id="privacyConsent"
                    checked={formData.privacyConsent}
                    onChange={(e) => setFormData({ ...formData, privacyConsent: e.target.checked })}
                    className="mt-1 h-4 w-4 text-brand-accent border-gray-300 rounded focus:ring-brand-accent"
                  />
                  <label htmlFor="privacyConsent" className="text-sm text-brand-text dark:text-white">
                    I agree to the{' '}
                    <a href="/privacy" target="_blank" rel="noopener noreferrer" className="text-brand-accent hover:text-brand-secondary underline">
                      Privacy Policy
                    </a>
                    {' '}and consent to data processing *
                  </label>
                </div>
                {validationErrors.privacyConsent && (
                  <p className="text-sm text-red-600 dark:text-red-400">{validationErrors.privacyConsent}</p>
                )}

                <div className="flex items-start space-x-3">
                  <input
                    type="checkbox"
                    id="termsAccepted"
                    checked={formData.termsAccepted}
                    onChange={(e) => setFormData({ ...formData, termsAccepted: e.target.checked })}
                    className="mt-1 h-4 w-4 text-brand-accent border-gray-300 rounded focus:ring-brand-accent"
                  />
                  <label htmlFor="termsAccepted" className="text-sm text-brand-text dark:text-white">
                    I agree to the{' '}
                    <a href="/terms" target="_blank" rel="noopener noreferrer" className="text-brand-accent hover:text-brand-secondary underline">
                      Terms of Service
                    </a>
                    {' '}*
                  </label>
                </div>
                {validationErrors.termsAccepted && (
                  <p className="text-sm text-red-600 dark:text-red-400">{validationErrors.termsAccepted}</p>
                )}

                <div className="flex items-start space-x-3">
                  <input
                    type="checkbox"
                    id="marketingConsent"
                    checked={formData.marketingConsent}
                    onChange={(e) => setFormData({ ...formData, marketingConsent: e.target.checked })}
                    className="mt-1 h-4 w-4 text-brand-accent border-gray-300 rounded focus:ring-brand-accent"
                  />
                  <label htmlFor="marketingConsent" className="text-sm text-brand-text dark:text-white">
                    I would like to receive marketing communications and product updates (optional)
                  </label>
                </div>
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
              <div className="mx-auto w-16 h-16 bg-brand-secondary/10 rounded-full flex items-center justify-center mb-4">
                <Database className="h-8 w-8 text-brand-secondary" />
              </div>
              <h2 className="text-2xl font-bold text-brand-text dark:text-white mb-2">Setting up your workspace</h2>
              <p className="text-gray-600 dark:text-gray-400">We're configuring your AI assistant and syncing your data</p>
            </div>

            {onboardingJob ? (
              <SyncProgress 
                userId={user?.id || 0}
                onComplete={() => {
                  updateOnboardingStep(4)
                  navigate('/onboarding/4')
                }}
              />
            ) : (
              <div className="text-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-brand-accent mx-auto mb-4" />
                <p className="text-gray-600 dark:text-gray-400">Starting workspace setup...</p>
              </div>
            )}
          </div>
        )

      case 4:
        return (
          <div className="space-y-6">
            <div className="text-center">
              <div className="mx-auto w-16 h-16 bg-brand-primary/10 rounded-full flex items-center justify-center mb-4">
                <Settings className="h-8 w-8 text-brand-primary" />
              </div>
              <h2 className="text-2xl font-bold text-brand-text dark:text-white mb-2">Choose your services</h2>
              <p className="text-gray-600 dark:text-gray-400">Select the business tools you want to integrate</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                { id: 'hubspot', name: 'HubSpot CRM', description: 'Customer relationship management', icon: Users },
                { id: 'shopify', name: 'Shopify', description: 'E-commerce platform', icon: Zap },
                { id: 'calendly', name: 'Calendly', description: 'Scheduling and appointments', icon: Mail },
                { id: 'slack', name: 'Slack', description: 'Team communication', icon: Brain },
                { id: 'zapier', name: 'Zapier', description: 'Workflow automation', icon: Settings },
                { id: 'salesforce', name: 'Salesforce', description: 'Sales and customer management', icon: Database }
              ].map((service) => {
                const Icon = service.icon
                const isSelected = formData.services.includes(service.id)
                
                return (
                  <div
                    key={service.id}
                    onClick={() => {
                      const newServices = isSelected
                        ? formData.services.filter(s => s !== service.id)
                        : [...formData.services, service.id]
                      setFormData({ ...formData, services: newServices })
                    }}
                    className={`p-4 border rounded-lg cursor-pointer transition-all duration-200 ${
                      isSelected
                        ? 'border-brand-accent bg-brand-accent/10 ring-2 ring-brand-accent'
                        : 'border-gray-300 dark:border-gray-600 hover:border-brand-accent hover:bg-brand-accent/5'
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <Icon className={`h-6 w-6 ${isSelected ? 'text-brand-accent' : 'text-gray-500'}`} />
                      <div>
                        <h3 className={`font-medium ${isSelected ? 'text-brand-accent' : 'text-brand-text dark:text-white'}`}>
                          {service.name}
                        </h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400">{service.description}</p>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>

            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
              <div className="flex items-start space-x-3">
                <Info className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5" />
                <div>
                  <h4 className="text-sm font-medium text-blue-800 dark:text-blue-200">Service Integration</h4>
                  <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                    You can always add or remove services later from your dashboard settings.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )

      case 5:
        return (
          <div className="space-y-6 text-center">
            <div className="mx-auto w-16 h-16 bg-green-100 dark:bg-green-900/20 rounded-full flex items-center justify-center mb-4">
              <CheckCircle className="h-8 w-8 text-green-600 dark:text-green-400" />
            </div>
            <h2 className="text-2xl font-bold text-brand-text dark:text-white mb-2">Welcome to Fikiri!</h2>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Your workspace is ready. You can now start using AI-powered automation for your business.
            </p>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center">
                <div className="w-12 h-12 bg-brand-accent/20 rounded-xl flex items-center justify-center mx-auto mb-2">
                  <CheckCircle className="h-6 w-6 text-brand-accent" />
                </div>
                <h3 className="font-medium text-brand-text dark:text-white">Gmail Connected</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">Email automation ready</p>
              </div>
              <div className="text-center">
                <div className="w-12 h-12 bg-brand-secondary/20 rounded-xl flex items-center justify-center mx-auto mb-2">
                  <Settings className="h-6 w-6 text-brand-secondary" />
                </div>
                <h3 className="font-medium text-brand-text dark:text-white">Services Configured</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">{formData.services.length} integrations</p>
              </div>
              <div className="text-center">
                <div className="w-12 h-12 bg-brand-primary/20 rounded-xl flex items-center justify-center mx-auto mb-2">
                  <Zap className="h-6 w-6 text-brand-primary" />
                </div>
                <h3 className="font-medium text-brand-text dark:text-white">AI Assistant Ready</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">Start automating</p>
              </div>
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
      default: return ''
    }
  }

  const isStepComplete = () => {
    switch (currentStep) {
      case 1: return validateStep(1)
      case 2: return gmailConnected
      case 3: return onboardingJob?.status === 'completed'
      case 4: return formData.services.length > 0
      case 5: return true
      default: return false
    }
  }

  const canProceed = () => {
    return isStepComplete() && !isLoading
  }

  return (
    <div className="min-h-screen bg-brand-background dark:bg-gray-900 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-brand-text dark:text-white">
              Step {currentStep} of 5
            </span>
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {Math.round((currentStep / 5) * 100)}% Complete
            </span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div 
              className="bg-gradient-to-r from-brand-primary to-brand-secondary h-2 rounded-full transition-all duration-300"
              style={{ width: `${(currentStep / 5) * 100}%` }}
            />
          </div>
        </div>

        {/* Main Content */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 p-8">
          {/* Step Title */}
          <div className="mb-6">
            <h1 className="text-xl font-semibold text-brand-text dark:text-white">
              {getStepTitle()}
            </h1>
          </div>

          {/* Error Display */}
          {error && (
            <div className="mb-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
              <div className="flex items-center">
                <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 mr-2" />
                <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
              </div>
            </div>
          )}

          {/* Step Content */}
          {renderStepContent()}

          {/* Navigation */}
          <div className="flex justify-between items-center mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={handlePrevious}
              disabled={currentStep === 1 || isLoading}
              className="flex items-center px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Previous
            </button>

            <div className="flex items-center space-x-2">
              {[1, 2, 3, 4, 5].map((step) => (
                <div
                  key={step}
                  className={`w-2 h-2 rounded-full ${
                    step <= currentStep
                      ? 'bg-brand-accent'
                      : 'bg-gray-300 dark:bg-gray-600'
                  }`}
                />
              ))}
            </div>

            <button
              onClick={handleNext}
              disabled={!canProceed()}
              className="flex items-center px-4 py-2 text-sm font-medium text-white bg-gradient-to-r from-brand-primary to-brand-secondary rounded-lg hover:from-brand-secondary hover:to-brand-primary disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : currentStep === 5 ? (
                <>
                  Get Started
                  <ArrowRight className="h-4 w-4 ml-2" />
                </>
              ) : (
                <>
                  Next
                  <ArrowRight className="h-4 w-4 ml-2" />
                </>
              )}
            </button>
          </div>
        </div>

        {/* Security Notice */}
        <div className="mt-6 text-center">
          <div className="flex items-center justify-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
            <Shield className="h-4 w-4" />
            <span>Your data is encrypted and secure</span>
          </div>
        </div>
      </div>
    </div>
  )
}