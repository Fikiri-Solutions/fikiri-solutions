import React from 'react'
import { Users, Plus, Mail, Settings, ArrowRight, LucideIcon } from 'lucide-react'

interface EmptyStateProps {
  type?: 'crm' | 'dashboard' | 'services' | 'ai' | 'chatbot' | 'faq'
  onAction?: () => void
  // Direct props (alternative to type-based)
  icon?: LucideIcon
  title?: string
  description?: string
  actionText?: string
  actionIcon?: LucideIcon
  illustration?: string
}

export const EmptyState: React.FC<EmptyStateProps> = ({ 
  type, 
  onAction,
  icon: directIcon,
  title: directTitle,
  description: directDescription,
  actionText: directActionText,
  actionIcon: directActionIcon,
  illustration: directIllustration
}) => {
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
      case 'chatbot':
      case 'faq':
        return {
          icon: Settings,
          title: 'No FAQs yet',
          description: 'Start building your knowledge base by adding FAQs or documents.',
          actionText: 'Add FAQ',
          actionIcon: Plus,
          illustration: '💬',
        }
      default:
        return {
          icon: Settings,
          title: 'No data available',
          description: 'Get started by configuring your services.',
          actionText: 'Get Started',
          actionIcon: ArrowRight,
          illustration: '📋',
        }
    }
  }

  // Use direct props if provided, otherwise use type-based config
  const config = type ? getEmptyStateConfig() : null
  const finalConfig = {
    icon: directIcon || config?.icon,
    title: directTitle || config?.title,
    description: directDescription || config?.description,
    actionText: directActionText || config?.actionText,
    actionIcon: directActionIcon || config?.actionIcon,
    illustration: directIllustration || config?.illustration,
  }
  
  if (!finalConfig.icon) {
    return null
  }
  
  const Icon = finalConfig.icon
  const ActionIcon = finalConfig.actionIcon

  return (
    <div className="text-center py-12 px-6">
      {finalConfig.illustration && (
        <div className="text-6xl mb-4">{finalConfig.illustration}</div>
      )}
      
      <div className="max-w-md mx-auto">
        {Icon && (
          <div className="flex items-center justify-center mb-4">
            <div className="p-3 bg-blue-100 dark:bg-blue-900 rounded-full">
              <Icon className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
          </div>
        )}
        
        {finalConfig.title && (
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            {finalConfig.title}
          </h3>
        )}
        
        {finalConfig.description && (
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            {finalConfig.description}
          </p>
        )}
        
        {onAction && ActionIcon && finalConfig.actionText && (
          <button
            onClick={onAction}
            className="fikiri-button inline-flex items-center space-x-2"
          >
            <ActionIcon className="h-4 w-4" />
            <span>{finalConfig.actionText}</span>
          </button>
        )}
      </div>
    </div>
  )
}
