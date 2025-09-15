import React, { useState } from 'react'
import { CheckCircle, ArrowRight, ArrowLeft, Mail, Users, Brain, Settings } from 'lucide-react'

export const Onboarding: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(1)
  const [formData, setFormData] = useState({
    businessName: '',
    businessEmail: '',
    industry: '',
    teamSize: '',
    services: [] as string[]
  })

  const steps = [
    {
      id: 1,
      title: 'Welcome to Fikiri Solutions',
      description: 'Let\'s get your business set up for success',
      icon: CheckCircle
    },
    {
      id: 2,
      title: 'Business Information',
      description: 'Tell us about your business',
      icon: Users
    },
    {
      id: 3,
      title: 'Email Integration',
      description: 'Connect your Gmail account',
      icon: Mail
    },
    {
      id: 4,
      title: 'Choose Services',
      description: 'Select the features you need',
      icon: Settings
    },
    {
      id: 5,
      title: 'You\'re All Set!',
      description: 'Start automating your business',
      icon: Brain
    }
  ]

  const serviceOptions = [
    { id: 'ai-assistant', name: 'AI Email Assistant', description: 'Automated responses and lead management' },
    { id: 'crm', name: 'CRM Service', description: 'Track leads and customer relationships' },
    { id: 'email-parser', name: 'Email Parser', description: 'Intelligent email content analysis' },
    { id: 'ml-scoring', name: 'ML Lead Scoring', description: 'AI-powered lead prioritization' }
  ]

  const handleNext = () => {
    if (currentStep < 5) {
      setCurrentStep(currentStep + 1)
    } else {
      // Complete onboarding
      window.location.href = '/'
    }
  }

  const handlePrevious = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleServiceToggle = (serviceId: string) => {
    setFormData(prev => ({
      ...prev,
      services: prev.services.includes(serviceId)
        ? prev.services.filter(id => id !== serviceId)
        : [...prev.services, serviceId]
    }))
  }

  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="text-center space-y-6">
            <div className="mx-auto w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center">
              <CheckCircle className="h-8 w-8 text-blue-600" />
            </div>
            <div>
              <h3 className="text-2xl font-bold text-gray-900">Welcome!</h3>
              <p className="mt-2 text-gray-600">
                We're excited to help you automate your business communications. 
                This setup will only take a few minutes.
              </p>
            </div>
          </div>
        )

      case 2:
        return (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700">Business Name</label>
              <input
                type="text"
                className="input-field mt-1"
                placeholder="Enter your business name"
                value={formData.businessName}
                onChange={(e) => setFormData(prev => ({ ...prev, businessName: e.target.value }))}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Business Email</label>
              <input
                type="email"
                className="input-field mt-1"
                placeholder="Enter your business email"
                value={formData.businessEmail}
                onChange={(e) => setFormData(prev => ({ ...prev, businessEmail: e.target.value }))}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Industry</label>
              <select
                className="input-field mt-1"
                value={formData.industry}
                onChange={(e) => setFormData(prev => ({ ...prev, industry: e.target.value }))}
              >
                <option value="">Select your industry</option>
                <option value="technology">Technology</option>
                <option value="healthcare">Healthcare</option>
                <option value="finance">Finance</option>
                <option value="retail">Retail</option>
                <option value="consulting">Consulting</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Team Size</label>
              <select
                className="input-field mt-1"
                value={formData.teamSize}
                onChange={(e) => setFormData(prev => ({ ...prev, teamSize: e.target.value }))}
              >
                <option value="">Select team size</option>
                <option value="1">Just me</option>
                <option value="2-5">2-5 people</option>
                <option value="6-20">6-20 people</option>
                <option value="21-50">21-50 people</option>
                <option value="50+">50+ people</option>
              </select>
            </div>
          </div>
        )

      case 3:
        return (
          <div className="text-center space-y-6">
            <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
              <Mail className="h-8 w-8 text-green-600" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-gray-900">Connect Your Gmail</h3>
              <p className="mt-2 text-gray-600">
                We'll help you connect your Gmail account to enable automated email processing.
              </p>
            </div>
            <button className="btn-primary">
              Connect Gmail Account
            </button>
            <p className="text-sm text-gray-500">
              Don't worry, you can skip this step and set it up later.
            </p>
          </div>
        )

      case 4:
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-gray-900">Choose Your Services</h3>
              <p className="text-sm text-gray-600">Select the features you'd like to enable</p>
            </div>
            <div className="space-y-4">
              {serviceOptions.map((service) => (
                <div
                  key={service.id}
                  className={`card cursor-pointer transition-all duration-200 ${
                    formData.services.includes(service.id)
                      ? 'ring-2 ring-blue-500 bg-blue-50'
                      : 'hover:shadow-md'
                  }`}
                  onClick={() => handleServiceToggle(service.id)}
                >
                  <div className="flex items-start">
                    <input
                      type="checkbox"
                      checked={formData.services.includes(service.id)}
                      onChange={() => handleServiceToggle(service.id)}
                      className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <div className="ml-3">
                      <h4 className="text-sm font-medium text-gray-900">{service.name}</h4>
                      <p className="text-xs text-gray-600">{service.description}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )

      case 5:
        return (
          <div className="text-center space-y-6">
            <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
              <Brain className="h-8 w-8 text-green-600" />
            </div>
            <div>
              <h3 className="text-2xl font-bold text-gray-900">You're All Set!</h3>
              <p className="mt-2 text-gray-600">
                Your Fikiri Solutions account is ready. You can start automating your business communications right away.
              </p>
            </div>
            <div className="bg-green-50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-green-800">What's Next?</h4>
              <ul className="mt-2 text-sm text-green-700 space-y-1">
                <li>• Your AI assistant is ready to respond to emails</li>
                <li>• CRM is set up to track your leads</li>
                <li>• You can customize settings anytime</li>
              </ul>
            </div>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-2xl mx-auto">
        {/* Progress Steps */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            {steps.map((step, index) => (
              <div key={step.id} className="flex items-center">
                <div className={`flex items-center justify-center w-8 h-8 rounded-full ${
                  currentStep >= step.id ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600'
                }`}>
                  {currentStep > step.id ? (
                    <CheckCircle className="h-5 w-5" />
                  ) : (
                    <span className="text-sm font-medium">{step.id}</span>
                  )}
                </div>
                {index < steps.length - 1 && (
                  <div className={`w-16 h-1 mx-2 ${
                    currentStep > step.id ? 'bg-blue-600' : 'bg-gray-200'
                  }`} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Step Content */}
        <div className="card">
          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold text-gray-900">{steps[currentStep - 1].title}</h2>
            <p className="mt-2 text-gray-600">{steps[currentStep - 1].description}</p>
          </div>

          {renderStepContent()}

          {/* Navigation */}
          <div className="flex justify-between mt-8">
            <button
              onClick={handlePrevious}
              disabled={currentStep === 1}
              className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Previous
            </button>
            <button
              onClick={handleNext}
              className="btn-primary"
            >
              {currentStep === 5 ? 'Get Started' : 'Next'}
              {currentStep < 5 && <ArrowRight className="h-4 w-4 ml-2" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
