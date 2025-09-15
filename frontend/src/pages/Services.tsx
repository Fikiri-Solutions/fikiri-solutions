import React, { useState, useEffect } from 'react'
import { Settings, ToggleLeft, ToggleRight, Save, RefreshCw } from 'lucide-react'

export const Services: React.FC = () => {
  const [services, setServices] = useState([
    {
      id: 'ai-assistant',
      name: 'AI Email Assistant',
      description: 'Automatically respond to customer emails with AI-powered responses',
      enabled: true,
      settings: {
        responseTone: 'professional',
        autoReplyDelay: 5,
        maxResponsesPerDay: 50
      }
    },
    {
      id: 'crm',
      name: 'CRM Service',
      description: 'Track and manage customer leads and relationships',
      enabled: true,
      settings: {
        autoLeadCreation: true,
        leadScoring: true,
        followUpReminders: true
      }
    },
    {
      id: 'email-parser',
      name: 'Email Parser',
      description: 'Intelligently analyze email content and extract key information',
      enabled: true,
      settings: {
        extractContacts: true,
        detectUrgency: true,
        categorizeEmails: true
      }
    },
    {
      id: 'ml-scoring',
      name: 'ML Lead Scoring',
      description: 'Use AI to prioritize leads based on likelihood to convert',
      enabled: false,
      settings: {
        scoringModel: 'standard',
        updateFrequency: 'daily',
        thresholdScore: 0.7
      }
    }
  ])

  const [isLoading, setIsLoading] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)

  useEffect(() => {
    // Load service configurations from API
    loadServiceConfigurations()
  }, [])

  const loadServiceConfigurations = async () => {
    try {
      // TODO: Replace with actual API call
      console.log('Loading service configurations...')
    } catch (error) {
      console.error('Failed to load configurations:', error)
    }
  }

  const toggleService = (serviceId: string) => {
    setServices(prev => prev.map(service => 
      service.id === serviceId 
        ? { ...service, enabled: !service.enabled }
        : service
    ))
    setHasChanges(true)
  }

  const updateServiceSettings = (serviceId: string, settingKey: string, value: any) => {
    setServices(prev => prev.map(service => 
      service.id === serviceId 
        ? { 
            ...service, 
            settings: { 
              ...service.settings, 
              [settingKey]: value 
            } 
          }
        : service
    ))
    setHasChanges(true)
  }

  const saveConfigurations = async () => {
    setIsLoading(true)
    try {
      // TODO: Implement actual API call to save configurations
      console.log('Saving configurations:', services)
      
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      setHasChanges(false)
      // Show success message
    } catch (error) {
      console.error('Failed to save configurations:', error)
      // Show error message
    } finally {
      setIsLoading(false)
    }
  }

  const testService = async (serviceId: string) => {
    try {
      // TODO: Implement actual service testing
      console.log(`Testing service: ${serviceId}`)
      
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      // Show test results
    } catch (error) {
      console.error('Service test failed:', error)
    }
  }

  const renderServiceSettings = (service: any) => {
    switch (service.id) {
      case 'ai-assistant':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Response Tone</label>
              <select
                className="input-field mt-1"
                value={service.settings.responseTone}
                onChange={(e) => updateServiceSettings(service.id, 'responseTone', e.target.value)}
              >
                <option value="professional">Professional</option>
                <option value="friendly">Friendly</option>
                <option value="formal">Formal</option>
                <option value="casual">Casual</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Auto-reply Delay (minutes)</label>
              <input
                type="number"
                className="input-field mt-1"
                value={service.settings.autoReplyDelay}
                onChange={(e) => updateServiceSettings(service.id, 'autoReplyDelay', parseInt(e.target.value))}
                min="1"
                max="60"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Max Responses Per Day</label>
              <input
                type="number"
                className="input-field mt-1"
                value={service.settings.maxResponsesPerDay}
                onChange={(e) => updateServiceSettings(service.id, 'maxResponsesPerDay', parseInt(e.target.value))}
                min="1"
                max="1000"
              />
            </div>
          </div>
        )

      case 'crm':
        return (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">Auto Lead Creation</label>
                <p className="text-xs text-gray-500">Automatically create leads from incoming emails</p>
              </div>
              <button
                onClick={() => updateServiceSettings(service.id, 'autoLeadCreation', !service.settings.autoLeadCreation)}
                className="ml-4"
              >
                {service.settings.autoLeadCreation ? (
                  <ToggleRight className="h-6 w-6 text-blue-600" />
                ) : (
                  <ToggleLeft className="h-6 w-6 text-gray-400" />
                )}
              </button>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">Lead Scoring</label>
                <p className="text-xs text-gray-500">Automatically score leads based on email content</p>
              </div>
              <button
                onClick={() => updateServiceSettings(service.id, 'leadScoring', !service.settings.leadScoring)}
                className="ml-4"
              >
                {service.settings.leadScoring ? (
                  <ToggleRight className="h-6 w-6 text-blue-600" />
                ) : (
                  <ToggleLeft className="h-6 w-6 text-gray-400" />
                )}
              </button>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">Follow-up Reminders</label>
                <p className="text-xs text-gray-500">Send reminders for follow-up actions</p>
              </div>
              <button
                onClick={() => updateServiceSettings(service.id, 'followUpReminders', !service.settings.followUpReminders)}
                className="ml-4"
              >
                {service.settings.followUpReminders ? (
                  <ToggleRight className="h-6 w-6 text-blue-600" />
                ) : (
                  <ToggleLeft className="h-6 w-6 text-gray-400" />
                )}
              </button>
            </div>
          </div>
        )

      case 'email-parser':
        return (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">Extract Contacts</label>
                <p className="text-xs text-gray-500">Automatically extract contact information from emails</p>
              </div>
              <button
                onClick={() => updateServiceSettings(service.id, 'extractContacts', !service.settings.extractContacts)}
                className="ml-4"
              >
                {service.settings.extractContacts ? (
                  <ToggleRight className="h-6 w-6 text-blue-600" />
                ) : (
                  <ToggleLeft className="h-6 w-6 text-gray-400" />
                )}
              </button>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">Detect Urgency</label>
                <p className="text-xs text-gray-500">Identify urgent emails that need immediate attention</p>
              </div>
              <button
                onClick={() => updateServiceSettings(service.id, 'detectUrgency', !service.settings.detectUrgency)}
                className="ml-4"
              >
                {service.settings.detectUrgency ? (
                  <ToggleRight className="h-6 w-6 text-blue-600" />
                ) : (
                  <ToggleLeft className="h-6 w-6 text-gray-400" />
                )}
              </button>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">Categorize Emails</label>
                <p className="text-xs text-gray-500">Automatically categorize emails by type</p>
              </div>
              <button
                onClick={() => updateServiceSettings(service.id, 'categorizeEmails', !service.settings.categorizeEmails)}
                className="ml-4"
              >
                {service.settings.categorizeEmails ? (
                  <ToggleRight className="h-6 w-6 text-blue-600" />
                ) : (
                  <ToggleLeft className="h-6 w-6 text-gray-400" />
                )}
              </button>
            </div>
          </div>
        )

      case 'ml-scoring':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Scoring Model</label>
              <select
                className="input-field mt-1"
                value={service.settings.scoringModel}
                onChange={(e) => updateServiceSettings(service.id, 'scoringModel', e.target.value)}
              >
                <option value="standard">Standard Model</option>
                <option value="advanced">Advanced Model</option>
                <option value="custom">Custom Model</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Update Frequency</label>
              <select
                className="input-field mt-1"
                value={service.settings.updateFrequency}
                onChange={(e) => updateServiceSettings(service.id, 'updateFrequency', e.target.value)}
              >
                <option value="realtime">Real-time</option>
                <option value="hourly">Hourly</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Threshold Score</label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                className="w-full mt-1"
                value={service.settings.thresholdScore}
                onChange={(e) => updateServiceSettings(service.id, 'thresholdScore', parseFloat(e.target.value))}
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>0.0</span>
                <span>{service.settings.thresholdScore}</span>
                <span>1.0</span>
              </div>
            </div>
          </div>
        )

      default:
        return <div className="text-gray-500">No settings available for this service.</div>
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Service Configuration</h1>
          <p className="mt-1 text-sm text-gray-600">
            Configure and manage your Fikiri Solutions services
          </p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={() => loadServiceConfigurations()}
            className="btn-secondary"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </button>
          <button
            onClick={saveConfigurations}
            disabled={!hasChanges || isLoading}
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Save className="h-4 w-4 mr-2" />
            {isLoading ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      {/* Services List */}
      <div className="space-y-6">
        {services.map((service) => (
          <div key={service.id} className="card">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center">
                  <h3 className="text-lg font-medium text-gray-900">{service.name}</h3>
                  <button
                    onClick={() => toggleService(service.id)}
                    className="ml-4"
                  >
                    {service.enabled ? (
                      <ToggleRight className="h-6 w-6 text-blue-600" />
                    ) : (
                      <ToggleLeft className="h-6 w-6 text-gray-400" />
                    )}
                  </button>
                </div>
                <p className="mt-1 text-sm text-gray-600">{service.description}</p>
                <div className="mt-2">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    service.enabled 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-gray-100 text-gray-800'
                  }`}>
                    {service.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
              </div>
              <div className="ml-6">
                <button
                  onClick={() => testService(service.id)}
                  className="btn-secondary text-sm"
                >
                  Test Service
                </button>
              </div>
            </div>

            {/* Service Settings */}
            {service.enabled && (
              <div className="mt-6 pt-6 border-t border-gray-200">
                <div className="flex items-center mb-4">
                  <Settings className="h-5 w-5 text-gray-400 mr-2" />
                  <h4 className="text-sm font-medium text-gray-900">Settings</h4>
                </div>
                {renderServiceSettings(service)}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
