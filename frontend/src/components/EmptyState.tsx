import React from 'react'
import { Users, Plus, Mail, Settings, ArrowRight } from 'lucide-react'

interface EmptyStateProps {
  type: 'crm' | 'dashboard' | 'services' | 'ai'
  onAction?: () => void
}

export const EmptyState: React.FC<EmptyStateProps> = ({ type, onAction }) => {
  const getEmptyStateConfig = () => {
    switch (type) {
      case 'crm':
        return {
          icon: Users,
          title: 'No leads yet',
          description: 'Start building your pipeline by adding your first lead.',
          actionText: 'Add First Lead',
          actionIcon: Plus,
          illustration: '👥',
        }
      case 'dashboard':
        return {
          icon: Mail,
          title: 'Welcome to your dashboard',
          description: 'Set up your services to start seeing data and insights.',
          actionText: 'Setup Services',
          actionIcon: Settings,
          illustration: '📊',
        }
      case 'services':
        return {
          icon: Settings,
          title: 'Configure your services',
          description: 'Connect your email, CRM, and AI services to get started.',
          actionText: 'Connect Services',
          actionIcon: ArrowRight,
          illustration: '⚙️',
        }
      case 'ai':
        return {
          icon: Mail,
          title: 'AI Assistant ready',
          description: 'Your AI assistant is ready to help with customer inquiries.',
          actionText: 'Start Chatting',
          actionIcon: ArrowRight,
          illustration: '🤖',
        }
    }
  }

  const config = getEmptyStateConfig()
  const Icon = config.icon

  return (
    <div className="text-center py-12 px-6">
      <div className="text-6xl mb-4">{config.illustration}</div>
      
      <div className="max-w-md mx-auto">
        <div className="flex items-center justify-center mb-4">
          <div className="p-3 bg-blue-100 dark:bg-blue-900 rounded-full">
            <Icon className="h-6 w-6 text-blue-600 dark:text-blue-400" />
          </div>
        </div>
        
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
          {config.title}
        </h3>
        
        <p className="text-gray-600 dark:text-gray-400 mb-6">
          {config.description}
        </p>
        
        {onAction && (
          <button
            onClick={onAction}
            className="fikiri-button inline-flex items-center space-x-2"
          >
            <config.actionIcon className="h-4 w-4" />
            <span>{config.actionText}</span>
          </button>
        )}
      </div>
    </div>
  )
}
