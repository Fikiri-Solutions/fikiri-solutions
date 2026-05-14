import React, { useCallback, useEffect, useMemo, useState } from 'react'
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
import {
  TriggerIfGroup,
  TriggerIfConditionRow,
  TriggerIfGroupValue,
} from '../components/TriggerIfGroup'
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
  /** Static UX note when marketing copy exceeds what the engine integrates. */
  honestyNote?: string
}

const automationPresets: AutomationPreset[] = [
  {
    id: 'inbound_crm_sync',
    name: 'Inbound email → CRM',
    description: 'When email matches your rules, upsert or enrich the CRM lead (stage/tags).',
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
          { value: 'replied', label: 'Replied' },
          { value: 'qualified', label: 'Qualified' },
          { value: 'closed', label: 'Closed' }
        ],
        helper: 'Must match CRM stages (see CRM page)'
      }
    ]
  },
  {
    id: 'lead_scoring',
    name: 'Lead Scoring',
    description: 'On new leads, update CRM fields when conditions match (lead score is computed by the CRM scorer).',
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
    description: 'POST lead/email payload to any HTTPS URL (bring your own Zapier, Sheets script, Airtable webhook, etc.).',
    icon: Table,
    triggerType: 'email_received',
    actionType: 'trigger_webhook',
    defaultConfig: { destination: 'Google Sheets', sheet_url: '' },
    honestyNote:
      'Webhook only: there is no native Google Sheets or Airtable connector in this preset—only a signed or plain HTTP POST.',
    configFields: [
      {
        key: 'destination',
        label: 'Where to send data',
        type: 'select',
        options: [
          { value: 'Google Sheets', label: 'Google Sheets (via webhook you configure)' },
          { value: 'Airtable', label: 'Airtable (via webhook you configure)' }
        ],
        helper: 'Label for your notes; delivery is always the webhook URL below'
      },
      {
        key: 'sheet_url',
        label: 'Webhook URL',
        type: 'text',
        helper: 'Must be reachable from the Fikiri backend (HTTPS)'
      }
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

function emptyTriggerIfByPreset(): Record<string, TriggerIfGroupValue> {
  const init: Record<string, TriggerIfGroupValue> = {}
  automationPresets.forEach(p => {
    init[p.id] = { match: 'all', conditions: [] }
  })
  return init
}

function normalizeTriggerConditions(tc: unknown): Record<string, unknown> | undefined {
  if (tc == null) return undefined
  if (typeof tc === 'string') {
    try {
      return JSON.parse(tc) as Record<string, unknown>
    } catch {
      return undefined
    }
  }
  if (typeof tc === 'object') return tc as Record<string, unknown>
  return undefined
}

function deriveIfGroupFromRule(
  tc: Record<string, unknown> | undefined,
  triggerType: string
): TriggerIfGroupValue {
  const base: TriggerIfGroupValue = { match: 'all', conditions: [] }
  const obj = normalizeTriggerConditions(tc)
  if (!obj) return base
  const ifBlock = (obj as { if?: { conditions?: TriggerIfConditionRow[] } }).if
  if (Array.isArray(ifBlock?.conditions) && ifBlock.conditions.length > 0) {
    return {
      match: 'all',
      conditions: ifBlock.conditions.map(c => ({
        field: c.field,
        op: c.op,
        value: c.value,
      })),
    }
  }
  const conds: TriggerIfConditionRow[] = []
  const legacy = obj as { sender_domain?: string; source?: string }
  if (triggerType === 'email_received' && legacy.sender_domain) {
    conds.push({ field: 'sender_email', op: 'ends_with', value: String(legacy.sender_domain) })
  }
  if (triggerType === 'lead_created' && legacy.source) {
    conds.push({ field: 'source', op: 'equals', value: String(legacy.source) })
  }
  return { match: 'all', conditions: conds }
}

function mapRuleToConfigSlice(rule: AutomationRule | undefined, preset: AutomationPreset, defaults: Record<string, any>) {
  if (!rule) {
    return { ...defaults }
  }
  const params = rule.action_parameters || {}
  if (rule.action_type === 'trigger_webhook') {
    return {
      ...params,
      webhook_url: params.webhook_url || params.sheet_url || '',
      payload: params.payload || {},
    }
  }
  return { ...params }
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
  const [triggerIfByPreset, setTriggerIfByPreset] =
    useState<Record<string, TriggerIfGroupValue>>(emptyTriggerIfByPreset)
  const [dirtyByPreset, setDirtyByPreset] = useState<Record<string, boolean>>({})
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
      setConfigState(prev => {
        const next = { ...prev }
        Object.entries(mapped).forEach(([slug, params]) => {
          if (dirtyByPreset[slug]) return
          next[slug] = params
        })
        return next
      })
      return data
    },
    staleTime: 1 * 60 * 1000, // 1 minute
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchInterval: 2 * 60 * 1000, // Auto-refresh every 2 minutes
  })

  useEffect(() => {
    if (isLoading) return
    setTriggerIfByPreset(prev => {
      const next = { ...prev }
      automationPresets.forEach(preset => {
        if (!next[preset.id]) {
          next[preset.id] = { match: 'all', conditions: [] }
        }
      })
      rules.forEach((rule: AutomationRule) => {
        const slug = rule.action_parameters?.slug ?? ''
        if (!slug || next[slug] === undefined || dirtyByPreset[slug]) return
        next[slug] = deriveIfGroupFromRule(rule.trigger_conditions, rule.trigger_type)
      })
      return next
    })
  }, [rules, isLoading, dirtyByPreset])

  const discardLocalChanges = useCallback(
    (preset: AutomationPreset) => {
      const rule = findRuleForPreset(rules, preset.id)
      setDirtyByPreset(prev => ({ ...prev, [preset.id]: false }))
      setConfigState(prev => ({
        ...prev,
        [preset.id]: mapRuleToConfigSlice(rule, preset, baseConfig[preset.id]),
      }))
      setTriggerIfByPreset(prev => ({
        ...prev,
        [preset.id]: rule
          ? deriveIfGroupFromRule(rule.trigger_conditions, rule.trigger_type)
          : { match: 'all', conditions: [] },
      }))
    },
    [rules, baseConfig]
  )

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

  const {
    data: capabilities = [],
    isError: capabilitiesQueryError,
    isFetched: capabilitiesFetched
  } = useQuery({
    queryKey: ['automation-capabilities'],
    queryFn: () => apiClient.getAutomationCapabilities(),
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
  })
  const capabilitiesReady = capabilitiesFetched && !capabilitiesQueryError && capabilities.length > 0

  const { data: triggerConditionMeta } = useQuery({
    queryKey: ['automation-trigger-condition-metadata'],
    queryFn: () => apiClient.getTriggerConditionMetadata(),
    staleTime: 60 * 60 * 1000,
    gcTime: 24 * 60 * 60 * 1000,
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
    onSuccess: (payload: { success?: boolean; correlation_id?: string; data?: { correlation_id?: string }; error?: string; message?: string } | undefined, presetId) => {
      if (payload && typeof payload === 'object' && payload.success === false) {
        addToast({
          type: 'error',
          title: 'Preset did not complete',
          message: payload.error || payload.message || 'Check logs and configuration'
        })
        return
      }
      const fromData = payload?.data?.correlation_id
      const fromRoot = payload?.correlation_id
      const cid =
        typeof fromData === 'string' && fromData
          ? fromData
          : typeof fromRoot === 'string' && fromRoot
            ? fromRoot
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
    mutationFn: (payload: {
      presetId: string
      rule: {
      name: string
      description: string
      trigger_type: string
      trigger_conditions: Record<string, any>
      action_type: string
      action_parameters: Record<string, any>
      }
    }) => apiClient.createAutomationRule(payload.rule),
    onSuccess: (_data, variables) => {
      setDirtyByPreset(prev => ({ ...prev, [variables.presetId]: false }))
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
    mutationFn: ({ ruleId, updates }: { ruleId: number; updates: Partial<AutomationRule>; presetId?: string }) =>
      apiClient.updateAutomationRule(ruleId, updates),
    onSuccess: (_data, variables) => {
      if (variables.presetId) {
        setDirtyByPreset(prev => ({ ...prev, [variables.presetId as string]: false }))
      }
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

  const buildTriggerConditions = (presetId: string): Record<string, unknown> => {
    const group = triggerIfByPreset[presetId]
    const out: Record<string, unknown> = { slug: presetId }
    if (!group?.conditions?.length) return out
    const conditions = group.conditions.map(c => {
      const row: Record<string, unknown> = { field: c.field, op: c.op }
      if (c.op === 'is_empty' || c.op === 'is_not_empty') return row
      if (typeof c.value === 'boolean') {
        row.value = c.value
        return row
      }
      if (typeof c.value === 'number' && !Number.isNaN(c.value)) {
        row.value = c.value
        return row
      }
      if (c.value === '' || c.value === null || c.value === undefined) {
        row.value = ''
        return row
      }
      const num = Number(c.value)
      if (['gt', 'gte', 'lt', 'lte'].includes(c.op) && !Number.isNaN(num)) {
        row.value = num
        return row
      }
      if (
        (c.field === 'lead_id' || c.field === 'score') &&
        (c.op === 'equals' || c.op === 'not_equals') &&
        !Number.isNaN(num) &&
        String(c.value).trim() !== ''
      ) {
        row.value = num
        return row
      }
      row.value = c.value
      return row
    })
    out.if = { match: 'all', conditions }
    return out
  }

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

      const trigger_conditions = buildTriggerConditions(preset.id)
      
      if (existing) {
        updateMutation.mutate({
          ruleId: existing.id,
          presetId: preset.id,
          updates: {
            status: 'active',
            action_parameters: actionParams,
            trigger_conditions,
          }
        })
      } else {
        createMutation.mutate({
          presetId: preset.id,
          rule: {
            name: preset.name,
            description: preset.description,
            trigger_type: preset.triggerType,
            trigger_conditions,
            action_type: preset.actionType,
            action_parameters: actionParams
          }
        })
      }
    } else if (existing) {
      updateMutation.mutate({
        ruleId: existing.id,
        presetId: preset.id,
        updates: { status: 'inactive' }
      })
    }
  }

  const handleConfigChange = (presetId: string, field: string, value: any) => {
    setDirtyByPreset(prev => ({ ...prev, [presetId]: true }))
    setConfigState(prev => ({
      ...prev,
      [presetId]: {
        ...prev[presetId],
        [field]: value
      }
    }))
  }

  const handleWebhookUrlChange = (presetId: string, url: string) => {
    setDirtyByPreset(prev => ({ ...prev, [presetId]: true }))
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
    setDirtyByPreset(prev => ({ ...prev, [presetId]: true }))
    setConfigState(prev => ({
      ...prev,
      [presetId]: {
        ...prev[presetId],
        payload: payload
      }
    }))
  }

  const renderField = (presetId: string, field: ConfigField, fieldId: string) => {
    const value = configState[presetId]?.[field.key] ?? ''
    if (field.type === 'select') {
      return (
        <select
          id={fieldId}
          name={field.key}
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
        id={fieldId}
        name={field.key}
        type={field.type === 'number' ? 'number' : 'text'}
        className="w-full rounded-lg border border-brand-text/20 px-3 py-2 bg-white dark:bg-gray-900"
        value={value}
        onChange={(e) => handleConfigChange(presetId, field.key, field.type === 'number' ? Number(e.target.value) : e.target.value)}
      />
    )
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-4 2xl:flex-row 2xl:items-start 2xl:justify-between">
        <div className="min-w-0">
          <p className="text-sm uppercase tracking-wide text-brand-text/60 dark:text-gray-400 break-words">Automation Studio</p>
          <h1 className="text-2xl font-bold text-brand-text dark:text-white mt-0.5 leading-tight break-words">Workflow Automations</h1>
          <p className="mt-1.5 text-sm text-brand-text/70 dark:text-gray-300 max-w-2xl break-words">
            Start with a guided setup for common outcomes, or use Automation studio for every preset, filters, and integrations.
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full 2xl:w-auto 2xl:max-w-[560px]">
          <div className="rounded-xl border border-brand-text/10 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-2.5 shadow-sm min-w-0">
            <div className="flex items-center gap-2.5 min-w-0">
              <Shield className="h-4 w-4 text-brand-primary flex-shrink-0" />
              <div className="min-w-0">
                <p className="text-xs uppercase tracking-wide text-brand-text/60 dark:text-gray-400 break-words">Safety</p>
                <p className="text-sm font-semibold text-brand-text dark:text-white break-words">
                  {safetyStatus?.automation_enabled ? 'Enabled' : 'Disabled'} · {safetyStatus?.safety_level ?? 'normal'}
                </p>
              </div>
            </div>
          </div>
          <div className="rounded-xl border border-brand-text/10 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-2.5 shadow-sm min-w-0">
            <div className="flex items-center gap-2.5">
              <BarChart3 className="h-4 w-4 text-brand-primary flex-shrink-0" />
              <div className="min-w-0">
                <p className="text-xs uppercase tracking-wide text-brand-text/60 dark:text-gray-400 break-words">Queue health</p>
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

      {!isLoading && (
        <section
          className="rounded-xl border border-brand-primary/25 bg-gradient-to-br from-brand-primary/[0.06] to-transparent dark:from-brand-primary/15 dark:border-brand-primary/30 p-5 shadow-sm"
          aria-labelledby="automations-get-started-heading"
        >
          <h2 id="automations-get-started-heading" className="text-sm font-semibold uppercase tracking-wide text-brand-text/70 dark:text-gray-300">
            Get started
          </h2>
          <p className="mt-1.5 text-sm text-brand-text/80 dark:text-gray-300 max-w-2xl">
            Guided setup walks through inbox connection, where leads go in CRM, and optional sender filters — then you go live
            on the same engine as the studio below.
          </p>
          <div className="mt-4 flex flex-col sm:flex-row flex-wrap gap-3">
            <Link
              to="/automations/setup/capture-leads-email"
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-brand-primary px-4 py-3 text-sm font-semibold text-white shadow-sm hover:opacity-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-2 dark:ring-offset-gray-900"
            >
              Capture leads from email
            </Link>
            <a
              href="#automation-studio"
              className="inline-flex items-center justify-center rounded-lg border border-brand-text/20 dark:border-gray-600 px-4 py-3 text-sm font-medium text-brand-text dark:text-gray-200 hover:bg-brand-text/5"
            >
              Automation studio (advanced)
            </a>
          </div>
        </section>
      )}

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
        <section id="automation-studio" className="space-y-3 scroll-mt-24">
          <div>
            <h2 className="text-lg font-semibold text-brand-text dark:text-white">Automation studio</h2>
            <p className="text-sm text-brand-text/65 dark:text-gray-400 mt-0.5">
              All workflow presets, trigger conditions (IF groups), and actions. For a step-by-step first workflow, use Get
              started above.
            </p>
          </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {automationPresets.map((preset) => {
            const Icon = preset.icon
            const rule = findRuleForPreset(rules, preset.id)
            const isActive = rule?.status === 'active'
            const capability = capabilitiesReady
              ? capabilityByAction[preset.actionType] ?? 'implemented'
              : 'unknown'
            const isStub = capability === 'stub'
            const isPartial = capability === 'partial'
            const isCapabilityUnknown = capability === 'unknown'
            const presetLogs = logsByPreset[preset.id] || []
            const lastLog = presetLogs[0]
            const statusKey = lastLog?.status || 'idle'
            const statusClass = statusBadgeClass[statusKey] || statusBadgeClass.idle
            const lastMessage = lastLog?.action_result?.message || lastLog?.error_message
            const isTesting = testPresetMutation.isPending && testPresetMutation.variables === preset.id
            return (
              <div key={preset.id} className="rounded-xl border border-brand-text/10 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 shadow-sm flex flex-col gap-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-2.5 min-w-0">
                    <div className="p-1.5 rounded-lg bg-brand-accent/20 flex-shrink-0">
                      <Icon className="h-4 w-4 text-brand-primary" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-base font-semibold text-brand-text dark:text-white leading-snug break-words">{preset.name}</h3>
                      <p className="text-xs text-brand-text/70 dark:text-gray-400 leading-snug break-words">{preset.description}</p>
                      {preset.honestyNote && (
                        <p className="text-[11px] text-brand-text/55 dark:text-gray-500 mt-1 leading-snug break-words">{preset.honestyNote}</p>
                      )}
                      {isCapabilityUnknown && (
                        <span className="inline-block mt-1 px-2 py-0.5 rounded text-xs font-medium bg-brand-text/10 text-brand-text/70 dark:text-gray-400 break-words">
                          Could not load capability status — refresh after signing in
                        </span>
                      )}
                      {isStub && capabilitiesReady && (
                        <span className="inline-block mt-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-500/15 text-amber-600 dark:text-amber-400 break-words">
                          Coming soon (engine returns 501 if executed)
                        </span>
                      )}
                      {isPartial && !isStub && capabilitiesReady && (
                        <span className="inline-block mt-1 px-2 py-0.5 rounded text-xs font-medium bg-blue-500/15 text-blue-600 dark:text-blue-400 break-words">
                          Partial · needs Slack / Twilio / templates where applicable
                        </span>
                      )}
                    </div>
                  </div>
                  <button
                    type="button"
                    aria-disabled={isStub && capabilitiesReady && !isActive}
                    title={
                      isStub && capabilitiesReady && !isActive
                        ? 'Cannot activate — this action is not implemented on the server yet'
                        : undefined
                    }
                    onClick={() => {
                      if (isStub && capabilitiesReady && !isActive) return
                      handleToggle(preset, !isActive)
                    }}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition shrink-0 ${
                      isActive ? 'bg-brand-primary' : 'bg-brand-text/30'
                    } ${isStub && capabilitiesReady && !isActive ? 'opacity-40 cursor-not-allowed' : ''}`}
                  >
                    <span className={`inline-block h-4 w-4 transform rounded-full bg-white dark:bg-gray-300 transition ${isActive ? 'translate-x-6' : 'translate-x-1'}`} />
                  </button>
                </div>

                {dirtyByPreset[preset.id] && (
                  <div className="flex items-center justify-between gap-2 rounded-lg border border-amber-500/35 bg-amber-500/10 dark:bg-amber-500/15 px-2.5 py-1.5">
                    <span className="text-xs font-medium text-amber-900 dark:text-amber-100">
                      Unsaved changes — use Save &amp; Activate to persist, or discard.
                    </span>
                    <button
                      type="button"
                      onClick={() => discardLocalChanges(preset)}
                      className="text-xs font-semibold text-amber-900 dark:text-amber-100 hover:underline flex-shrink-0"
                    >
                      Discard
                    </button>
                  </div>
                )}

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
                    {preset.configFields.map(field => {
                      const fieldId = `automation-${preset.id}-${field.key}`

                      return (
                        <div key={field.key}>
                          <label htmlFor={fieldId} className="text-xs font-medium text-brand-text dark:text-gray-200">{field.label}</label>
                          {renderField(preset.id, field, fieldId)}
                          {field.helper && <p className="text-xs text-brand-text/60 dark:text-gray-400 mt-0.5">{field.helper}</p>}
                        </div>
                      )
                    })}
                  </div>
                )}

                <TriggerIfGroup
                  triggerType={preset.triggerType}
                  value={triggerIfByPreset[preset.id] ?? { match: 'all', conditions: [] }}
                  onChange={next => {
                    setDirtyByPreset(prev => ({ ...prev, [preset.id]: true }))
                    setTriggerIfByPreset(prev => ({
                      ...prev,
                      [preset.id]: next,
                    }))
                  }}
                  metadata={triggerConditionMeta ?? null}
                />

                <div className="rounded-lg border border-brand-text/10 dark:border-gray-700 bg-brand-accent/5 dark:bg-gray-900 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-xs uppercase tracking-wide text-brand-text/50 dark:text-gray-400">Last run</p>
                      <p className="text-xs font-medium text-brand-text dark:text-white break-words">{formatAbsoluteTimestamp(lastLog?.executed_at)}</p>
                      <p className="text-xs text-brand-text/60 dark:text-gray-400 break-words" title={lastMessage || undefined}>
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
                        <div key={log.execution_id} className="flex items-center justify-between gap-2">
                          <span className="truncate min-w-0">{log.action_result?.summary || log.action_result?.message || log.status}</span>
                          <span>{formatRelativeTimestamp(log.executed_at)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between border-t border-brand-text/10 dark:border-gray-700 pt-3 gap-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <button
                      type="button"
                      onClick={() => handleTestPreset(preset.id)}
                      disabled={isTesting || (isStub && capabilitiesReady)}
                      className={`text-xs font-medium inline-flex items-center gap-1.5 ${
                        isTesting || (isStub && capabilitiesReady)
                          ? 'text-brand-text/50 dark:text-gray-500 cursor-not-allowed'
                          : 'text-brand-primary hover:text-brand-secondary'
                      }`}
                      title={
                        isStub && capabilitiesReady
                          ? 'Not available — action is stub on the server'
                          : isPartial && preset.actionType === 'send_notification'
                            ? 'Requires slack_webhook_url on the rule or SLACK_WEBHOOK_URL in the environment'
                            : undefined
                      }
                    >
                      <PlayCircle className="h-3.5 w-3.5" />
                      {isTesting ? 'Testing…' : 'Run Test'}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleToggle(preset, true)}
                      disabled={isStub && capabilitiesReady}
                      className={`text-xs font-medium inline-flex items-center gap-1.5 ${
                        isStub && capabilitiesReady
                          ? 'text-brand-text/40 cursor-not-allowed'
                          : 'text-brand-primary hover:text-brand-secondary'
                      }`}
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
        </section>
      )}

      <div className="rounded-xl border border-brand-text/10 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 shadow-sm">
        <div className="flex items-center justify-between mb-3 gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <History className="h-4 w-4 text-brand-primary" />
            <div className="min-w-0">
              <p className="text-xs uppercase tracking-wide text-brand-text/60 dark:text-gray-400 break-words">Automation activity</p>
              <h2 className="text-lg font-semibold text-brand-text dark:text-white break-words">Recent executions</h2>
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
                      <p className="text-xs font-semibold text-brand-text dark:text-white break-words">{log.rule_name}</p>
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
          <div className="flex items-center gap-2.5 mb-3 min-w-0">
            <GitBranch className="h-4 w-4 text-brand-primary" />
            <div className="min-w-0">
              <p className="text-xs uppercase tracking-wide text-brand-text/60 dark:text-gray-400 break-words">AI recommendations</p>
              <h2 className="text-lg font-semibold text-brand-text dark:text-white break-words">Suggested automations</h2>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {suggestions.map((suggestion: any, idx: number) => (
              <div key={idx} className="rounded-lg border border-brand-text/10 dark:border-gray-700 p-3 text-sm text-brand-text/80 dark:text-gray-300">
                <p className="font-semibold text-brand-text dark:text-white text-sm break-words">{suggestion.title || suggestion.name || 'Automation suggestion'}</p>
                <p className="mt-0.5 text-xs break-words">{suggestion.description || suggestion.reason || 'Optimize this workflow for better response times.'}</p>
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
