import React, { useState, useEffect, useCallback } from 'react'
import { 
  Code, 
  Play, 
  Copy, 
  Check, 
  Plus, 
  Trash2, 
  ChevronDown, 
  ChevronRight,
  Loader2,
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  Info
} from 'lucide-react'
import { webhookTemplates, webhookVariables, WebhookTemplate, replaceVariables } from '../utils/webhookTemplates'
import { Button } from './ui/Button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import { useToast } from './Toast'
import { useAuth } from '../contexts/AuthContext'

interface WebhookPayloadBuilderProps {
  webhookUrl: string
  payload: Record<string, any>
  onUrlChange: (url: string) => void
  onPayloadChange: (payload: Record<string, any>) => void
  triggerType?: string
}

export const WebhookPayloadBuilder: React.FC<WebhookPayloadBuilderProps> = ({
  webhookUrl,
  payload,
  onUrlChange,
  onPayloadChange,
  triggerType = 'email_received'
}) => {
  const { user } = useAuth()
  const { addToast } = useToast()
  const [selectedTemplate, setSelectedTemplate] = useState<WebhookTemplate | null>(null)
  const [showJsonEditor, setShowJsonEditor] = useState(false)
  const [jsonEditorValue, setJsonEditorValue] = useState('')
  const [isTesting, setIsTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  const [expandedFields, setExpandedFields] = useState<Set<string>>(new Set())
  const [customFields, setCustomFields] = useState<Array<{ key: string; value: any }>>([])

  // Initialize with custom template if payload exists
  useEffect(() => {
    if (payload && Object.keys(payload).length > 0) {
      // Check if payload matches a template
      const matchingTemplate = webhookTemplates.find(template => {
        const templateKeys = Object.keys(template.defaultPayload)
        const payloadKeys = Object.keys(payload)
        return templateKeys.some(key => payloadKeys.includes(key))
      })
      
      if (matchingTemplate) {
        setSelectedTemplate(matchingTemplate)
      } else {
        setSelectedTemplate(webhookTemplates.find(t => t.id === 'custom') || null)
      }
    }
  }, [])

  // Update JSON editor when payload changes
  useEffect(() => {
    if (showJsonEditor) {
      setJsonEditorValue(JSON.stringify(payload, null, 2))
    }
  }, [payload, showJsonEditor])

  const handleTemplateSelect = (template: WebhookTemplate) => {
    setSelectedTemplate(template)
    const newPayload = JSON.parse(JSON.stringify(template.defaultPayload))
    onPayloadChange(newPayload)
    if (template.exampleUrl && !webhookUrl) {
      onUrlChange(template.exampleUrl)
    }
    addToast({
      type: 'info',
      title: 'Template Applied',
      message: `${template.name} template loaded. Customize the fields below.`
    })
  }

  const handleFieldChange = (key: string, value: any) => {
    const newPayload = { ...payload }
    
    // Handle nested keys (e.g., "fields.Email")
    if (key.includes('.')) {
      const [parent, child] = key.split('.')
      if (!newPayload[parent]) {
        newPayload[parent] = {}
      }
      newPayload[parent][child] = value
    } else {
      newPayload[key] = value
    }
    
    onPayloadChange(newPayload)
  }

  const handleJsonEditorChange = (value: string) => {
    setJsonEditorValue(value)
    try {
      const parsed = JSON.parse(value)
      onPayloadChange(parsed)
    } catch (e) {
      // Invalid JSON, but keep the editor value
    }
  }

  const handleAddCustomField = () => {
    const newField = { key: '', value: '' }
    setCustomFields([...customFields, newField])
  }

  const handleCustomFieldChange = (index: number, key: string, value: any) => {
    const updated = [...customFields]
    updated[index] = { key, value }
    setCustomFields(updated)
    
    const newPayload = { ...payload }
    if (key) {
      newPayload[key] = value
    }
    onPayloadChange(newPayload)
  }

  const handleRemoveCustomField = (index: number) => {
    const updated = [...customFields]
    const field = updated[index]
    updated.splice(index, 1)
    setCustomFields(updated)
    
    const newPayload = { ...payload }
    delete newPayload[field.key]
    onPayloadChange(newPayload)
  }

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(payload, null, 2))
    addToast({
      type: 'success',
      title: 'Copied!',
      message: 'Webhook payload copied to clipboard'
    })
  }

  const handleTestWebhook = async () => {
    if (!webhookUrl) {
      addToast({
        type: 'error',
        title: 'Missing URL',
        message: 'Please enter a webhook URL first'
      })
      return
    }

    setIsTesting(true)
    setTestResult(null)

    try {
      // Create sample trigger data based on trigger type
      const sampleTriggerData: Record<string, any> = {
        event_type: triggerType,
        timestamp: new Date().toISOString(),
        user_id: user?.id || 1
      }

      if (triggerType === 'email_received') {
        sampleTriggerData.sender_email = 'sample@example.com'
        sampleTriggerData.subject = 'Sample Email Subject'
        sampleTriggerData.text = 'This is a sample email body for testing'
      } else if (triggerType === 'lead_created') {
        sampleTriggerData.lead_id = 1
        sampleTriggerData.lead_name = 'Sample Lead'
        sampleTriggerData.lead_email = 'lead@example.com'
      } else if (triggerType === 'lead_stage_changed') {
        sampleTriggerData.lead_id = 1
        sampleTriggerData.old_stage = 'new'
        sampleTriggerData.new_stage = 'qualified'
      }

      // Replace variables in payload
      const testPayload = replaceVariables(payload, sampleTriggerData, user?.id)

      // Send test request
      const response = await fetch(webhookUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(testPayload)
      })

      if (response.ok) {
        const responseText = await response.text()
        setTestResult({
          success: true,
          message: `Webhook sent successfully! Status: ${response.status}${responseText ? `\nResponse: ${responseText.substring(0, 200)}` : ''}`
        })
        addToast({
          type: 'success',
          title: 'Test Successful',
          message: `Webhook sent successfully (${response.status})`
        })
      } else {
        const errorText = await response.text()
        setTestResult({
          success: false,
          message: `Webhook failed: ${response.status} ${response.statusText}${errorText ? `\nError: ${errorText.substring(0, 200)}` : ''}`
        })
        addToast({
          type: 'error',
          title: 'Test Failed',
          message: `Webhook returned ${response.status}: ${response.statusText}`
        })
      }
    } catch (error: any) {
      setTestResult({
        success: false,
        message: `Error: ${error.message || 'Failed to send webhook'}`
      })
      addToast({
        type: 'error',
        title: 'Test Failed',
        message: error.message || 'Failed to send webhook'
      })
    } finally {
      setIsTesting(false)
    }
  }

  const renderFieldEditor = (key: string, value: any, path: string = '') => {
    const fullPath = path ? `${path}.${key}` : key
    const isExpanded = expandedFields.has(fullPath)

    if (value && typeof value === 'object' && !Array.isArray(value)) {
      return (
        <div key={key} className="border-l-2 border-gray-200 dark:border-gray-700 pl-4 ml-2">
          <button
            type="button"
            onClick={() => {
              const newExpanded = new Set(expandedFields)
              if (isExpanded) {
                newExpanded.delete(fullPath)
              } else {
                newExpanded.add(fullPath)
              }
              setExpandedFields(newExpanded)
            }}
            className="flex items-center gap-2 text-sm font-medium text-brand-text dark:text-white mb-2"
          >
            {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            {key}
          </button>
          {isExpanded && (
            <div className="space-y-3 ml-6">
              {Object.entries(value).map(([subKey, subValue]) =>
                renderFieldEditor(subKey, subValue, fullPath)
              )}
            </div>
          )}
        </div>
      )
    }

    return (
      <div key={key} className="space-y-1">
        <label className="block text-sm font-medium text-brand-text dark:text-gray-300">
          {key}
        </label>
        {typeof value === 'boolean' ? (
          <select
            className="w-full rounded-lg border border-brand-text/20 px-3 py-2 bg-white dark:bg-gray-900 text-brand-text dark:text-white"
            value={String(value)}
            onChange={(e) => handleFieldChange(fullPath, e.target.value === 'true')}
          >
            <option value="true">True</option>
            <option value="false">False</option>
          </select>
        ) : typeof value === 'number' ? (
          <input
            type="number"
            className="w-full rounded-lg border border-brand-text/20 px-3 py-2 bg-white dark:bg-gray-900 text-brand-text dark:text-white"
            value={value}
            onChange={(e) => handleFieldChange(fullPath, Number(e.target.value))}
          />
        ) : (
          <input
            type="text"
            className="w-full rounded-lg border border-brand-text/20 px-3 py-2 bg-white dark:bg-gray-900 text-brand-text dark:text-white"
            value={String(value)}
            onChange={(e) => handleFieldChange(fullPath, e.target.value)}
            placeholder={`Enter ${key}...`}
          />
        )}
        <p className="text-xs text-brand-text/60 dark:text-gray-500">
          Use variables like {'{sender_email}'}, {'{subject}'}, {'{timestamp}'}
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Webhook URL Input */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-brand-text dark:text-white">
          Your App's Webhook URL <span className="text-red-500">*</span>
        </label>
        <input
          type="url"
          className="w-full rounded-lg border border-brand-text/20 px-4 py-2 bg-white dark:bg-gray-900 text-brand-text dark:text-white"
          value={webhookUrl}
          onChange={(e) => onUrlChange(e.target.value)}
          placeholder="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
        />
        <p className="text-xs text-brand-text/60 dark:text-gray-500">
          This is like an address where we'll send your leads. Your app (Slack, Google Sheets, etc.) will give you this URL when you set up a webhook.
        </p>
      </div>

      {/* Template Selection */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <label className="block text-sm font-medium text-brand-text dark:text-white">
              Choose Your App (Optional)
            </label>
            <p className="text-xs text-brand-text/60 dark:text-gray-500 mt-1">
              Pick the app you want to send data to, or choose "Custom" to connect to your own system
            </p>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setShowJsonEditor(!showJsonEditor)}
          >
            <Code className="h-4 w-4 mr-2" />
            {showJsonEditor ? 'Visual Editor' : 'Advanced'}
          </Button>
        </div>
        
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {webhookTemplates.map((template) => (
            <button
              key={template.id}
              type="button"
              onClick={() => handleTemplateSelect(template)}
              className={`p-3 rounded-lg border-2 text-left transition-all ${
                selectedTemplate?.id === template.id
                  ? 'border-brand-primary bg-brand-primary/10'
                  : 'border-brand-text/10 hover:border-brand-primary/50'
              }`}
            >
              <div className="text-2xl mb-1">{template.icon}</div>
              <div className="text-sm font-medium text-brand-text dark:text-white">
                {template.name}
              </div>
              <div className="text-xs text-brand-text/60 dark:text-gray-400 mt-1">
                {template.description}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Payload Editor */}
      {showJsonEditor ? (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="block text-sm font-medium text-brand-text dark:text-white">
              Payload JSON
            </label>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleCopyJson}
            >
              <Copy className="h-4 w-4 mr-2" />
              Copy
            </Button>
          </div>
          <textarea
            className="w-full h-64 font-mono text-sm rounded-lg border border-brand-text/20 px-4 py-3 bg-gray-50 dark:bg-gray-900 text-brand-text dark:text-white"
            value={jsonEditorValue}
            onChange={(e) => handleJsonEditorChange(e.target.value)}
            placeholder='{"key": "value"}'
          />
          <p className="text-xs text-brand-text/60 dark:text-gray-500">
            Edit JSON directly. Use variables like {'{sender_email}'}, {'{subject}'}, {'{timestamp}'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="block text-sm font-medium text-brand-text dark:text-white">
              Payload Fields
            </label>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setShowJsonEditor(true)}
            >
              <Code className="h-4 w-4 mr-2" />
              View JSON
            </Button>
          </div>

          {selectedTemplate && selectedTemplate.fields.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">{selectedTemplate.name} Fields</CardTitle>
                <CardDescription className="text-xs">
                  Configure template-specific fields
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {selectedTemplate.fields.map((field) => (
                  <div key={field.key} className="space-y-1">
                    <label className="block text-sm font-medium text-brand-text dark:text-gray-300">
                      {field.label}
                      {field.required && <span className="text-red-500 ml-1">*</span>}
                    </label>
                    {field.type === 'select' && field.options ? (
                      <select
                        className="w-full rounded-lg border border-brand-text/20 px-3 py-2 bg-white dark:bg-gray-900 text-brand-text dark:text-white"
                        value={payload[field.key] || field.defaultValue || ''}
                        onChange={(e) => handleFieldChange(field.key, e.target.value)}
                      >
                        {field.options.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type={field.type}
                        className="w-full rounded-lg border border-brand-text/20 px-3 py-2 bg-white dark:bg-gray-900 text-brand-text dark:text-white"
                        value={payload[field.key] || field.defaultValue || ''}
                        onChange={(e) => handleFieldChange(field.key, e.target.value)}
                        placeholder={field.placeholder}
                        required={field.required}
                      />
                    )}
                    {field.helper && (
                      <p className="text-xs text-brand-text/60 dark:text-gray-500">
                        {field.helper}
                      </p>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Payload Structure Editor */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Payload Structure</CardTitle>
              <CardDescription className="text-xs">
                Edit the webhook payload structure
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {Object.entries(payload).map(([key, value]) => renderFieldEditor(key, value))}
              
              {/* Custom Fields */}
              {customFields.map((field, index) => (
                <div key={index} className="flex items-center gap-2">
                  <input
                    type="text"
                    className="flex-1 rounded-lg border border-brand-text/20 px-3 py-2 bg-white dark:bg-gray-900 text-brand-text dark:text-white"
                    placeholder="Field name"
                    value={field.key}
                    onChange={(e) => handleCustomFieldChange(index, e.target.value, field.value)}
                  />
                  <input
                    type="text"
                    className="flex-1 rounded-lg border border-brand-text/20 px-3 py-2 bg-white dark:bg-gray-900 text-brand-text dark:text-white"
                    placeholder="Field value"
                    value={field.value}
                    onChange={(e) => handleCustomFieldChange(index, field.key, e.target.value)}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => handleRemoveCustomField(index)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
              
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleAddCustomField}
                className="w-full"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Custom Field
              </Button>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Available Variables */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Info className="h-4 w-4" />
            What Information Can We Send?
          </CardTitle>
          <CardDescription className="text-xs">
            Click any item below to copy it. Use these in your message to include real data (like the lead's name or email).
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {webhookVariables.map((variable) => (
              <Badge
                key={variable.key}
                variant="outline"
                className="text-xs font-mono cursor-pointer hover:bg-brand-primary/10"
                onClick={() => {
                  navigator.clipboard.writeText(variable.key)
                  addToast({
                    type: 'success',
                    title: 'Copied!',
                    message: `${variable.label} copied to clipboard`
                  })
                }}
                title={variable.description}
              >
                {variable.label}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* JSON Preview */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">JSON Preview</CardTitle>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleCopyJson}
            >
              <Copy className="h-4 w-4 mr-2" />
              Copy JSON
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <pre className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg text-xs font-mono overflow-x-auto">
            {JSON.stringify(payload, null, 2)}
          </pre>
        </CardContent>
      </Card>

      {/* Test Webhook */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Test Your Connection</CardTitle>
          <CardDescription className="text-xs">
            Send a test message to make sure everything is working before you activate this automation
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button
            type="button"
            onClick={handleTestWebhook}
            disabled={isTesting || !webhookUrl}
            className="w-full"
          >
            {isTesting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Sending test...
              </>
            ) : (
              <>
                <Play className="h-4 w-4 mr-2" />
                Send Test Message
              </>
            )}
          </Button>

          {testResult && (
            <div className={`p-4 rounded-lg border ${
              testResult.success
                ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
            }`}>
              <div className="flex items-start gap-2">
                {testResult.success ? (
                  <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400 mt-0.5" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 mt-0.5" />
                )}
                <div className="flex-1">
                  <p className={`text-sm font-medium ${
                    testResult.success
                      ? 'text-green-800 dark:text-green-200'
                      : 'text-red-800 dark:text-red-200'
                  }`}>
                    {testResult.success ? 'Test Successful' : 'Test Failed'}
                  </p>
                  <pre className="text-xs mt-2 whitespace-pre-wrap font-mono">
                    {testResult.message}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

