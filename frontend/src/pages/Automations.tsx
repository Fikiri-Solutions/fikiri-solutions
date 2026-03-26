import React, { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
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
  CheckCircle2,
  BarChart3
} from 'lucide-react'
import { apiClient, AutomationLog, AutomationRule, AutomationSafetyStatus } from '../services/apiClient'
import { useToast } from '../components/Toast'
import { AutomationWizard } from '../components/AutomationWizard'
import { WebhookPayloadBuilder } from '../components/WebhookPayloadBuilder'
import { useAuth } from '../contexts/AuthContext'
import { FIKIRI_LAST_AUTOMATION_CORRELATION_KEY } from '../constants/correlationDebug'

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
      { key: 'slack_webhook_url', label: 'Slack webhook URL', type: 'text', helper: 'Incoming Webhook URL from Slack (required for delivery)' },
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
  const [lastCorrelationId, setLastCorrelationId] = useState<string | null>(null)
  const [tracePreview, setTracePreview] = useState<string | null>(null)
  const [traceLoading, setTraceLoading] = useState(false)

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

  const { data: capabilities = [] } = useQuery({
    queryKey: ['automation-capabilities'],
    queryFn: () => apiClient.getAutomationCapabilities(),
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
  })

  const capabilityByAction = useMemo(() => {
    const map: Record<string, 'implemented' | 'partial' | 'stub'> = {}
    capabilities.forEach((c: { action_type: string; capability: string }) => {
      map[c.action_type] = c.capability as 'implemented' | 'partial' | 'stub'
    })
    return map
  }, [capabilities])

  const { data: automationMetrics, isFetching: metricsLoading } = useQuery({
    queryKey: ['automation-metrics'],
    queryFn: () => apiClient.getAutomationMetrics({ hours: 24 }),
    staleTime: 60 * 1000,
    gcTime: 5 * 60 * 1000,
    refetchInterval: 2 * 60 * 1000,
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
    onSuccess: (payload: { correlation_id?: string } | undefined, presetId) => {
      const cid =
        typeof payload?.correlation_id === 'string' && payload.correlation_id
          ? payload.correlation_id
          : null
      if (cid) {
        setLastCorrelationId(cid)
        setTracePreview(null)
        try {
          if (typeof sessionStorage !== 'undefined') {
            sessionStorage.setItem(FIKIRI_LAST_AUTOMATION_CORRELATION_KEY, cid)
          }
        } catch {
          /* ignore */
        }
      }
      addToast({
        type: 'success',
        title: `Preset ${presetId} ran successfully`,
        message: cid ? `Correlation: ${cid}` : undefined,
      })
      refetchLogs()
    },
    onError: (error: any) => {
      const data = error?.response?.data
      const message = data?.error || data?.message || 'Preset failed to execute'
      const is501 = error?.response?.status === 501
      addToast({
        type: 'error',
        title: is501 ? 'Action not implemented' : 'Preset failed',
        message: message
      })
    }
  })

  const handleTestPreset = (presetId: string) => {
    testPresetMutation.mutate(presetId)
  }

  const createMutation = useMutation({
    mutationFn: (rule: {
      name: string
      description: string
      trigger_type: string
      trigger_conditions: Record<string, any>
      action_type: string
      action_parameters: Record<string, any>
    }) => apiClient.createAutomationRule(rule),
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
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm uppercase tracking-wide text-brand-text/60 dark:text-gray-400">Automation Studio</p>
          <h1 className="text-2xl font-bold text-brand-text dark:text-white mt-0.5">Workflow Automations</h1>
          <p className="mt-1.5 text-sm text-brand-text/70 dark:text-gray-300 max-w-xl">
            Toggle always-on workflows without writing code. Each automation runs using your connected Gmail and CRM.
          </p>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          <div className="rounded-xl border border-brand-text/10 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-2.5 shadow-sm">
            <div className="flex items-center gap-2.5">
              <Shield className="h-4 w-4 text-brand-primary" />
              <div>
                <p className="text-xs uppercase tracking-wide text-brand-text/60 dark:text-gray-400">Safety</p>
                <p className="text-sm font-semibold text-brand-text dark:text-white">
                  {safetyStatus?.automation_enabled ? 'Enabled' : 'Disabled'} · {safetyStatus?.safety_level ?? 'normal'}
                </p>
              </div>
            </div>
          </div>
          <div className="rounded-xl border border-brand-text/10 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-2.5 shadow-sm min-w-[180px]">
            <div className="flex items-center gap-2.5">
              <BarChart3 className="h-4 w-4 text-brand-primary flex-shrink-0" />
              <div className="min-w-0">
                <p className="text-xs uppercase tracking-wide text-brand-text/60 dark:text-gray-400">Queue health</p>
                {metricsLoading ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-brand-text/50 mt-0.5" />
                ) : automationMetrics ? (
                  <p className="text-xs font-semibold text-brand-text dark:text-white leading-tight mt-0.5">
                    Q: {automationMetrics.queued ?? 0} · R: {automationMetrics.running ?? 0} · ✓ {automationMetrics.success ?? 0} · ✗ {automationMetrics.failed ?? 0}
                    {automationMetrics.success_rate_24h != null && (
                      <span className="block text-brand-text/70 dark:text-gray-300 font-normal mt-0.5">
                        {Math.round(automationMetrics.success_rate_24h * 100)}% success
                        {automationMetrics.p95_duration_seconds != null && ` · p95 ${automationMetrics.p95_duration_seconds}s`}
                      </span>
                    )}
                  </p>
                ) : (
                  <p className="text-xs text-brand-text/60 dark:text-gray-400 mt-0.5">No metrics yet</p>
                )}
              </div>
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
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {automationPresets.map((preset) => {
            const Icon = preset.icon
            const rule = findRuleForPreset(rules, preset.id)
            const isActive = rule?.status === 'active'
            const capability = capabilityByAction[preset.actionType] ?? 'implemented'
            const isStub = capability === 'stub'
            const isPartial = capability === 'partial'
            const presetLogs = logsByPreset[preset.id] || []
            const lastLog = presetLogs[0]
            const statusKey = lastLog?.status || 'idle'
            const statusClass = statusBadgeClass[statusKey] || statusBadgeClass.idle
            const lastMessage = lastLog?.action_result?.message || lastLog?.error_message
            const isTesting = testPresetMutation.isPending && testPresetMutation.variables === preset.id
            return (
              <div key={preset.id} className="rounded-xl border border-brand-text/10 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 shadow-sm flex flex-col gap-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="p-1.5 rounded-lg bg-brand-accent/20 flex-shrink-0">
                      <Icon className="h-4 w-4 text-brand-primary" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-base font-semibold text-brand-text dark:text-white">{preset.name}</h3>
                      <p className="text-xs text-brand-text/70 dark:text-gray-400 line-clamp-2">{preset.description}</p>
                      {isStub && (
                        <span className="inline-block mt-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-500/15 text-amber-600 dark:text-amber-400">
                          Not implemented yet
                        </span>
                      )}
                      {isPartial && !isStub && (
                        <span className="inline-block mt-1 px-2 py-0.5 rounded text-xs font-medium bg-blue-500/15 text-blue-600 dark:text-blue-400">
                          Partial (depends on configuration)
                        </span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => handleToggle(preset, !isActive)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${isActive ? 'bg-brand-primary' : 'bg-brand-text/30'}`}
                  >
                    <span className={`inline-block h-4 w-4 transform rounded-full bg-white dark:bg-gray-300 transition ${isActive ? 'translate-x-6' : 'translate-x-1'}`} />
                  </button>
                </div>

                {preset.actionType === 'trigger_webhook' && (
                  <div className="space-y-3 mt-1">
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
                  <div className="space-y-2">
                    {preset.configFields.map(field => (
                      <div key={field.key}>
                        <label className="text-xs font-medium text-brand-text dark:text-gray-200">{field.label}</label>
                        {renderField(preset.id, field)}
                        {field.helper && <p className="text-xs text-brand-text/60 dark:text-gray-400 mt-0.5">{field.helper}</p>}
                      </div>
                    ))}
                  </div>
                )}

                <div className="rounded-lg border border-brand-text/10 dark:border-gray-700 bg-brand-accent/5 dark:bg-gray-900 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-xs uppercase tracking-wide text-brand-text/50 dark:text-gray-400">Last run</p>
                      <p className="text-xs font-medium text-brand-text dark:text-white truncate">{formatAbsoluteTimestamp(lastLog?.executed_at)}</p>
                      <p className="text-xs text-brand-text/60 dark:text-gray-400 truncate" title={lastMessage || undefined}>
                        {lastMessage ? lastMessage : lastLog ? 'Preset executed via backend' : 'No executions yet'}
                      </p>
                    </div>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0 ${statusClass}`}>
                      {lastLog ? (lastLog.status === 'success' ? 'Healthy' : 'Needs attention') : 'Idle'}
                    </span>
                  </div>
                  {presetLogs.length > 0 && (
                    <div className="mt-2 space-y-0.5 max-h-16 overflow-y-auto pr-1 text-xs text-brand-text/70 dark:text-gray-300">
                      {presetLogs.slice(0, 3).map(log => (
                        <div key={log.execution_id} className="flex items-center justify-between">
                          <span className="truncate">{log.action_result?.summary || log.action_result?.message || log.status}</span>
                          <span>{formatRelativeTimestamp(log.executed_at)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between border-t border-brand-text/10 dark:border-gray-700 pt-3 gap-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <button
                      onClick={() => handleTestPreset(preset.id)}
                      disabled={isTesting}
                      className={`text-xs font-medium inline-flex items-center gap-1.5 ${
                        isTesting ? 'text-brand-text/50 dark:text-gray-500 cursor-not-allowed' : 'text-brand-primary hover:text-brand-secondary'
                      } ${isStub ? 'opacity-75' : ''}`}
                      title={isStub ? 'Run Test will return "Not implemented" until this action is built' : undefined}
                    >
                      <PlayCircle className="h-3.5 w-3.5" />
                      {isTesting ? 'Testing…' : 'Run Test'}
                    </button>
                    <button
                      onClick={() => handleToggle(preset, true)}
                      className="text-xs font-medium text-brand-primary hover:text-brand-secondary inline-flex items-center gap-1.5"
                    >
                      <Zap className="h-3.5 w-3.5" />
                      Save & Activate
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      <div className="rounded-xl border border-brand-text/10 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 shadow-sm">
        <div className="flex items-center justify-between mb-3 gap-3">
          <div className="flex items-center gap-2.5">
            <History className="h-4 w-4 text-brand-primary" />
            <div>
              <p className="text-xs uppercase tracking-wide text-brand-text/60 dark:text-gray-400">Automation activity</p>
              <h2 className="text-lg font-semibold text-brand-text dark:text-white">Recent executions</h2>
            </div>
          </div>
          {logsLoading && (
            <div className="flex items-center text-xs text-brand-text/60 dark:text-gray-400">
              <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />
              Updating…
            </div>
          )}
        </div>
        {automationLogs.length === 0 ? (
          <div className="text-sm text-brand-text/60 dark:text-gray-400">No automation activity recorded yet.</div>
        ) : (
          <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
            {automationLogs.slice(0, 12).map(log => {
              const isSuccess = log.status === 'success'
              const StatusIcon = isSuccess ? CheckCircle2 : AlertTriangle
              return (
                <div key={log.execution_id} className="flex items-start justify-between gap-3 rounded-lg border border-brand-text/10 dark:border-gray-700 p-3">
                  <div className="flex items-start gap-2 min-w-0">
                    <div className={`p-1.5 rounded-full flex-shrink-0 ${isSuccess ? 'bg-emerald-500/10 text-emerald-500 dark:text-emerald-300' : 'bg-rose-500/10 text-rose-500 dark:text-rose-300'}`}>
                      <StatusIcon className="h-3.5 w-3.5" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-brand-text dark:text-white">{log.rule_name}</p>
                      <p className="text-xs text-brand-text/70 dark:text-gray-300 mt-0.5 line-clamp-2">
                        {log.action_result?.message || log.action_result?.summary || log.error_message || 'Automation completed successfully'}
                      </p>
                    </div>
                  </div>
                  <div className="text-right text-xs text-brand-text/60 dark:text-gray-400 flex-shrink-0">
                    <p>{formatRelativeTimestamp(log.executed_at)}</p>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {suggestions && suggestions.length > 0 && (
        <div className="rounded-xl border border-brand-text/10 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 shadow-sm">
          <div className="flex items-center gap-2.5 mb-3">
            <GitBranch className="h-4 w-4 text-brand-primary" />
            <div>
              <p className="text-xs uppercase tracking-wide text-brand-text/60 dark:text-gray-400">AI recommendations</p>
              <h2 className="text-lg font-semibold text-brand-text dark:text-white">Suggested automations</h2>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {suggestions.map((suggestion: any, idx: number) => (
              <div key={idx} className="rounded-lg border border-brand-text/10 dark:border-gray-700 p-3 text-sm text-brand-text/80 dark:text-gray-300">
                <p className="font-semibold text-brand-text dark:text-white text-sm">{suggestion.title || suggestion.name || 'Automation suggestion'}</p>
                <p className="mt-0.5 text-xs">{suggestion.description || suggestion.reason || 'Optimize this workflow for better response times.'}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <details className="rounded-xl border border-dashed border-brand-text/20 dark:border-gray-600 bg-white/50 dark:bg-gray-900/40 p-4 text-xs text-brand-text/70 dark:text-gray-400">
        <summary className="cursor-pointer font-medium text-brand-text dark:text-gray-200 select-none">
          Debug: correlation ID &amp; trace
        </summary>
        <p className="mt-2 text-[11px] leading-relaxed">
          Top-level <code className="px-1 rounded bg-brand-text/10">correlation_id</code> is canonical on API
          responses. Use{' '}
          <code className="px-1 rounded bg-brand-text/10">GET /api/debug/correlation/&lt;id&gt;</code> for a
          stitched view (see <code className="px-1 rounded bg-brand-text/10">docs/CORRELATION_AND_EVENTS.md</code>
          ).
        </p>
        <p className="mt-2 text-[11px]">
          <Link
            to={
              lastCorrelationId
                ? `/debug/correlation?id=${encodeURIComponent(lastCorrelationId)}`
                : '/debug/correlation'
            }
            className="font-medium text-brand-primary hover:underline dark:text-brand-accent"
          >
            Open full correlation debug page →
          </Link>
        </p>
        {lastCorrelationId ? (
          <div className="mt-3 space-y-2">
            <p className="break-all font-mono text-[11px] text-brand-text dark:text-gray-200">{lastCorrelationId}</p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="rounded-md border border-brand-text/20 px-2 py-1 text-xs font-medium text-brand-text dark:text-gray-200 hover:bg-brand-text/5"
                onClick={() => {
                  void navigator.clipboard.writeText(lastCorrelationId)
                  addToast({ type: 'success', title: 'Copied correlation ID' })
                }}
              >
                Copy ID
              </button>
              <button
                type="button"
                disabled={traceLoading}
                className="rounded-md border border-brand-primary/40 bg-brand-primary/10 px-2 py-1 text-xs font-medium text-brand-primary disabled:opacity-50"
                onClick={async () => {
                  setTraceLoading(true)
                  setTracePreview(null)
                  try {
                    const t = await apiClient.getCorrelationTrace(lastCorrelationId)
                    setTracePreview(JSON.stringify(t, null, 2))
                  } catch (e: unknown) {
                    const msg =
                      e && typeof e === 'object' && 'response' in e
                        ? String((e as { response?: { data?: { error?: string } } }).response?.data?.error)
                        : 'Trace request failed'
                    addToast({ type: 'error', title: 'Trace failed', message: msg })
                  } finally {
                    setTraceLoading(false)
                  }
                }}
              >
                {traceLoading ? 'Loading…' : 'Load stitched trace'}
              </button>
            </div>
            {tracePreview ? (
              <pre className="mt-2 max-h-56 overflow-auto rounded-md border border-brand-text/10 bg-black/5 dark:bg-black/30 p-2 text-[10px] leading-snug text-brand-text dark:text-gray-200">
                {tracePreview}
              </pre>
            ) : null}
          </div>
        ) : (
          <p className="mt-2 text-[11px]">Run a preset test above to capture the last correlation ID.</p>
        )}
      </details>
    </div>
  )
}
