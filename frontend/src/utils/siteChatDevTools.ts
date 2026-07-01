import type { FikiriSiteChatMessageData } from '../types/fikiriSiteBot'

export interface TranscriptLine {
  role: 'assistant' | 'user'
  text: string
  grounded?: boolean
  sources?: FikiriSiteChatMessageData['sources']
}

/** Dev-only widget affordances (matches Symbolics `data-dev-tools` / localhost). */
export function isSiteChatDevToolsEnabled(): boolean {
  const forced = (import.meta.env.VITE_SITE_CHAT_DEV_TOOLS || '').trim().toLowerCase()
  if (forced === 'true' || forced === '1' || forced === 'on') return true
  if (forced === 'false' || forced === '0' || forced === 'off') return false
  if (import.meta.env.DEV) return true
  if (typeof window === 'undefined') return false
  const host = window.location.hostname
  return (
    host === 'localhost' ||
    host === '127.0.0.1' ||
    host === '[::1]' ||
    host.endsWith('.local')
  )
}

export function formatSiteChatTranscript(
  sessionId: string | null,
  lines: TranscriptLine[],
  lastReply: FikiriSiteChatMessageData | null
): string {
  const meta: string[] = [
    '# Fikiri site chat transcript (dev)',
    `session_id: ${sessionId || '(not started)'}`,
  ]
  if (lastReply) {
    meta.push(`last_mode: ${lastReply.mode}`)
    meta.push(`turn_count: ${lastReply.turn_count}`)
    if (lastReply.intake?.active) {
      meta.push(`intake_active: true (${lastReply.intake.filled_core_count ?? 0}/4)`)
    }
    if (lastReply.intake?.slots) {
      meta.push(`intake_slots: ${JSON.stringify(lastReply.intake.slots)}`)
    }
    if (lastReply.grounded) {
      meta.push(`grounded: true (confidence=${lastReply.confidence ?? 0})`)
    }
    if (lastReply.lead_assessment) {
      const la = lastReply.lead_assessment
      meta.push(
        `lead_assessment: score=${la.score} tier=${la.tier} handoff=${la.recommended_handoff ?? 'none'}`
      )
      meta.push(`lead_signals: ${(la.signals || []).join(', ') || '(none)'}`)
      if (la.synopsis) {
        meta.push(`lead_synopsis: ${la.synopsis}`)
      }
    }
  }
  meta.push('---', '')

  const body = lines.map((line) => {
    const role = line.role === 'user' ? 'User' : 'Assistant'
    const parts = [`${role}: ${line.text}`]
    if (line.role === 'assistant' && line.grounded) {
      parts.push('  [grounded]')
    }
    if (line.sources?.length) {
      const ids = line.sources.map((s) => s.id).join(', ')
      parts.push(`  [sources: ${ids}]`)
    }
    return parts.join('\n')
  })

  const text = [...meta, ...body].join('\n').trim()
  return text || '(No messages yet)'
}

export async function copyTextToClipboard(text: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text)
      return
    } catch {
      /* fall through */
    }
  }
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', '')
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  document.body.appendChild(textarea)
  textarea.select()
  try {
    document.execCommand('copy')
  } finally {
    document.body.removeChild(textarea)
  }
}
