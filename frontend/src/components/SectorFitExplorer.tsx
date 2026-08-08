import React, { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import type { LucideIcon } from 'lucide-react'
import { Mail, Sparkles, Users, X } from 'lucide-react'
import {
  analyzeSectorInput,
  combineSectorQueries,
  MAX_RAW_INPUT_CHARS,
  type FeatureFitId,
  type SectorFitPresentationStatus,
} from '../lib/aboutSectorMatch'
import {
  buildSectorExplorerResultPayload,
  trackSectorExplorerCta,
  trackSectorExplorerResult,
  trackSectorExplorerStarted,
} from '../lib/sectorFitAnalytics'
import { cn } from '../lib/utils'

/** One-tap probes across different sector templates—click applies instantly */
const EXAMPLE_BUSINESS_HINTS = [
  'Landscaping and seasonal cleanup',
  'Neighborhood bakery / café',
  'Family dental clinic',
  'MSP / managed IT for SMBs',
  'Staffing agency for healthcare hires',
  'Commercial janitorial contractor',
  'Independent insurance brokerage',
  'Fitness studio memberships',
]

/** Universal follow-up prompts (one useful detail at a time) */
const FOLLOW_UP_CONTEXT_HINTS = [
  'What we sell or provide',
  'Who our customers are',
  'Appointment-based / recurring work',
  'Field crews / on-site jobs',
  'Customers visit us or contact by email',
]

const FEATURE_ICONS: Record<FeatureFitId, LucideIcon> = {
  email_automation: Mail,
  crm_management: Users,
  ai_assistant: Sparkles,
}

function strengthLabel(strength: 'high' | 'medium' | null | undefined): string | null {
  if (strength === 'high') return 'Strong match'
  if (strength === 'medium') return 'Possible match'
  return null
}

function shouldShowFollowUp(status: SectorFitPresentationStatus): boolean {
  return status === 'needs_detail' || status === 'ambiguous'
}

function shouldShowFeatures(status: SectorFitPresentationStatus): boolean {
  return status === 'matched'
}

export function SectorFitExplorer() {
  const [query, setQuery] = useState('')
  const [additionalContext, setAdditionalContext] = useState('')
  const [announcedKey, setAnnouncedKey] = useState('')
  const textareaId = useId()
  const followUpId = useId()
  const resultsId = useId()
  const announceId = useId()
  const charCountId = useId()
  const announceTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const cappedQuery = query.length > MAX_RAW_INPUT_CHARS ? query.slice(0, MAX_RAW_INPUT_CHARS) : query
  const trimmedQuery = cappedQuery.trim()
  const trimmedAdditional = additionalContext.trim()
  const combinedQuery = useMemo(
    () => combineSectorQueries(trimmedQuery, trimmedAdditional),
    [trimmedQuery, trimmedAdditional]
  )
  const analysis = useMemo(() => analyzeSectorInput(combinedQuery), [combinedQuery])
  const fit = analysis.presentation
  const status = fit.status
  const showFollowUp = shouldShowFollowUp(status)
  const showFeatureList = shouldShowFeatures(status)
  const nearLimit = cappedQuery.length >= MAX_RAW_INPUT_CHARS - 40

  const syncQuery = useCallback((value: string) => {
    const next = value.length > MAX_RAW_INPUT_CHARS ? value.slice(0, MAX_RAW_INPUT_CHARS) : value
    setQuery(next)
    if (!next.trim()) {
      setAdditionalContext('')
    }
  }, [])

  const clearQuery = useCallback(() => {
    setQuery('')
    setAdditionalContext('')
  }, [])

  const appendFollowUp = useCallback((snippet: string) => {
    setAdditionalContext((prev) => {
      const next = prev.trim()
      if (!next) return snippet
      if (next.includes(snippet)) return prev
      return `${next} ${snippet}`
    })
  }, [])

  // Announce meaningful result changes (not every keystroke)
  useEffect(() => {
    const key = `${status}:${fit.sectorId ?? ''}:${fit.reasonCode ?? ''}:${trimmedAdditional ? '1' : '0'}`
    if (key === announcedKey) return
    if (status === 'idle') {
      setAnnouncedKey(key)
      return
    }
    if (announceTimer.current) clearTimeout(announceTimer.current)
    announceTimer.current = setTimeout(() => {
      setAnnouncedKey(key)
      trackSectorExplorerResult(
        buildSectorExplorerResultPayload({
          status,
          reasonCode: fit.reasonCode,
          sectorId: fit.sectorId,
          matchStrength: fit.matchStrength,
          inputLength: combinedQuery.length,
          usedFollowUp: trimmedAdditional.length > 0,
        })
      )
    }, 400)
    return () => {
      if (announceTimer.current) clearTimeout(announceTimer.current)
    }
  }, [
    status,
    fit.sectorId,
    fit.reasonCode,
    fit.matchStrength,
    announcedKey,
    trimmedAdditional,
    combinedQuery.length,
  ])

  useEffect(() => {
    trackSectorExplorerStarted()
  }, [])

  const liveAnnouncement =
    announcedKey && status !== 'idle' ? `${fit.headline}. ${fit.summary}` : ''

  const matchBadge = strengthLabel(fit.matchStrength)

  return (
    <div className="rounded-2xl border border-border/80 bg-card/85 backdrop-blur-sm shadow-lg shadow-stone-900/5 overflow-hidden relative max-w-full">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-orange-500/[0.07] via-transparent to-sky-500/[0.06]" />
      <div className="relative grid grid-cols-1 lg:grid-cols-12 gap-0 lg:divide-x lg:divide-border/60">
        <div className="lg:col-span-5 p-5 sm:p-8 flex flex-col gap-5 border-b lg:border-b-0 border-border/60 pb-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">Step 1</p>
            <label htmlFor={textareaId} className="text-base font-semibold text-foreground block mb-2">
              Tell us what your business does
            </label>
            <p id={`${textareaId}-hint`} className="text-sm text-muted-foreground mb-3 leading-relaxed">
              Use plain language: what you sell, who you serve, and how leads usually come in (e.g. emergency
              plumbing, med-spa consultations).
            </p>
            <div className="relative">
              <textarea
                id={textareaId}
                name="business_description"
                aria-describedby={`${textareaId}-hint${nearLimit ? ` ${charCountId}` : ''}${showFollowUp ? ` ${followUpId}-hint` : ''}`}
                rows={5}
                value={cappedQuery}
                maxLength={MAX_RAW_INPUT_CHARS}
                onChange={(e) => syncQuery(e.target.value)}
                onInput={(e) => syncQuery(e.currentTarget.value)}
                placeholder="e.g. we run a small HVAC company…"
                autoComplete="off"
                enterKeyHint="done"
                className={cn(
                  // text-base below sm prevents iOS zoom-on-focus when font size would be under 16px
                  'w-full max-w-full resize-y rounded-xl border border-border bg-background/80 px-4 py-3 pr-11 text-base leading-relaxed sm:text-sm',
                  'placeholder:text-muted-foreground/70 touch-manipulation',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/70 focus-visible:ring-offset-2 focus-visible:ring-offset-background'
                )}
                spellCheck
              />
              {cappedQuery.length > 0 ? (
                <button
                  type="button"
                  onClick={clearQuery}
                  aria-label="Clear business description"
                  className={cn(
                    'absolute top-2.5 right-2.5 inline-flex h-9 w-9 items-center justify-center rounded-lg',
                    'text-muted-foreground hover:text-foreground hover:bg-muted/80 touch-manipulation',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/70'
                  )}
                >
                  <X className="h-4 w-4" aria-hidden />
                </button>
              ) : null}
            </div>
            {nearLimit ? (
              <p id={charCountId} className="mt-2 text-xs text-muted-foreground text-right">
                {cappedQuery.length}/{MAX_RAW_INPUT_CHARS}
              </p>
            ) : null}
            <div className="flex flex-wrap gap-2 mt-4">
              <span className="text-xs text-muted-foreground w-full pt-1 sm:inline sm:w-auto sm:mr-1 sm:pt-0">Examples:</span>
              {EXAMPLE_BUSINESS_HINTS.map((hint) => (
                <button
                  key={hint}
                  type="button"
                  aria-label={`Use example: ${hint}`}
                  onClick={() => {
                    syncQuery(hint)
                    setAdditionalContext('')
                  }}
                  className={cn(
                    'text-xs font-medium px-4 py-2.5 sm:py-1.5 sm:px-3 rounded-full text-left',
                    'min-h-11 sm:min-h-0 bg-muted/70 hover:bg-muted active:bg-muted/90 text-foreground border border-border/80 transition-colors touch-manipulation',
                    '[-webkit-tap-highlight-color:transparent]'
                  )}
                >
                  <span className="break-words">{hint}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="lg:col-span-7 p-5 sm:p-8 flex flex-col min-h-[240px] sm:min-h-[280px]">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">Step 2</p>
          <h3 className="text-lg font-semibold text-foreground mb-3">How Fikiri can help</h3>
          <div
            id={resultsId}
            className={cn(
              'flex-1 rounded-xl border border-border/70 bg-background/55 px-4 py-5 sm:px-5 sm:py-6 max-w-full min-w-0',
              status === 'matched' && fit.matchStrength === 'high' && 'ring-2 ring-orange-500/35',
              status === 'matched' && fit.matchStrength === 'medium' && 'ring-1 ring-amber-500/35',
              status === 'ambiguous' && 'ring-1 ring-amber-500/35',
              status === 'invalid' && 'ring-1 ring-border'
            )}
          >
            {/* Debounced polite announcement for status changes */}
            <div id={announceId} className="sr-only" aria-live="polite" aria-atomic="true">
              {liveAnnouncement}
            </div>

            {fit.category && status === 'matched' ? (
              <p className="text-xs font-semibold uppercase tracking-wide text-orange-600 dark:text-orange-400 mb-1">
                {fit.category}
              </p>
            ) : null}

            <div className="flex flex-wrap items-center gap-2 mb-2">
              <p className="text-sm font-semibold text-foreground break-words hyphens-none">{fit.headline}</p>
              {matchBadge ? (
                <span className="text-[11px] font-medium uppercase tracking-wide rounded-full px-2 py-0.5 bg-orange-500/10 text-orange-700 dark:text-orange-300 ring-1 ring-orange-500/20">
                  {matchBadge}
                </span>
              ) : null}
            </div>

            {fit.ambiguousAlternates && fit.ambiguousAlternates.length > 0 ? (
              <p className="text-xs text-muted-foreground mb-3 leading-relaxed">
                Close matches: {fit.ambiguousAlternates.map((a) => a.displayName).join(' · ')}
              </p>
            ) : null}

            {showFollowUp ? (
              <div
                className="rounded-xl border border-amber-500/35 bg-amber-500/[0.06] px-4 py-4 sm:px-5 sm:py-5 mb-6"
                aria-labelledby={`${followUpId}-label`}
              >
                <p id={`${followUpId}-label`} className="text-sm font-semibold text-foreground mb-1">
                  {status === 'ambiguous' ? 'Which sounds closest?' : 'Tell us a bit more'}
                </p>
                <p id={`${followUpId}-hint`} className="text-xs text-muted-foreground mb-3 leading-relaxed">
                  {fit.summary}
                </p>
                <textarea
                  id={followUpId}
                  name="business_sector_detail"
                  aria-describedby={`${followUpId}-hint`}
                  rows={3}
                  value={additionalContext}
                  maxLength={MAX_RAW_INPUT_CHARS}
                  onChange={(e) => setAdditionalContext(e.target.value.slice(0, MAX_RAW_INPUT_CHARS))}
                  onInput={(e) => setAdditionalContext(e.currentTarget.value.slice(0, MAX_RAW_INPUT_CHARS))}
                  placeholder="e.g. commercial HVAC — emergency calls and quote requests by email"
                  autoComplete="off"
                  className={cn(
                    'w-full max-w-full resize-y rounded-lg border border-border bg-background/90 px-3 py-2.5 text-base sm:text-sm leading-relaxed',
                    'placeholder:text-muted-foreground/70 touch-manipulation',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500/60 focus-visible:ring-offset-2 focus-visible:ring-offset-background'
                  )}
                  spellCheck
                />
                <div className="flex flex-wrap gap-2 mt-3">
                  <span className="text-xs text-muted-foreground w-full sm:inline sm:w-auto sm:mr-1">Try adding:</span>
                  {FOLLOW_UP_CONTEXT_HINTS.map((hint) => (
                    <button
                      key={hint}
                      type="button"
                      aria-label={`Add context: ${hint}`}
                      onClick={() => appendFollowUp(hint)}
                      className={cn(
                        'text-xs font-medium px-3 py-2 sm:py-1.5 rounded-full text-left',
                        'min-h-10 sm:min-h-0 bg-background/80 hover:bg-muted border border-border/80 transition-colors touch-manipulation',
                        '[-webkit-tap-highlight-color:transparent]'
                      )}
                    >
                      <span className="break-words">{hint}</span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground leading-relaxed mb-6 break-words">{fit.summary}</p>
            )}

            {showFeatureList && (
              <ul className="space-y-5">
                {fit.featuresOrdered.map((row) => {
                  const Icon = FEATURE_ICONS[row.id]
                  return (
                    <li key={row.id} className="flex gap-3 min-w-0">
                      <span className="mt-0.5 flex h-10 w-10 sm:h-9 sm:w-9 shrink-0 items-center justify-center rounded-lg bg-orange-500/10 ring-1 ring-orange-500/20">
                        <Icon className="h-5 w-5 text-orange-600 dark:text-orange-400" aria-hidden />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-foreground break-words">{row.title}</p>
                        <p className="text-sm text-muted-foreground mt-1 leading-relaxed break-words">{row.fit}</p>
                      </div>
                    </li>
                  )
                })}
              </ul>
            )}
            <div className="mt-8 pt-5 border-t border-border/70">
              <p className="text-sm text-muted-foreground mb-3">
                Want a tailored game plan for your exact workflow? Speak with our team and get practical next steps.
              </p>
              <Link
                to="/contact"
                onClick={() => trackSectorExplorerCta('contact')}
                className={cn(
                  'inline-flex min-h-11 min-w-[44px] items-center text-sm font-semibold text-orange-600 hover:text-orange-500',
                  'dark:text-orange-400 dark:hover:text-orange-300 underline underline-offset-2 py-2 -my-2 sm:min-h-0 sm:py-0 sm:my-0 touch-manipulation',
                  '[-webkit-tap-highlight-color:transparent]'
                )}
              >
                Talk to us
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

type SectorFitSectionProps = {
  /** Optional heading id for aria-labelledby */
  headingId?: string
  className?: string
  /** Dark hero shell: light copy on charcoal, explorer stays as a readable product card */
  tone?: 'default' | 'onDark'
}

/** Intro copy + interactive explorer used on the home landing hero. */
export function SectorFitSection({ headingId, className, tone = 'default' }: SectorFitSectionProps) {
  const fallbackId = useId()
  const titleId = headingId ?? fallbackId
  const onDark = tone === 'onDark'

  return (
    <section aria-labelledby={titleId} className={cn('overflow-x-hidden text-left', className)}>
      <p
        className={cn(
          'mb-3 text-center text-[11px] font-semibold uppercase tracking-[0.18em]',
          onDark ? 'text-orange-300' : 'text-muted-foreground'
        )}
      >
        Consulting-first workflow systems
      </p>
      <h1
        id={titleId}
        className={cn(
          'mb-3 text-center font-serif text-2xl font-semibold leading-tight break-words sm:text-3xl md:text-4xl',
          onDark ? 'text-white' : 'text-foreground'
        )}
      >
        See how Fikiri fits your sector
      </h1>
      <p
        className={cn(
          'mx-auto mb-2 max-w-3xl text-center text-sm leading-relaxed break-words sm:text-base',
          onDark ? 'text-white/85' : 'text-muted-foreground'
        )}
      >
        We start with workflow discovery, then build practical systems around each business. Describe your
        sector below to map Email Automation, CRM Management, and AI Assistant workflows that typically fit
        teams like yours.
      </p>
      <p
        className={cn(
          'mx-auto mb-5 max-w-2xl text-center text-xs leading-relaxed sm:mb-6',
          onDark ? 'text-white/75' : 'text-muted-foreground'
        )}
      >
        This is a fast directional guide, not formal consulting. We can validate the recommendations with your
        team in a short call.
      </p>
      <div
        className={cn(
          onDark &&
            'rounded-2xl bg-white/95 p-1 shadow-2xl shadow-black/40 ring-1 ring-white/10 dark:bg-gray-950/90'
        )}
      >
        <SectorFitExplorer />
      </div>
    </section>
  )
}
