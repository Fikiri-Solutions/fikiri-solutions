import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  CheckCircle, 
  ArrowRight, 
  ArrowLeft, 
  Mail, 
  Users, 
  Brain,
  Zap,
  Star,
  Info
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from './Toast'

interface OnboardingWizardProps {
  isOpen: boolean
  onClose: () => void
  onComplete: () => void
}

interface Step {
  id: number
  title: string
  description: string
  icon: React.ComponentType<any>
  content: React.ReactNode
}

export const OnboardingWizard: React.FC<OnboardingWizardProps> = ({ 
  isOpen, 
  onComplete 
}) => {
  const { user, updateUser } = useAuth()
  const { addToast } = useToast()
  const [currentStep, setCurrentStep] = useState(1)
  const [completedSteps, setCompletedSteps] = useState<number[]>([])

  const steps: Step[] = [
    {
      id: 1,
      title: "Welcome to Fikiri",
      description: "Let's get you set up for success",
      icon: Star,
      content: (
        <div className="text-center space-y-6">
          <div className="w-20 h-20 bg-orange-100 dark:bg-orange-900/20 rounded-full flex items-center justify-center mx-auto">
            <Star className="w-10 h-10 text-orange-600 dark:text-orange-400" />
          </div>
          <div>
            <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              Welcome, {user?.name || 'there'}!
            </h3>
            <p className="text-gray-600 dark:text-gray-300">
              We're excited to help you automate your business processes. 
              This quick setup will get you started in just a few minutes.
            </p>
          </div>
        </div>
      )
    },
    {
      id: 2,
      title: "Connect Your Email",
      description: "Link your Gmail account for AI-powered email management",
      icon: Mail,
      content: (
        <div className="space-y-6">
          <div className="text-center">
            <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <Mail className="w-8 h-8 text-blue-600 dark:text-blue-400" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
              Email Integration
            </h3>
            <p className="text-gray-600 dark:text-gray-300">
              Connect your Gmail account to enable AI-powered email responses, 
              smart categorization, and automated follow-ups.
            </p>
          </div>
          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
            <div className="flex items-start space-x-3">
              <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5" />
              <div>
                <h4 className="font-medium text-blue-900 dark:text-blue-100">What you'll get:</h4>
                <ul className="text-sm text-blue-700 dark:text-blue-200 mt-1 space-y-1">
                  <li>• AI-generated email responses</li>
                  <li>• Smart email categorization</li>
                  <li>• Automated follow-up reminders</li>
                  <li>• Email analytics and insights</li>
                </ul>
              </div>
            </div>
          </div>
          <button className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg hover:bg-blue-700 transition-colors">
            Connect Gmail Account
          </button>
        </div>
      )
    },
    {
      id: 3,
      title: "Set Up Your CRM",
      description: "Configure your customer relationship management",
      icon: Users,
      content: (
        <div className="space-y-6">
          <div className="text-center">
            <div className="w-16 h-16 bg-green-100 dark:bg-green-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <Users className="w-8 h-8 text-green-600 dark:text-green-400" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
              CRM Configuration
            </h3>
            <p className="text-gray-600 dark:text-gray-300">
              Set up your customer relationship management system to track leads, 
              manage contacts, and automate your sales pipeline.
            </p>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
              <h4 className="font-medium text-green-900 dark:text-green-100 mb-2">Lead Management</h4>
              <p className="text-sm text-green-700 dark:text-green-200">
                Automatically capture and score leads from your website and forms.
              </p>
            </div>
            <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
              <h4 className="font-medium text-green-900 dark:text-green-100 mb-2">Pipeline Tracking</h4>
              <p className="text-sm text-green-700 dark:text-green-200">
                Visual pipeline management with automated stage progression.
              </p>
            </div>
          </div>
          <button className="w-full bg-green-600 text-white py-3 px-6 rounded-lg hover:bg-green-700 transition-colors">
            Configure CRM
          </button>
        </div>
      )
    },
    {
      id: 4,
      title: "AI Assistant Setup",
      description: "Customize your AI assistant for your business",
      icon: Brain,
      content: (
        <div className="space-y-6">
          <div className="text-center">
            <div className="w-16 h-16 bg-purple-100 dark:bg-purple-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <Brain className="w-8 h-8 text-purple-600 dark:text-purple-400" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
              AI Assistant
            </h3>
            <p className="text-gray-600 dark:text-gray-300">
              Configure your AI assistant to understand your business context 
              and provide intelligent responses to customer inquiries.
            </p>
          </div>
          <div className="space-y-4">
            <div className="flex items-center space-x-3">
              <CheckCircle className="w-5 h-5 text-green-500" />
              <span className="text-gray-700 dark:text-gray-300">Smart FAQ responses</span>
            </div>
            <div className="flex items-center space-x-3">
              <CheckCircle className="w-5 h-5 text-green-500" />
              <span className="text-gray-700 dark:text-gray-300">Context-aware conversations</span>
            </div>
            <div className="flex items-center space-x-3">
              <CheckCircle className="w-5 h-5 text-green-500" />
              <span className="text-gray-700 dark:text-gray-300">Multi-channel support</span>
            </div>
          </div>
          <button className="w-full bg-purple-600 text-white py-3 px-6 rounded-lg hover:bg-purple-700 transition-colors">
            Set Up AI Assistant
          </button>
        </div>
      )
    },
    {
      id: 5,
      title: "You're All Set!",
      description: "Your Fikiri workspace is ready to go",
      icon: CheckCircle,
      content: (
        <div className="text-center space-y-6">
          <div className="w-20 h-20 bg-green-100 dark:bg-green-900/20 rounded-full flex items-center justify-center mx-auto">
            <CheckCircle className="w-10 h-10 text-green-600 dark:text-green-400" />
          </div>
          <div>
            <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              Congratulations!
            </h3>
            <p className="text-gray-600 dark:text-gray-300">
              Your Fikiri workspace is now fully configured and ready to help 
              you automate your business processes. You can start using all 
              the features right away.
            </p>
          </div>
          <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
            <h4 className="font-medium text-green-900 dark:text-green-100 mb-2">What's next?</h4>
            <ul className="text-sm text-green-700 dark:text-green-200 space-y-1">
              <li>• Explore your dashboard</li>
              <li>• Set up your first automation</li>
              <li>• Invite team members</li>
              <li>• Customize your settings</li>
            </ul>
          </div>
        </div>
      )
    }
  ]

  const handleNext = () => {
    if (currentStep < steps.length) {
      setCompletedSteps(prev => [...prev, currentStep])
      setCurrentStep(prev => prev + 1)
    } else {
      handleComplete()
    }
  }

  const handlePrevious = () => {
    if (currentStep > 1) {
      setCurrentStep(prev => prev - 1)
    }
  }

  const handleComplete = () => {
    if (user) {
      const updatedUser = {
        ...user,
        onboarding_completed: true
      }
      updateUser(updatedUser)
    }
    addToast({ type: 'success', title: 'Welcome to Fikiri! Your workspace is ready.' })
    onComplete()
  }

  const handleSkip = () => {
    if (typeof window !== 'undefined' && window.confirm('Are you sure you want to skip the setup? You can always complete it later from your settings.')) {
      handleComplete()
    }
  }

  if (!isOpen) return null

  const currentStepData = steps.find(step => step.id === currentStep)

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 overflow-y-auto">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-2xl my-8 flex flex-col max-h-[90vh]"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-orange-100 dark:bg-orange-900/20 rounded-full flex items-center justify-center">
              <Zap className="w-4 h-4 text-orange-600 dark:text-orange-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Quick Setup</h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Step {currentStep} of {steps.length}
              </p>
            </div>
          </div>
          <button
            onClick={handleSkip}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-sm"
          >
            Skip for now
          </button>
        </div>

        {/* Progress Bar */}
        <div className="px-6 py-4 flex-shrink-0">
          <div className="flex items-center space-x-2">
            {steps.map((step) => (
              <div
                key={step.id}
                className={`flex-1 h-2 rounded-full ${
                  step.id <= currentStep
                    ? 'bg-orange-500'
                    : 'bg-gray-200 dark:bg-gray-700'
                }`}
              />
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto flex-1 min-h-0">
          <AnimatePresence mode="wait">
            {currentStepData && (
              <motion.div
                key={currentStep}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-6"
              >
                <div className="text-center">
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                    {currentStepData.title}
                  </h3>
                  <p className="text-gray-600 dark:text-gray-300">
                    {currentStepData.description}
                  </p>
                </div>
                {currentStepData.content}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200 dark:border-gray-700 flex-shrink-0">
          <button
            onClick={handlePrevious}
            disabled={currentStep === 1}
            className="flex items-center space-x-2 px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Previous</span>
          </button>

          <div className="flex items-center space-x-2">
            {steps.map((step) => (
              <div
                key={step.id}
                className={`w-2 h-2 rounded-full ${
                  completedSteps.includes(step.id)
                    ? 'bg-green-500'
                    : step.id === currentStep
                    ? 'bg-orange-500'
                    : 'bg-gray-300 dark:bg-gray-600'
                }`}
              />
            ))}
          </div>

          <button
            onClick={handleNext}
            className="flex items-center space-x-2 bg-orange-500 text-white px-6 py-2 rounded-lg hover:bg-orange-600 transition-colors"
          >
            <span>{currentStep === steps.length ? 'Get Started' : 'Next'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </motion.div>
    </div>
  )
}