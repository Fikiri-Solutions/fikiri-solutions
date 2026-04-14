/**
 * Convert API/Gmail snippets and previews to customer-safe plain text.
 * No HTML tags, entities, MIME headers, or obvious code — unless explicitly shown via dev tools.
 */

import DOMPurify from 'dompurify'

const MIME_OR_HEADER_LINE =
  /^(Content-(?:Type|Transfer-Encoding|Disposition|ID)|MIME-Version|boundary=|--[a-zA-Z0-9_-]{6,}|Return-Path:|Received:|DKIM-Signature:|X-[^:]{1,40}:)/i

/** Dev / admin / internal: show raw snippet UI (never default for end users). */
export function canShowInboxTechnicalDetails(options?: { role?: string | null }): boolean {
  const r = (options?.role || '').toLowerCase()
  if (r === 'admin' || r === 'superadmin') return true
  if (import.meta.env.DEV) return true
  if (import.meta.env.VITE_INBOX_TECHNICAL === '1') return true
  if (typeof window !== 'undefined' && window.localStorage?.getItem('fikiri-inbox-technical') === '1') {
    return true
  }
  return false
}

function decodeHtmlEntitiesOnce(s: string): string {
  if (typeof document === 'undefined') {
    return s
      .replace(/&nbsp;/gi, ' ')
      .replace(/&amp;/g, '&')
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&quot;/g, '"')
      .replace(/&#(\d+);/g, (_, n) => {
        const code = Number(n)
        return Number.isFinite(code) && code >= 0 && code < 0x110000 ? String.fromCodePoint(code) : _
      })
      .replace(/&#x([0-9a-f]+);/gi, (_, h) => {
        const code = parseInt(h, 16)
        return Number.isFinite(code) && code >= 0 && code < 0x110000 ? String.fromCodePoint(code) : _
      })
  }
  const ta = document.createElement('textarea')
  ta.innerHTML = s
  return ta.value
}

function stripMarkupToTextBrowser(s: string): string {
  const shell = document.createElement('div')
  shell.innerHTML = DOMPurify.sanitize(s, { ALLOWED_TAGS: [], KEEP_CONTENT: true })
  return (shell.textContent || '').replace(/\u00a0/g, ' ')
}

/**
 * Gmail/API snippets are often truncated mid-tag (`<div id="ms-outlook…`, `<meta name=robots…`).
 * DOM + `/<[^>]+>/g` miss those. Split on `>` and drop from each segment's first real tag opener.
 */
function stripTruncatedAndResidualHtmlFragments(s: string): string {
  const tagStart = /<(?:\/?|\!?)[a-zA-Z]/
  return s
    .split('>')
    .map((segment) => {
      const m = segment.match(tagStart)
      if (!m || m.index === undefined) return segment
      return segment.slice(0, m.index)
    })
    .join(' ')
}

/**
 * Final pass: remove any remaining complete tags and whitespace-collapse.
 */
function stripRemainingCompleteTags(s: string): string {
  let t = s
  for (let i = 0; i < 12; i++) {
    const n = t.replace(/<[^>]+>/g, ' ')
    if (n === t) break
    t = n
  }
  return t
}

/** Regex-only fallback when DOM is unavailable (tests / SSR). */
function stripMarkupToTextRegex(s: string): string {
  let t = s
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, ' ')
    .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, ' ')
    .replace(/<!--[\s\S]*?-->/g, ' ')
    .replace(/<[^>]+>/g, ' ')
  t = decodeHtmlEntitiesOnce(t)
  return t.replace(/\u00a0/g, ' ')
}

function filterMimeNoise(multiline: string): string {
  return multiline
    .split(/\r?\n/)
    .filter((line) => {
      const x = line.trim()
      if (!x) return false
      if (MIME_OR_HEADER_LINE.test(x)) return false
      if (/^--[a-zA-Z0-9_-]{8,}$/.test(x)) return false
      return true
    })
    .join(' ')
}

function looksLikeTechnicalGarbage(t: string): boolean {
  const s = t.trim()
  if (!s) return true
  if (/<(?:\/?|\!?)[a-zA-Z]/.test(s)) return true
  if (/\b(?:<!DOCTYPE|DOCTYPE|xmlns=|Content-Transfer-Encoding|MIME-Version)\b/i.test(s)) return true
  if (/^\s*[\[{]\s*"(?:intent|confidence|@type|success)"/.test(s)) return true
  if (/\b(?:function\s*\(|var\s+\w+\s*=|<\?php|SELECT\s+\*\s+FROM)\b/i.test(s)) return true
  const tagLike = (s.match(/<\/?[a-z][a-z0-9]*\b/gi) || []).length
  if (tagLike >= 3) return true
  return false
}

export type SnippetOptions = {
  /** One-line list preview vs body fallback with newlines from block elements */
  preserveNewlines?: boolean
  maxLen: number
}

/**
 * Customer-facing snippet: plain language only; returns '' if nothing safe to show.
 */
export function emailSnippetToCustomerPlainText(raw: string, options: SnippetOptions): string {
  const { preserveNewlines = false, maxLen } = options
  if (!raw?.trim()) return ''

  let s = raw.trim()
  s = s.replace(/^\s*<!DOCTYPE[^>]*>/i, '').replace(/<\?xml[^?]*\?>/gi, '')
  s = decodeHtmlEntitiesOnce(s)
  // Second pass if still entity-heavy (double-encoded)
  if (/&(lt|gt|amp|#\d+|#x[0-9a-f]+);/i.test(s)) {
    s = decodeHtmlEntitiesOnce(s)
  }

  let text: string
  if (typeof document !== 'undefined') {
    try {
      text = stripMarkupToTextBrowser(s)
    } catch {
      text = stripMarkupToTextRegex(s)
    }
  } else {
    text = stripMarkupToTextRegex(s)
  }

  text = stripTruncatedAndResidualHtmlFragments(text)
  text = stripRemainingCompleteTags(text)

  text = text
    .replace(/\bContent-Type:\s*[^\s;]+(?:\s*;\s*charset=[^\s"]+)?/gi, ' ')
    .replace(/\bMIME-Version:\s*[^\s]+/gi, ' ')
    .replace(/\bContent-Transfer-Encoding:\s*[^\s]+/gi, ' ')

  if (preserveNewlines) {
    text = text.replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n')
  } else {
    text = text.replace(/\s+/g, ' ')
  }
  text = filterMimeNoise(text)
  if (!preserveNewlines) {
    text = text.replace(/\s+/g, ' ').trim()
  } else {
    text = text.trim()
  }

  if (looksLikeTechnicalGarbage(text)) {
    return ''
  }

  if (text.length > maxLen) {
    const cut = text.slice(0, maxLen).trim()
    return `${cut}…`
  }
  return text
}

/**
 * When email body is "plain" but contains escaped HTML, show decoded safe text only.
 */
export function emailPlainBodyForCustomerDisplay(content: string): string {
  if (!content?.trim()) return ''
  let s = content
  if (/&(lt|gt|amp|nbsp|#\d+|#x[0-9a-f]+);/i.test(s)) {
    s = decodeHtmlEntitiesOnce(s)
  }
  if (/<[a-z][\s\S]*>/i.test(s)) {
    return emailSnippetToCustomerPlainText(s, { preserveNewlines: true, maxLen: 500_000 })
  }
  return s
}
