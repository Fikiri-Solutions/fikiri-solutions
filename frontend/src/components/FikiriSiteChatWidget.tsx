import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Copy, Loader2, Send, Sparkles, X } from 'lucide-react'
import { cn } from '../lib/utils'
import FikiriLogo from './FikiriLogo'
import {
  handoffPath,
  sendSiteChatMessage,
  startSiteChatSession,
  type SiteChatMessageData,
} from '../services/siteChatApi'
import {
  copyTextToClipboard,
  formatSiteChatTranscript,
  isSiteChatDevToolsEnabled,
} from '../utils/siteChatDevTools'

type ChatRole = 'assistant' | 'user'

interface ChatLine {
  id: string
  role: ChatRole
  text: string
  grounded?: boolean
  sources?: SiteChatMessageData['sources']
}

const QUICK_PROMPTS = [
  { label: 'Pricing', message: 'What does Fikiri cost?' },
  { label: 'Fit check', message: 'Is Fikiri a fit for my business?' },
  { label: 'Workflow audit', message: "I'd like a workflow audit" },
  { label: 'Talk to team', message: 'I want to talk with your team' },
] as const

let lineCounter = 0
function nextLineId(): string {
  lineCounter += 1
  return `line_${lineCounter}`
}

function handoffLabel(handoffType: string | null | undefined): string {
  if (handoffType === 'contact') return 'Contact us'
  if (handoffType === 'intake') return 'Start workflow intake'
  return 'Continue'
}

function sourceLabel(url?: string): string {
  if (!url) return 'Fikiri knowledge base'
  try {
    const host = new URL(url).hostname.replace(/^www\./, '')
    return host
  } catch {
    return 'fikirisolutions.com'
  }
}

export const FikiriSiteChatWidget: React.FC = () => {
  const [open, setOpen] = useState(false)
  const [lines, setLines] = useState<ChatLine[]>([])
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastReply, setLastReply] = useState<SiteChatMessageData | null>(null)
  const sessionIdRef = useRef<string | null>(null)
  const bootstrappedRef = useRef(false)
  const scrollAnchorRef = useRef<HTMLDivElement | null>(null)
  const inputRef = useRef<HTMLInputElement | null>(null)
  const devTools = useMemo(() => isSiteChatDevToolsEnabled(), [])
  const [copyState, setCopyState] = useState<'idle' | 'copied'>('idle')

  const intake = lastReply?.intake
  const intakeActive = Boolean(intake?.active)
  const intakeFilled = intake?.filled_core_count ?? 0
  const intakeComplete = Boolean(intake?.complete)

  const showQuickPrompts = useMemo(() => {
    if (loading || error || lines.length === 0) return false
    const userTurns = lines.filter((line) => line.role === 'user').length
    return userTurns === 0
  }, [error, lines, loading])

  const appendLine = useCallback((line: Omit<ChatLine, 'id'>) => {
    setLines((prev) => [...prev, { ...line, id: nextLineId() }])
  }, [])

  const ensureSession = useCallback(async () => {
    if (sessionIdRef.current) return sessionIdRef.current
    const session = await startSiteChatSession()
    sessionIdRef.current = session.session_id
    appendLine({ role: 'assistant', text: session.welcome })
    return session.session_id
  }, [appendLine])

  const openPanel = useCallback(async () => {
    setOpen(true)
    setError(null)
    if (bootstrappedRef.current) return
    bootstrappedRef.current = true
    setLoading(true)
    try {
      await ensureSession()
    } catch {
      setError('Chat is temporarily unavailable. Visit our contact page instead.')
      bootstrappedRef.current = false
    } finally {
      setLoading(false)
    }
  }, [ensureSession])

  const togglePanel = useCallback(() => {
    if (open) {
      setOpen(false)
      return
    }
    void openPanel()
  }, [open, openPanel])

  const sendMessage = useCallback(
    async (overrideText?: string) => {
      const text = (overrideText ?? draft).trim()
      if (!text || loading) return

      if (!overrideText) setDraft('')
      setError(null)
      appendLine({ role: 'user', text })
      setLoading(true)

      try {
        const sessionId = await ensureSession()
        const reply = await sendSiteChatMessage(sessionId, text)
        setLastReply(reply)
        appendLine({
          role: 'assistant',
          text: reply.response,
          grounded: reply.grounded,
          sources: reply.sources,
        })
      } catch {
        setError('Could not send your message. Please try again or use the links below.')
      } finally {
        setLoading(false)
      }
    },
    [appendLine, draft, ensureSession, loading]
  )

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    void sendMessage()
  }

  const copyTranscript = useCallback(async () => {
    const text = formatSiteChatTranscript(sessionIdRef.current, lines, lastReply)
    try {
      await copyTextToClipboard(text)
      setCopyState('copied')
      window.setTimeout(() => setCopyState('idle'), 1600)
    } catch {
      /* clipboard blocked — no user-facing error in dev helper */
    }
  }, [lastReply, lines])

  useEffect(() => {
    if (!open) return
    const anchor = scrollAnchorRef.current
    if (anchor && typeof anchor.scrollIntoView === 'function') {
      anchor.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }, [lines, loading, open])

  useEffect(() => {
    if (!open || loading) return
    const timer = window.setTimeout(() => inputRef.current?.focus(), 80)
    return () => window.clearTimeout(timer)
  }, [loading, open])

  const handoffHref = lastReply ? handoffPath(lastReply.handoff) : null
  const handoffCta = handoffLabel(lastReply?.handoff.handoff_type)

  return (
    <div className="fixed bottom-4 right-4 z-[60] flex flex-col items-end gap-3 pb-[env(safe-area-inset-bottom)] pr-[env(safe-area-inset-right)]">
      {open && (
        <div
          className="flex w-[min(100vw-2rem,26rem)] flex-col overflow-hidden rounded-2xl border border-neutral-200/80 bg-white text-neutral-900 shadow-[0_20px_60px_-12px_rgba(179,59,30,0.35)]"
          role="dialog"
          aria-label="Fikiri assistant chat"
          aria-modal="false"
        >
          <header className="relative overflow-hidden bg-gradient-to-br from-[#992D1E] via-[#B33B1E] to-[#C55A0F] px-4 py-3 text-white">
            <div className="pointer-events-none absolute -right-6 -top-8 h-24 w-24 rounded-full bg-white/10 blur-2xl" />
            <div className="relative flex items-start justify-between gap-3">
              <div className="flex min-w-0 items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white/15 ring-1 ring-white/25">
                  <FikiriLogo variant="white" size="xs" className="!h-7 w-7" />
                </div>
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold tracking-tight text-white">
                    Fikiri Assistant
                  </p>
                  <p className="flex items-center gap-1 text-xs text-white/95">
                    <Sparkles className="h-3 w-3 shrink-0 text-white" aria-hidden />
                    Answers from fikirisolutions.com
                  </p>
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-1">
                {devTools && (
                  <button
                    type="button"
                    onClick={() => void copyTranscript()}
                    className={cn(
                      'rounded-lg px-2 py-1 text-xs font-medium text-white/95 transition hover:bg-white/15',
                      copyState === 'copied' && 'bg-white/20'
                    )}
                    aria-label="Copy chat transcript"
                    title="Copy full thread for dev/debug"
                  >
                    <span className="inline-flex items-center gap-1">
                      <Copy className="h-3.5 w-3.5" aria-hidden />
                      {copyState === 'copied' ? 'Copied' : 'Copy'}
                    </span>
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className="rounded-lg p-1.5 text-white/90 transition hover:bg-white/15"
                  aria-label="Close chat"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>
          </header>

          {intakeActive && (
            <div className="border-b border-neutral-200 bg-[#FFF8F0] px-4 py-2.5">
              <div className="mb-1.5 flex items-center justify-between gap-2 text-xs">
                <span className="font-medium text-neutral-800">Quick fit check</span>
                <span className="text-neutral-600">
                  {intakeComplete ? 'Complete' : `${intakeFilled} of 4`}
                </span>
              </div>
              <div
                className="h-1.5 overflow-hidden rounded-full bg-black/10"
                role="progressbar"
                aria-valuenow={intakeFilled}
                aria-valuemin={0}
                aria-valuemax={4}
                aria-label="Intake progress"
              >
                <div
                  className="h-full rounded-full bg-gradient-to-r from-fikiri-400 to-brand-primary transition-all duration-300"
                  style={{ width: `${Math.min(100, (intakeFilled / 4) * 100)}%` }}
                />
              </div>
            </div>
          )}

          <div className="max-h-[min(50vh,28rem)] space-y-3 overflow-y-auto bg-[#FAFAFA] px-3 py-4 sm:px-4">
            {lines.map((line) => (
              <div
                key={line.id}
                className={cn(
                  'flex gap-2',
                  line.role === 'user' ? 'flex-row-reverse' : 'flex-row'
                )}
              >
                {line.role === 'assistant' && (
                  <div
                    className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-white shadow-sm ring-1 ring-black/5"
                    aria-hidden
                  >
                    <FikiriLogo variant="circle" size="xs" className="!h-5 w-5" />
                  </div>
                )}
                <div
                  className={cn(
                    'max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed shadow-sm',
                    line.role === 'user'
                      ? 'rounded-br-md bg-gradient-to-br from-[#992D1E] to-[#B33B1E] text-white'
                      : 'rounded-bl-md border border-neutral-200 bg-white text-neutral-900'
                  )}
                >
                  <p className="whitespace-pre-wrap">{line.text}</p>
                  {line.role === 'assistant' && line.grounded && (
                    <p className="mt-2 flex items-center gap-1 text-[11px] font-medium text-neutral-600">
                      <Sparkles className="h-3 w-3 text-[#B33B1E]" aria-hidden />
                      Grounded in site content
                    </p>
                  )}
                  {line.role === 'assistant' && line.sources && line.sources.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {line.sources.slice(0, 2).map((source) => (
                        <span
                          key={source.id}
                          className="inline-flex max-w-full items-center rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] text-neutral-700"
                        >
                          {source.source_url ? (
                            <a
                              href={source.source_url}
                              target="_blank"
                              rel="noreferrer"
                              className="truncate text-[#8B4513] underline-offset-2 hover:text-[#B33B1E] hover:underline"
                            >
                              {sourceLabel(source.source_url)}
                            </a>
                          ) : (
                            <span className="truncate">{source.topic || 'Fikiri KB'}</span>
                          )}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {showQuickPrompts && (
              <div className="pt-1">
                <p className="mb-2 text-center text-[11px] font-semibold uppercase tracking-wide text-neutral-500">
                  Popular questions
                </p>
                <div className="flex flex-wrap justify-center gap-2">
                  {QUICK_PROMPTS.map((prompt) => (
                    <button
                      key={prompt.label}
                      type="button"
                      disabled={loading}
                      onClick={() => void sendMessage(prompt.message)}
                      className="rounded-full border border-neutral-300 bg-white px-3 py-1.5 text-xs font-medium text-neutral-800 shadow-sm transition hover:border-[#B33B1E]/40 hover:bg-[#FFF8F0] disabled:opacity-50"
                    >
                      {prompt.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {loading && (
              <div className="flex items-center gap-2 px-1 text-xs text-neutral-600">
                <div className="flex h-7 w-7 items-center justify-center rounded-full bg-white shadow-sm ring-1 ring-black/5">
                  <FikiriLogo variant="circle" size="xs" className="!h-5 w-5" />
                </div>
                <div className="flex items-center gap-2 rounded-2xl rounded-bl-md border border-neutral-200 bg-white px-3 py-2 text-neutral-700">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-[#B33B1E]" />
                  <span>Thinking…</span>
                </div>
              </div>
            )}

            {error && (
              <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
                <p>{error}</p>
                <Link to="/contact" className="mt-1 inline-block font-medium underline">
                  Go to contact page
                </Link>
              </div>
            )}

            <div ref={scrollAnchorRef} aria-hidden className="h-px w-full shrink-0" />
          </div>

          {handoffHref && (
            <div className="border-t border-neutral-200 bg-neutral-50 px-4 py-2.5">
              <Link
                to={handoffHref}
                className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[#B33B1E] px-3 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#992D1E]"
              >
                {handoffCta}
                <ArrowRight className="h-4 w-4" aria-hidden />
              </Link>
            </div>
          )}

          <form onSubmit={onSubmit} className="border-t border-neutral-200 bg-white p-3">
            <div className="flex items-center gap-2">
              <label htmlFor="fikiri-site-chat-input" className="sr-only">
                Message Fikiri assistant
              </label>
              <input
                ref={inputRef}
                id="fikiri-site-chat-input"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Ask about pricing, fit, or audits…"
                disabled={loading}
                autoComplete="off"
                className="min-h-[44px] flex-1 rounded-xl border border-neutral-300 bg-white px-3 text-sm text-neutral-900 placeholder:text-neutral-400 outline-none transition focus:border-[#B33B1E]/50 focus:ring-2 focus:ring-[#B33B1E]/20"
              />
              <button
                type="submit"
                disabled={loading || !draft.trim()}
                className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl bg-[#B33B1E] text-white shadow-sm transition hover:bg-[#992D1E] disabled:opacity-50"
                aria-label="Send message"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </form>

          <footer className="border-t border-neutral-200 bg-white px-4 py-2 text-center text-[11px] text-neutral-500">
            Powered by Fikiri Solutions
          </footer>
        </div>
      )}

      <button
        type="button"
        onClick={togglePanel}
        className={cn(
          'group relative inline-flex h-14 w-14 items-center justify-center rounded-full text-white shadow-lg transition',
          'bg-gradient-to-br from-[#992D1E] to-[#B33B1E] hover:from-[#B33B1E] hover:to-[#C55A0F]',
          'ring-4 ring-white/90',
          open && 'scale-95 opacity-90'
        )}
        aria-label={open ? 'Minimize Fikiri assistant' : 'Open Fikiri assistant'}
        aria-expanded={open}
      >
        {open ? (
          <X className="h-6 w-6" aria-hidden />
        ) : (
          <>
            <FikiriLogo variant="white" size="xs" className="!h-8 w-8" />
            <span className="absolute -right-0.5 -top-0.5 flex h-3.5 w-3.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-fikiri-100 opacity-60" />
              <span className="relative inline-flex h-3.5 w-3.5 rounded-full bg-fikiri-100 ring-2 ring-white" />
            </span>
          </>
        )}
      </button>
    </div>
  )
}
