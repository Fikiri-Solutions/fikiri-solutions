import React, { useState } from 'react'
import { Sparkles, Zap, CheckCircle, X, ArrowRight, Lightbulb } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from './Toast'
import { apiClient } from '../services/apiClient'

interface RecommendedAutomation {
  presetId: string
  name: string
  description: string
  reason: string
  priority: 'high' | 'medium' | 'low'
}

// Industry-based automation recommendations
const getRecommendations = (industry: string = ''): RecommendedAutomation[] => {
  const industryLower = industry.toLowerCase()
  
  // Base recommendations for everyone
  const base: RecommendedAutomation[] = [
    {
      presetId: 'gmail_crm',
      name: 'Gmail → CRM',
      description: 'Automatically convert emails into CRM leads',
      reason: 'Essential for capturing leads from your inbox',
      priority: 'high'
    }
  ]
  
  // Industry-specific recommendations
  if (industryLower.includes('landscap') || industryLower.includes('garden') || industryLower.includes('lawn')) {
    return [
      ...base,
      {
        presetId: 'lead_scoring',
        name: 'Lead Scoring',
        description: 'Prioritize quote requests and property inquiries',
        reason: 'Helps you focus on high-value landscaping projects',
        priority: 'high'
      },
      {
        presetId: 'calendar_followups',
        name: 'Calendar Follow-ups',
        description: 'Auto-remind for site visits and consultations',
        reason: 'Never miss a follow-up after property assessments',
        priority: 'medium'
      }
    ]
  }
  
  if (industryLower.includes('restaurant') || industryLower.includes('food') || industryLower.includes('cater')) {
    return [
      ...base,
      {
        presetId: 'lead_scoring',
        name: 'Lead Scoring',
        description: 'Identify high-value catering and event inquiries',
        reason: 'Prioritize large events and repeat customers',
        priority: 'high'
      },
      {
        presetId: 'calendar_followups',
        name: 'Calendar Follow-ups',
        description: 'Follow up on event bookings and reservations',
        reason: 'Improve booking conversion rates',
        priority: 'medium'
      }
    ]
  }
  
  if (industryLower.includes('medical') || industryLower.includes('health') || industryLower.includes('clinic')) {
    return [
      ...base,
      {
        presetId: 'lead_scoring',
        name: 'Lead Scoring',
        description: 'Prioritize patient inquiries and appointments',
        reason: 'Focus on urgent cases and new patient intake',
        priority: 'high'
      },
      {
        presetId: 'calendar_followups',
        name: 'Calendar Follow-ups',
        description: 'Send appointment reminders and follow-ups',
        reason: 'Reduce no-shows and improve patient care',
        priority: 'high'
      }
    ]
  }
  
  if (industryLower.includes('real estate') || industryLower.includes('property')) {
    return [
      ...base,
      {
        presetId: 'lead_scoring',
        name: 'Lead Scoring',
        description: 'Score buyer and seller inquiries',
        reason: 'Identify serious buyers and motivated sellers',
        priority: 'high'
      },
      {
        presetId: 'calendar_followups',
        name: 'Calendar Follow-ups',
        description: 'Follow up on showings and property inquiries',
        reason: 'Convert more leads into showings and offers',
        priority: 'high'
      }
    ]
  }
  
  // Default for other industries
  return [
    ...base,
    {
      presetId: 'lead_scoring',
      name: 'Lead Scoring',
      description: 'Automatically score and prioritize leads',
      reason: 'Helps you focus on the most promising opportunities',
      priority: 'medium'
    },
    {
      presetId: 'calendar_followups',
      name: 'Calendar Follow-ups',
      description: 'Never miss a follow-up with automated reminders',
      reason: 'Improve conversion rates with timely follow-ups',
      priority: 'medium'
    }
  ]
}

interface AutomationWizardProps {
  onComplete?: () => void
  onSkip?: () => void
}

export const AutomationWizard: React.FC<AutomationWizardProps> = ({ onComplete, onSkip }) => {
  const { user } = useAuth()
  const { addToast } = useToast()
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [isSettingUp, setIsSettingUp] = useState(false)
  
  const recommendations = getRecommendations(user?.industry || '')
  const highPriority = recommendations.filter(r => r.priority === 'high')
  
  const toggleSelection = (presetId: string) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(presetId)) {
        next.delete(presetId)
      } else {
        next.add(presetId)
      }
      return next
    })
  }
  
  const handleSetup = async () => {
    if (selected.size === 0) {
      addToast({
        type: 'warning',
        title: 'Select Automations',
        message: 'Please select at least one automation to set up'
      })
      return
    }
    
    setIsSettingUp(true)
    
    try {
      // Get existing rules
      const existingRules = await apiClient.getAutomationRules()
      
      // Create rules for selected presets
      const promises = Array.from(selected).map(async (presetId) => {
        // Check if rule already exists
        const existing = existingRules.find((r: any) => 
          r.action_parameters?.slug === presetId || r.name === presetId
        )
        
        if (existing) {
          // Activate existing rule
          await apiClient.updateAutomationRule(existing.id, { status: 'active' })
          return
        }
        
        // Find preset config
        const preset = recommendations.find(r => r.presetId === presetId)
        if (!preset) return
        
        // Create new rule based on preset
        const ruleData: any = {
          name: preset.name,
          description: preset.description,
          trigger_type: presetId === 'gmail_crm' ? 'email_received' : 
                       presetId === 'lead_scoring' ? 'lead_created' :
                       presetId === 'calendar_followups' ? 'lead_stage_changed' : 'email_received',
          action_type: presetId === 'gmail_crm' ? 'update_crm_field' :
                      presetId === 'lead_scoring' ? 'update_crm_field' :
                      presetId === 'calendar_followups' ? 'schedule_follow_up' : 'update_crm_field',
          status: 'active',
          trigger_conditions: {},
          action_parameters: {
            slug: presetId,
            ...(presetId === 'gmail_crm' ? { target_stage: 'new' } : {}),
            ...(presetId === 'lead_scoring' ? { min_score: 6 } : {}),
            ...(presetId === 'calendar_followups' ? { delay_hours: 24 } : {})
          }
        }
        
        await apiClient.createAutomationRule(ruleData)
      })
      
      await Promise.all(promises)
      
      addToast({
        type: 'success',
        title: 'Automations Set Up',
        message: `Successfully configured ${selected.size} automation${selected.size > 1 ? 's' : ''}`
      })
      
      if (onComplete) {
        onComplete()
      }
    } catch (error: any) {
      addToast({
        type: 'error',
        title: 'Setup Failed',
        message: error?.message || 'Failed to set up automations. Please try again.'
      })
    } finally {
      setIsSettingUp(false)
    }
  }
  
  if (recommendations.length === 0) {
    return null
  }
  
  return (
    <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-800 dark:to-gray-900 rounded-xl p-6 border border-blue-200 dark:border-gray-700">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
            <Sparkles className="h-5 w-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Recommended Automations
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Based on your {user?.industry ? `${user.industry} ` : ''}business
            </p>
          </div>
        </div>
        {onSkip && (
          <button
            onClick={onSkip}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>
      
      <div className="space-y-3 mb-6">
        {recommendations.map((rec) => (
          <div
            key={rec.presetId}
            onClick={() => toggleSelection(rec.presetId)}
            className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
              selected.has(rec.presetId)
                ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-blue-300'
            }`}
          >
            <div className="flex items-start gap-3">
              <div className={`mt-1 p-1 rounded ${
                selected.has(rec.presetId) ? 'bg-blue-500' : 'bg-gray-200 dark:bg-gray-700'
              }`}>
                {selected.has(rec.presetId) ? (
                  <CheckCircle className="h-4 w-4 text-white" />
                ) : (
                  <div className="h-4 w-4" />
                )}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h4 className="font-medium text-gray-900 dark:text-white">{rec.name}</h4>
                  {rec.priority === 'high' && (
                    <span className="text-xs px-2 py-0.5 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded">
                      Recommended
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">{rec.description}</p>
                <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                  <Lightbulb className="h-3 w-3" />
                  <span>{rec.reason}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
      
      <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          {selected.size} of {recommendations.length} selected
        </p>
        <button
          onClick={handleSetup}
          disabled={selected.size === 0 || isSettingUp}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {isSettingUp ? (
            <>
              <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Setting Up...
            </>
          ) : (
            <>
              <Zap className="h-4 w-4" />
              Set Up Selected
            </>
          )}
        </button>
      </div>
    </div>
  )
}

