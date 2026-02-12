import React, { useMemo, useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  Mail,
  Slack,
  Activity,
  Calendar,
  Table,
  Shield,
  Loader2,
  Zap,
  GitBranch,
  History,
  AlertTriangle,
  PlayCircle,
  CheckCircle2
} from 'lucide-react'
import { apiClient, AutomationLog, AutomationRule, AutomationSafetyStatus } from '../services/apiClient'
import { useToast } from '../components/Toast'
import { AutomationWizard } from '../components/AutomationWizard'
import { WebhookPayloadBuilder } from '../components/WebhookPayloadBuilder'
import { useAuth } from '../contexts/AuthContext'

type ConfigField = {
  key: string
  label: string
  type: 'text' | 'select' | 'number'
  helper?: string
  options?: { value: string; label: string }[]
}

type AutomationPreset = {
  id: string
  name: string
  description: string
  icon: React.ElementType
  triggerType: string
  actionType: string
  defaultConfig: Record<string, any>
  configFields: ConfigField[]
}

const automationPresets: AutomationPreset[] = [
  {
    id: 'gmail_crm',
    name: 'Gmail → CRM',
    description: 'Convert new inbound emails into CRM leads automatically.',
    icon: Mail,
    triggerType: 'email_received',
    actionType: 'update_crm_field',
    defaultConfig: { target_stage: 'new', tags: ['inbox'] },
    configFields: [
      {
        key: 'target_stage',
        label: 'Pipeline stage',
        type: 'select',
        options: [
          { value: 'new', label: 'New' },
          { value: 'contacted', label: 'Contacted' },
          { value: 'qualified', label: 'Qualified' },
          { value: 'booked', label: 'Booked' }
        ],
        helper: 'Stage to create the lead in'
      }
    ]
  },
  {
    id: 'lead_scoring',
    name: 'Lead Scoring',
    description: 'Score leads using AI classifications and prioritise outreach.',
    icon: Activity,
    triggerType: 'lead_created',
    actionType: 'update_crm_field',
    defaultConfig: { min_score: 6 },
    configFields: [
      {
        key: 'min_score',
        label: 'Alert threshold',
        type: 'number',
        helper: 'Notify when score is above this value'
      }
    ]
  },
  {
    id: 'slack_digest',
    name: 'Slack summaries',
    description: 'Send daily Slack digests of lead activity.',
    icon: Slack,
    triggerType: 'time_based',
    actionType: 'send_notification',
    defaultConfig: { channel: '#sales', frequency: 'daily' },
    configFields: [
      { key: 'channel', label: 'Slack channel', type: 'text', helper: 'Example: #leads' },
      {
        key: 'frequency',
        label: 'Summary cadence',
        type: 'select',
        options: [
          { value: 'daily', label: 'Daily' },
          { value: 'weekly', label: 'Weekly' }
        ]
      }
    ]
  },
  {
    id: 'email_sheets',
    name: 'Send Leads to Your Tools',
    description: 'Automatically send new leads and emails to your favorite apps like Slack, Google Sheets, or your own system. No coding required.',
    icon: Table,
    triggerType: 'email_received',
    actionType: 'trigger_webhook',
    defaultConfig: { destination: 'Google Sheets', sheet_url: '' },
    configFields: [
      {
        key: 'destination',
        label: 'Where to send data',
        type: 'select',
        options: [
          { value: 'Google Sheets', label: 'Google Sheets' },
          { value: 'Airtable', label: 'Airtable' }
        ],
        helper: 'Choose where you want your leads sent'
      },
      { key: 'sheet_url', label: 'Your webhook URL', type: 'text', helper: 'Paste the webhook URL from your app (we\'ll help you find it)' }
    ]
  },
  {
    id: 'calendar_followups',
    name: 'Calendar follow-ups',
    description: 'Auto-create follow-up reminders for hot leads.',
    icon: Calendar,
    triggerType: 'lead_stage_changed',
    actionType: 'schedule_follow_up',
    defaultConfig: { delay_hours: 24 },
    configFields: [
      {
        key: 'delay_hours',
        label: 'Reminder delay (hrs)',
        type: 'number',
        helper: 'Time after lead is qualified'
      }
    ]
  }
]

const findRuleForPreset = (rules: AutomationRule[] = [], presetId: string) => {
  return rules.find(rule => rule.action_parameters?.slug === presetId || rule.name === presetId)
}

const formatAbsoluteTimestamp = (timestamp?: string) => {
  if (!timestamp) {
    return 'No executions yet'
  }
  const parsed = new Date(timestamp)
  if (Number.isNaN(parsed.getTime())) {
    return 'Unknown timestamp'
  }
  return parsed.toLocaleString()
}

const formatRelativeTimestamp = (timestamp?: string) => {
  if (!timestamp) {
    return 'Never'
  }
  const parsed = new Date(timestamp)
  if (Number.isNaN(parsed.getTime())) {
    return 'Never'
  }
  const diffMs = Math.max(0, Date.now() - parsed.getTime())
  const diffSeconds = Math.floor(diffMs / 1000)
  if (diffSeconds < 60) return `${diffSeconds}s ago`
  const diffMinutes = Math.floor(diffSeconds / 60)
  if (diffMinutes < 60) return `${diffMinutes}m ago`
  const diffHours = Math.floor(diffMinutes / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  return `${diffDays}d ago`
}

const statusBadgeClass: Record<string, string> = {
  success: 'bg-emerald-500/10 text-emerald-500 dark:text-emerald-300',
  error: 'bg-rose-500/10 text-rose-500 dark:text-rose-300',
  pending: 'bg-amber-500/10 text-amber-500 dark:text-amber-300',
  idle: 'bg-brand-text/10 text-brand-text/70 dark:text-gray-300'
}

export const Automations: React.FC = () => {
  const { addToast } = useToast()
  const { user } = useAuth()
  const [showWizard, setShowWizard] = useState(true)
  const baseConfig = useMemo(() => {
    const defaults: Record<string, Record<string, any>> = {}
    automationPresets.forEach(preset => {
      defaults[preset.id] = { ...preset.defaultConfig }
    })
    return defaults
  }, [])
  const [configState, setConfigState] = useState<Record<string, Record<string, any>>>(baseConfig)

  const { data: rules = [], refetch: refetchRules, isLoading } = useQuery({
    queryKey: ['automation-rules'],
    queryFn: async () => {
      const data = await apiClient.getAutomationRules()
      const mapped: Record<string, Record<string, any>> = {}
      data.forEach(rule => {
        const slug = rule.action_parameters?.slug || rule.name
        const params = rule.action_parameters || {}
        
        // For webhook rules, extract payload separately
        if (rule.action_type === 'trigger_webhook') {
          mapped[slug] = {
            ...params,
            webhook_url: params.webhook_url || params.sheet_url || '',
            payload: params.payload || {}
          }
        } else {
          mapped[slug] = params
        }
      })
      setConfigState(prev => ({ ...prev, ...mapped }))
      return data
    },
    staleTime: 1 * 60 * 1000, // 1 minute
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchInterval: 2 * 60 * 1000, // Auto-refresh every 2 minutes
  })

  const { data: safetyStatus } = useQuery<AutomationSafetyStatus>({
    queryKey: ['automation-safety'],
    queryFn: () => apiClient.getAutomationSafetyStatus(),
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  })

  const { data: suggestions } = useQuery({
    queryKey: ['automation-suggestions'],
    queryFn: () => apiClient.getAutomationSuggestions(),
    staleTime: 5 * 60 * 1000, // 5 minutes - suggestions don't change often
    gcTime: 30 * 60 * 1000, // 30 minutes
  })

  const { data: automationLogs = [], refetch: refetchLogs, isFetching: logsLoading } = useQuery<AutomationLog[]>({
    queryKey: ['automation-logs'],
    queryFn: () => apiClient.getAutomationLogs({ limit: 50 }),
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 60 * 1000, // Auto-refresh every minute
  })

  const logsByPreset = useMemo(() => {
    const grouped: Record<string, AutomationLog[]> = {}
    automationLogs.forEach(log => {
      const key = log.slug || `rule-${log.rule_id}`
      if (!grouped[key]) {
        grouped[key] = []
      }
      grouped[key].push(log)
    })
    return grouped
  }, [automationLogs])

  const testPresetMutation = useMutation({
    mutationFn: (presetId: string) => apiClient.runAutomationPreset(presetId),
    onSuccess: (_, presetId) => {
      addToast({ type: 'success', title: `Preset ${presetId} ran successfully` })
      refetchLogs()
    },
    onError: (error: any) => {
      const message = error?.response?.data?.error || 'Preset failed to execute'
      addToast({ type: 'error', title: message })
    }
  })

  const handleTestPreset = (presetId: string) => {
    testPresetMutation.mutate(presetId)
  }

  const createMutation = useMutation({
    mutationFn: apiClient.createAutomationRule,
    onSuccess: () => {
      addToast({ type: 'success', title: 'Automation enabled' })
      refetchRules()
      refetchLogs()
    },
    onError: (error: any) => {
      const errorMessage = error?.response?.data?.message || error?.response?.data?.error || error?.message || 'Failed to enable automation'
      addToast({ 
        type: 'error', 
        title: 'Failed to enable automation',
        message: errorMessage
      })
      console.error('Automation creation error:', error)
    }
  })

  const updateMutation = useMutation({
    mutationFn: ({ ruleId, updates }: { ruleId: number; updates: Partial<AutomationRule> }) =>
      apiClient.updateAutomationRule(ruleId, updates),
    onSuccess: () => {
      addToast({ type: 'success', title: 'Automation updated' })
      refetchRules()
      refetchLogs()
    },
    onError: (error: any) => {
      const errorMessage = error?.response?.data?.message || error?.response?.data?.error || error?.message || 'Failed to update automation'
      addToast({ 
        type: 'error', 
        title: 'Failed to update automation',
        message: errorMessage
      })
      console.error('Automation update error:', error)
    }
  })

  const handleToggle = (preset: AutomationPreset, active: boolean) => {
    const existing = findRuleForPreset(rules, preset.id)
    if (active) {
      // Build action parameters
      const actionParams: Record<string, any> = {
        ...preset.defaultConfig,
        ...configState[preset.id],
        slug: preset.id
      }
      
      // For webhook actions, ensure webhook_url and payload are included
      if (preset.actionType === 'trigger_webhook') {
        actionParams.webhook_url = configState[preset.id]?.webhook_url || configState[preset.id]?.sheet_url || ''
        if (configState[preset.id]?.payload) {
          actionParams.payload = configState[preset.id].payload
        }
      }
      
      if (existing) {
        updateMutation.mutate({
          ruleId: existing.id,
          updates: {
            status: 'active',
            action_parameters: actionParams
          }
        })
      } else {
        createMutation.mutate({
          name: preset.name,
          description: preset.description,
          trigger_type: preset.triggerType,
          trigger_conditions: { ...preset.defaultConfig, slug: preset.id },
          action_type: preset.actionType,
          action_parameters: actionParams
        })
      }
    } else if (existing) {
      updateMutation.mutate({
        ruleId: existing.id,
        updates: { status: 'inactive' }
      })
    }
  }

  const handleConfigChange = (presetId: string, field: string, value: any) => {
    setConfigState(prev => ({
      ...prev,
      [presetId]: {
        ...prev[presetId],
        [field]: value
      }
    }))
  }

  const handleWebhookUrlChange = (presetId: string, url: string) => {
    setConfigState(prev => ({
      ...prev,
      [presetId]: {
        ...prev[presetId],
        webhook_url: url,
        sheet_url: url // Keep for backward compatibility
      }
    }))
  }

  const handleWebhookPayloadChange = (presetId: string, payload: Record<string, any>) => {
    setConfigState(prev => ({
      ...prev,
      [presetId]: {
        ...prev[presetId],
        payload: payload
      }
    }))
  }

  const renderField = (presetId: string, field: ConfigField) => {
    const value = configState[presetId]?.[field.key] ?? ''
    if (field.type === 'select') {
      return (
        <select
          className="w-full rounded-lg border border-brand-text/20 px-3 py-2 bg-white dark:bg-gray-900"
          value={value}
          onChange={(e) => handleConfigChange(presetId, field.key, e.target.value)}
        >
          {field.options?.map(option => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      )
    }
    return (
      <input
        type={field.type === 'number' ? 'number' : 'text'}
        className="w-full rounded-lg border border-brand-text/20 px-3 py-2 bg-white dark:bg-gray-900"
        value={value}
        onChange={(e) => handleConfigChange(presetId, field.key, field.type === 'number' ? Number(e.target.value) : e.target.value)}
      />
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-wide text-brand-text/60 dark:text-gray-400">Automation Studio</p>
          <h1 className="text-3xl font-bold text-brand-text dark:text-white">Workflow Automations</h1>
          <p className="mt-2 text-brand-text/70 dark:text-gray-300">
            Toggle always-on workflows without writing code. Each automation runs using your connected Gmail and CRM.
          </p>
        </div>
        <div className="rounded-2xl border border-brand-text/10 dark:border-gray-700 bg-white dark:bg-gray-800 px-5 py-3 shadow-sm">
          <div className="flex items-center gap-3">
            <Shield className="h-5 w-5 text-brand-primary" />
            <div>
              <p className="text-xs uppercase tracking-wide text-brand-text/60 dark:text-gray-400">Safety</p>
              <p className="text-sm font-semibold text-brand-text dark:text-white">
                {safetyStatus?.automation_enabled ? 'Enabled' : 'Disabled'} · {safetyStatus?.safety_level ?? 'normal'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Show wizard if user has no active automations */}
      {!isLoading && rules.filter((r: any) => r.status === 'active').length === 0 && showWizard && (
        <AutomationWizard
          onComplete={() => {
            setShowWizard(false)
            refetchRules()
          }}
          onSkip={() => setShowWizard(false)}
        />
      )}

      {isLoading ? (
        <div className="flex items-center justify-center py-20 text-brand-text/60">
          <Loader2 className="h-5 w-5 animate-spin mr-2" />
          Loading automations…
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {automationPresets.map((preset) => {
            const Icon = preset.icon
            const rule = findRuleForPreset(rules, preset.id)
            const isActive = rule?.status === 'active'
            const presetLogs = logsByPreset[preset.id] || []
            const lastLog = presetLogs[0]
            const statusKey = lastLog?.status || 'idle'
            const statusClass = statusBadgeClass[statusKey] || statusBadgeClass.idle
            const lastMessage = lastLog?.action_result?.message || lastLog?.error_message
            const isTesting = testPresetMutation.isPending && testPresetMutation.variables === preset.id
            return (
              <div key={preset.id} className="rounded-2xl border border-brand-text/10 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm flex flex-col gap-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-xl bg-brand-accent/20">
                      <Icon className="h-5 w-5 text-brand-primary" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-brand-text dark:text-white">{preset.name}</h3>
                      <p className="text-sm text-brand-text/70 dark:text-gray-400">{preset.description}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleToggle(preset, !isActive)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${isActive ? 'bg-brand-primary' : 'bg-brand-text/30'}`}
                  >
                    <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${isActive ? 'translate-x-6' : 'translate-x-1'}`} />
                  </button>
                </div>

                {preset.actionType === 'trigger_webhook' && (
                  <div className="space-y-4 mt-4">
                    <WebhookPayloadBuilder
                      webhookUrl={configState[preset.id]?.webhook_url || configState[preset.id]?.sheet_url || ''}
                      payload={configState[preset.id]?.payload || {}}
                      onUrlChange={(url) => handleWebhookUrlChange(preset.id, url)}
                      onPayloadChange={(payload) => handleWebhookPayloadChange(preset.id, payload)}
                      triggerType={preset.triggerType}
                    />
                  </div>
                )}

                {preset.actionType !== 'trigger_webhook' && preset.configFields.length > 0 && (
                  <div className="space-y-3">
                    {preset.configFields.map(field => (
                      <div key={field.key}>
                        <label className="text-sm font-medium text-brand-text dark:text-gray-200">{field.label}</label>
                        {renderField(preset.id, field)}
                        {field.helper && <p className="text-xs text-brand-text/60 dark:text-gray-400 mt-1">{field.helper}</p>}
                      </div>
                    ))}
                  </div>
                )}

                <div className="rounded-xl border border-brand-text/10 dark:border-gray-700 bg-brand-accent/5 dark:bg-gray-900 p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs uppercase tracking-wide text-brand-text/50 dark:text-gray-400">Last run</p>
                      <p className="text-sm font-medium text-brand-text dark:text-white">{formatAbsoluteTimestamp(lastLog?.executed_at)}</p>
                      <p className="text-xs text-brand-text/60 dark:text-gray-400">
                        {lastMessage ? lastMessage : lastLog ? 'Preset executed via backend' : 'No executions have been recorded yet'}
                      </p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${statusClass}`}>
                      {lastLog ? (lastLog.status === 'success' ? 'Healthy' : 'Needs attention') : 'Idle'}
                    </span>
                  </div>
                  {presetLogs.length > 0 && (
                    <div className="mt-3 space-y-1 max-h-24 overflow-y-auto pr-1 text-xs text-brand-text/70 dark:text-gray-300">
                      {presetLogs.slice(0, 3).map(log => (
                        <div key={log.execution_id} className="flex items-center justify-between">
                          <span className="truncate">{log.action_result?.summary || log.action_result?.message || log.status}</span>
                          <span>{formatRelativeTimestamp(log.executed_at)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between border-t border-brand-text/10 dark:border-gray-700 pt-4">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => handleTestPreset(preset.id)}
                      disabled={isTesting}
                      className={`text-sm font-medium inline-flex items-center gap-2 ${
                        isTesting ? 'text-brand-text/50 dark:text-gray-500 cursor-not-allowed' : 'text-brand-primary hover:text-brand-secondary'
                      }`}
                    >
                      <PlayCircle className="h-4 w-4" />
                      {isTesting ? 'Testing…' : 'Run Test'}
                    </button>
                    <button
                      onClick={() => handleToggle(preset, true)}
                      className="text-sm font-medium text-brand-primary hover:text-brand-secondary inline-flex items-center gap-2"
                    >
                      <Zap className="h-4 w-4" />
                      Save & Activate
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      <div className="rounded-2xl border border-brand-text/10 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <History className="h-5 w-5 text-brand-primary" />
            <div>
              <p className="text-xs uppercase tracking-wide text-brand-text/60 dark:text-gray-400">Automation activity</p>
              <h2 className="text-xl font-semibold text-brand-text dark:text-white">Recent executions</h2>
            </div>
          </div>
          {logsLoading && (
            <div className="flex items-center text-xs text-brand-text/60 dark:text-gray-400">
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Updating…
            </div>
          )}
        </div>
        {automationLogs.length === 0 ? (
          <div className="text-sm text-brand-text/60 dark:text-gray-400">No automation activity recorded yet.</div>
        ) : (
          <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
            {automationLogs.slice(0, 12).map(log => {
              const isSuccess = log.status === 'success'
              const StatusIcon = isSuccess ? CheckCircle2 : AlertTriangle
              return (
                <div key={log.execution_id} className="flex items-start justify-between gap-4 rounded-xl border border-brand-text/10 dark:border-gray-700 p-4">
                  <div className="flex items-start gap-3">
                    <div className={`p-2 rounded-full ${isSuccess ? 'bg-emerald-500/10 text-emerald-500 dark:text-emerald-300' : 'bg-rose-500/10 text-rose-500 dark:text-rose-300'}`}>
                      <StatusIcon className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-brand-text dark:text-white">{log.rule_name}</p>
                      <p className="text-sm text-brand-text/70 dark:text-gray-300 mt-1">
                        {log.action_result?.message || log.action_result?.summary || log.error_message || 'Automation completed successfully'}
                      </p>
                    </div>
                  </div>
                  <div className="text-right text-xs text-brand-text/60 dark:text-gray-400 min-w-[120px]">
                    <p>{formatAbsoluteTimestamp(log.executed_at)}</p>
                    <p>{formatRelativeTimestamp(log.executed_at)}</p>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {suggestions && suggestions.length > 0 && (
        <div className="rounded-2xl border border-brand-text/10 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-4">
            <GitBranch className="h-5 w-5 text-brand-primary" />
            <div>
              <p className="text-xs uppercase tracking-wide text-brand-text/60 dark:text-gray-400">AI recommendations</p>
              <h2 className="text-xl font-semibold text-brand-text dark:text-white">Suggested automations</h2>
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {suggestions.map((suggestion: any, idx: number) => (
              <div key={idx} className="rounded-xl border border-brand-text/10 dark:border-gray-700 p-4 text-sm text-brand-text/80 dark:text-gray-300">
                <p className="font-semibold text-brand-text dark:text-white">{suggestion.title || suggestion.name || 'Automation suggestion'}</p>
                <p className="mt-1">{suggestion.description || suggestion.reason || 'Optimize this workflow for better response times.'}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
