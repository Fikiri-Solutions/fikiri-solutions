import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Loader2,
  Mail,
  PlayCircle,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'
import { apiClient, AutomationRule } from '../services/apiClient'
import { useToast } from '../components/Toast'
import {
  buildInboundCrmSyncActionParameters,
  buildInboundCrmSyncTriggerConditions,
  INBOUND_CRM_SYNC_PRESET_ID,
  isInboundCrmSyncSlug,
} from '../lib/automationInboundCrmPayload'

const PIPELINE_STAGES = [
  { value: 'new', label: 'New' },
  { value: 'contacted', label: 'Contacted' },
  { value: 'qualified', label: 'Qualified' },
  { value: 'booked', label: 'Booked' },
] as const

const STEP_COUNT = 5

function findInboundCrmSyncRule(rules: AutomationRule[]): AutomationRule | undefined {
  return rules.find(
    r =>
      isInboundCrmSyncSlug(r.action_parameters?.slug) ||
      r.name === 'Gmail → CRM' ||
      r.name === 'Inbound email → CRM'
  )
}

export const AutomationSetupCaptureLeadsEmail: React.FC = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { addToast } = useToast()
  const [step, setStep] = useState(1)
  const [targetStage, setTargetStage] = useState<string>('new')
  const [senderFilter, setSenderFilter] = useState('')
  const [savedLive, setSavedLive] = useState(false)

  const { data: rules = [], isLoading: rulesLoading } = useQuery({
    queryKey: ['automation-rules'],
    queryFn: () => apiClient.getAutomationRules(),
  })

  const { data: gmailStatus, isFetching: gmailLoading } = useQuery({
    queryKey: ['gmail-connection-status'],
    queryFn: () => apiClient.getGmailConnectionStatus(),
    staleTime: 30 * 1000,
  })

  const { data: outlookStatus, isFetching: outlookLoading } = useQuery({
    queryKey: ['outlook-connection-status'],
    queryFn: () => apiClient.getOutlookConnectionStatus(),
    staleTime: 30 * 1000,
  })

  const inboxReady = Boolean(gmailStatus?.connected || outlookStatus?.connected)
  const loadingPrereqs = gmailLoading || outlookLoading

  const existingRule = useMemo(() => findInboundCrmSyncRule(rules), [rules])

  useEffect(() => {
    if (!existingRule || rulesLoading) return
    const params = existingRule.action_parameters || {}
    if (params.target_stage) setTargetStage(String(params.target_stage))
    const tc = existingRule.trigger_conditions as Record<string, unknown> | undefined
    const conds = (tc?.if as { conditions?: { field?: string; op?: string; value?: string }[] })?.conditions
    const ends = conds?.find(c => c.field === 'sender_email' && c.op === 'ends_with')
    if (ends?.value) setSenderFilter(String(ends.value))
  }, [existingRule, rulesLoading])

  useEffect(() => {
    if (rulesLoading) return
    if (existingRule?.status === 'active') {
      setSavedLive(true)
      setStep(5)
    }
  }, [rulesLoading, existingRule])

  const saveMutation = useMutation({
    mutationFn: async () => {
      const opts = { targetStage, senderEmailEndsWith: senderFilter.trim() || undefined }
      const trigger_conditions = buildInboundCrmSyncTriggerConditions(opts)
      const action_parameters = buildInboundCrmSyncActionParameters(opts)
      if (existingRule) {
        return apiClient.updateAutomationRule(existingRule.id, {
          status: 'active',
          trigger_conditions: trigger_conditions as Record<string, any>,
          action_parameters: action_parameters as Record<string, any>,
        })
      }
      return apiClient.createAutomationRule({
        name: 'Inbound email → CRM',
        description: 'Convert new inbound emails into CRM leads automatically.',
        trigger_type: 'email_received',
        trigger_conditions: trigger_conditions as Record<string, any>,
        action_type: 'update_crm_field',
        action_parameters: action_parameters as Record<string, any>,
      })
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['automation-rules'] })
      setSavedLive(true)
      addToast({ type: 'success', title: 'Automation is on', message: 'New inbound mail can create or update CRM leads.' })
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.message || err?.response?.data?.error || err?.message || 'Save failed'
      addToast({ type: 'error', title: 'Could not save', message: msg })
    },
  })

  const testMutation = useMutation({
    mutationFn: () => apiClient.runAutomationPreset(INBOUND_CRM_SYNC_PRESET_ID),
    onSuccess: () => {
      addToast({ type: 'success', title: 'Sample test run', message: 'Check the Automations page for execution logs.' })
    },
    onError: (err: any) => {
      const status = err?.response?.status
      const msg = err?.response?.data?.error || err?.response?.data?.message || err?.message || 'Test failed'
      addToast({
        type: 'error',
        title: status === 501 ? 'Action needs configuration' : 'Test failed',
        message: msg,
      })
    },
  })

  const canGoNext = (): boolean => {
    if (step === 1) return inboxReady
    if (step === 2) return Boolean(targetStage)
    return true
  }

  const goNext = () => {
    if (!canGoNext()) return
    setStep(s => Math.min(STEP_COUNT, s + 1))
  }

  const goBack = () => setStep(s => Math.max(1, s - 1))

  const summaryLines = useMemo(() => {
    const opts = { targetStage, senderEmailEndsWith: senderFilter.trim() || undefined }
    const lines: string[] = []
    lines.push(
      inboxReady
        ? 'Inbox connected (Gmail and/or Outlook sync can feed this automation).'
        : 'Connect an inbox before turning this on.'
    )
    lines.push(`New leads land in pipeline stage: ${PIPELINE_STAGES.find(s => s.value === targetStage)?.label ?? targetStage}.`)
    if (senderFilter.trim()) {
      lines.push(`Only when the sender address ends with: ${senderFilter.trim()}`)
    } else {
      lines.push('Applies to inbound mail from any sender (no extra filter).')
    }
    lines.push('When mail arrives, Fikiri creates or updates a lead in your CRM from the sender.')
    return lines
  }, [inboxReady, targetStage, senderFilter])

  return (
    <div className="max-w-2xl mx-auto space-y-6 pb-12">
      <div className="flex items-start gap-3">
        <button
          type="button"
          onClick={() => navigate('/automations')}
          className="mt-0.5 p-1.5 rounded-lg border border-brand-text/15 text-brand-text/70 hover:bg-brand-text/5 dark:border-gray-600 dark:text-gray-300"
          aria-label="Back to Automations"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>
        <div>
          <p className="text-xs uppercase tracking-wide text-brand-text/60 dark:text-gray-400">Guided setup</p>
          <h1 className="text-2xl font-bold text-brand-text dark:text-white mt-0.5">Capture leads from email</h1>
          <p className="mt-1 text-sm text-brand-text/70 dark:text-gray-300">
            Turn inbound messages into CRM leads. This uses the same automation engine as Advanced Studio — no separate setup path.
          </p>
        </div>
      </div>

      <ol className="flex flex-wrap gap-2 text-xs" aria-label="Setup steps">
        {['Inbox', 'Stage', 'Filter', 'Review', 'Go live'].map((label, i) => (
          <li
            key={label}
            className={`rounded-full px-2.5 py-1 font-medium ${
              i + 1 === step
                ? 'bg-brand-primary text-white'
                : i + 1 < step
                  ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'
                  : 'bg-brand-text/10 text-brand-text/60 dark:text-gray-500'
            }`}
          >
            {i + 1}. {label}
          </li>
        ))}
      </ol>

      <div className="rounded-xl border border-brand-text/10 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 shadow-sm min-h-[220px]">
        {step === 1 && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-brand-primary">
              <Mail className="h-5 w-5" />
              <h2 className="text-lg font-semibold text-brand-text dark:text-white">Connect your inbox</h2>
            </div>
            <p className="text-sm text-brand-text/70 dark:text-gray-300">
              Fikiri watches synced mail to run this automation. Connect Gmail or Microsoft Outlook (at least one).
            </p>
            {loadingPrereqs ? (
              <div className="flex items-center gap-2 text-sm text-brand-text/60">
                <Loader2 className="h-4 w-4 animate-spin" /> Checking connections…
              </div>
            ) : (
              <ul className="space-y-2 text-sm">
                <li className="flex items-center justify-between gap-2 rounded-lg border border-brand-text/10 px-3 py-2 dark:border-gray-600">
                  <span>Gmail</span>
                  {gmailStatus?.connected ? (
                    <span className="text-emerald-600 dark:text-emerald-400 font-medium">Connected</span>
                  ) : (
                    <Link to="/integrations/gmail" className="text-brand-primary font-medium hover:underline">
                      Connect
                    </Link>
                  )}
                </li>
                <li className="flex items-center justify-between gap-2 rounded-lg border border-brand-text/10 px-3 py-2 dark:border-gray-600">
                  <span>Outlook</span>
                  {outlookStatus?.connected ? (
                    <span className="text-emerald-600 dark:text-emerald-400 font-medium">Connected</span>
                  ) : (
                    <Link to="/integrations/outlook" className="text-brand-primary font-medium hover:underline">
                      Connect
                    </Link>
                  )}
                </li>
              </ul>
            )}
            {!loadingPrereqs && !inboxReady && (
              <p className="text-sm text-amber-700 dark:text-amber-300 rounded-lg bg-amber-500/10 px-3 py-2">
                Connect at least one inbox to continue. You can return here after authorizing in Integrations.
              </p>
            )}
            {inboxReady && (
              <p className="text-sm text-emerald-700 dark:text-emerald-300 flex items-center gap-1.5">
                <ShieldCheck className="h-4 w-4 flex-shrink-0" /> Ready to sync inbound mail for automations.
              </p>
            )}
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-brand-text dark:text-white">Where should new leads go?</h2>
            <p className="text-sm text-brand-text/70 dark:text-gray-300">
              Choose the CRM pipeline stage for leads created or updated from inbound email.
            </p>
            <label htmlFor="capture-leads-target-stage" className="block text-xs font-medium text-brand-text/80 dark:text-gray-300">Pipeline stage</label>
            <select
              id="capture-leads-target-stage"
              name="target_stage"
              className="w-full max-w-md rounded-lg border border-brand-text/20 px-3 py-2 bg-white dark:bg-gray-900 text-brand-text dark:text-white"
              value={targetStage}
              onChange={e => setTargetStage(e.target.value)}
            >
              {PIPELINE_STAGES.map(s => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-brand-text dark:text-white">Optional: limit senders</h2>
            <p className="text-sm text-brand-text/70 dark:text-gray-300">
              Leave blank to capture leads from anyone. To only react when the sender address ends with a specific domain or
              suffix (for example <code className="text-xs">@yourclient.com</code>), enter it below.
            </p>
            <label htmlFor="capture-leads-sender-filter" className="block text-xs font-medium text-brand-text/80 dark:text-gray-300">Sender address ends with</label>
            <input
              id="capture-leads-sender-filter"
              name="sender_email_ends_with"
              type="text"
              className="w-full max-w-md rounded-lg border border-brand-text/20 px-3 py-2 bg-white dark:bg-gray-900"
              placeholder="e.g. @acme.com or acme.com"
              value={senderFilter}
              onChange={e => setSenderFilter(e.target.value)}
            />
          </div>
        )}

        {step === 4 && (
          <div className="space-y-3">
            <h2 className="text-lg font-semibold text-brand-text dark:text-white">Review</h2>
            <ul className="list-disc pl-5 space-y-1.5 text-sm text-brand-text/80 dark:text-gray-300">
              {summaryLines.map((line, idx) => (
                <li key={idx}>{line}</li>
              ))}
            </ul>
          </div>
        )}

        {step === 5 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-brand-text dark:text-white flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-brand-primary" />
              Go live
            </h2>
            {!savedLive ? (
              <>
                <p className="text-sm text-brand-text/70 dark:text-gray-300">
                  Save turns this automation on. After that, new synced mail can create or update CRM leads per your review
                  above.
                </p>
                <button
                  type="button"
                  disabled={!inboxReady || saveMutation.isPending}
                  onClick={() => saveMutation.mutate()}
                  className="inline-flex items-center gap-2 rounded-lg bg-brand-primary px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
                >
                  {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                  Turn on automation
                </button>
                {!inboxReady && (
                  <p className="text-xs text-amber-700 dark:text-amber-300">Connect an inbox in step 1 first.</p>
                )}
              </>
            ) : (
              <div className="space-y-4">
                <div className="flex items-start gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2.5 text-sm text-emerald-900 dark:text-emerald-100">
                  <CheckCircle2 className="h-5 w-5 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-semibold">You are live</p>
                    <p className="mt-0.5 text-emerald-800/90 dark:text-emerald-200/90">
                      This rule is active. After mail sync runs, matching messages will update your CRM.
                    </p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => testMutation.mutate()}
                    disabled={testMutation.isPending}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-brand-text/20 px-3 py-2 text-sm font-medium text-brand-primary hover:bg-brand-text/5"
                  >
                    {testMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <PlayCircle className="h-4 w-4" />}
                    Run sample test
                  </button>
                  <Link
                    to="/automations#automation-studio"
                    className="inline-flex items-center gap-1.5 rounded-lg border border-brand-text/20 px-3 py-2 text-sm font-medium text-brand-text dark:text-gray-200 hover:bg-brand-text/5"
                  >
                    Open advanced studio
                  </Link>
                </div>
                <p className="text-xs text-brand-text/60 dark:text-gray-400">
                  Sample test runs the backend preset test for this workflow (requires this automation to be active).
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={goBack}
          disabled={step <= 1}
          className="inline-flex items-center gap-1 text-sm font-medium text-brand-text/70 hover:text-brand-text disabled:opacity-40"
        >
          <ArrowLeft className="h-4 w-4" /> Back
        </button>
        {step < STEP_COUNT ? (
          <button
            type="button"
            onClick={goNext}
            disabled={!canGoNext()}
            className="inline-flex items-center gap-1 rounded-lg bg-brand-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            Next <ArrowRight className="h-4 w-4" />
          </button>
        ) : null}
      </div>

      <p className="text-xs text-brand-text/50 dark:text-gray-500">
        CRM data is stored in Fikiri. For more workflows and technical filters, use{' '}
        <Link to="/automations#automation-studio" className="text-brand-primary hover:underline">
          Automation studio
        </Link>
        .
      </p>
    </div>
  )
}
