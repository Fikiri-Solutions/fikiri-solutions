import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { Link } from 'react-router-dom'
import {
  Mail,
  Search,
  Sparkles,
  Send,
  Reply,
  Archive,
  MoreVertical,
  Loader2,
  RefreshCw,
  Paperclip,
  Download,
  Activity,
  ChevronLeft,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  FileText,
} from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../contexts/AuthContext'
import { apiClient } from '../services/apiClient'
import { useToast } from '../components/Toast'
import { EmptyState } from '../components/EmptyState'
import DOMPurify from 'dompurify'
import {
  canShowInboxTechnicalDetails,
  emailPlainBodyForCustomerDisplay,
  emailSnippetToCustomerPlainText,
} from '../utils/emailPlainText'

interface Attachment {
  id: number
  attachment_id: string
  filename: string
  mime_type: string
  size: number
}

function isImageMime(mimeType?: string): boolean {
  return Boolean(mimeType && mimeType.startsWith('image/'))
}

function isAudioMime(mimeType?: string): boolean {
  return Boolean(mimeType && mimeType.startsWith('audio/'))
}

function isVideoMime(mimeType?: string): boolean {
  return Boolean(mimeType && mimeType.startsWith('video/'))
}

function isPdfMime(mimeType?: string): boolean {
  return mimeType === 'application/pdf'
}

function canPreviewAttachment(mimeType?: string): boolean {
  return isImageMime(mimeType) || isAudioMime(mimeType) || isVideoMime(mimeType) || isPdfMime(mimeType)
}

interface Email {
  id: string
  subject: string
  from: string
  from_name?: string
  date: string
  snippet: string
  body?: string
  unread: boolean
  has_attachments?: boolean
  attachments?: Attachment[]
  thread_id?: string
}

/** Outlook-style initials for avatar chips */
function senderInitials(fromName: string | undefined, from: string): string {
  const raw = (fromName || from || '?').replace(/<[^>]+>/g, '').trim()
  const parts = raw.split(/\s+/).filter(Boolean)
  if (parts.length >= 2) {
    const a = parts[0][0] || ''
    const b = parts[parts.length - 1][0] || ''
    return (a + b).toUpperCase().slice(0, 2)
  }
  return raw.slice(0, 2).toUpperCase() || '?'
}

/** Gmail-style: time if today, else short date */
function formatInboxListDate(iso: string): string {
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return ''
    const now = new Date()
    const sameDay =
      d.getFullYear() === now.getFullYear() &&
      d.getMonth() === now.getMonth() &&
      d.getDate() === now.getDate()
    if (sameDay) {
      return d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
    }
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  } catch {
    return ''
  }
}

/** API image URLs need Authorization; plain <img src> does not send Bearer tokens — fetch as blob. */
function getAuthTokenForImages(): string | null {
  if (typeof window === 'undefined') return null
  const direct = localStorage.getItem('fikiri-token')
  if (direct) return direct
  try {
    const raw = localStorage.getItem('fikiri-user')
    if (!raw) return null
    const u = JSON.parse(raw) as { token?: string; access_token?: string }
    return u.token || u.access_token || null
  } catch {
    return null
  }
}

function imageSrcNeedsAuthFetch(src: string): boolean {
  try {
    const u = new URL(src, typeof window !== 'undefined' ? window.location.origin : 'http://localhost')
    return (
      u.pathname.startsWith('/api/email/') &&
      (u.pathname.includes('/embedded-image/') || u.pathname.includes('/attachments/'))
    )
  } catch {
    return false
  }
}

// Component to safely render email body (HTML or plain text)
const EmailBodyRenderer: React.FC<{ content: string; emailId?: string }> = ({ content, emailId }) => {
  const containerRef = React.useRef<HTMLDivElement>(null)

  // Check if content is HTML (contains HTML tags)
  const isHTML = /<[a-z][\s\S]*>/i.test(content)

  // Load same-origin /api/email/* images with JWT (matches Gmail-visible inline attachments)
  React.useEffect(() => {
    if (!containerRef.current || !isHTML) return

    const container = containerRef.current
    let cancelled = false
    const objectUrls: string[] = []

    const run = async () => {
      const token = getAuthTokenForImages()
      const imgs = Array.from(container.querySelectorAll('img'))
      for (const img of imgs) {
        if (cancelled) return
        const raw = img.getAttribute('src') || ''
        if (!raw || raw.startsWith('blob:') || !imageSrcNeedsAuthFetch(raw)) continue
        try {
          const url = new URL(raw, window.location.origin).toString()
          const res = await fetch(url, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            credentials: 'include',
          })
          if (!res.ok || cancelled) continue
          const blob = await res.blob()
          if (cancelled) return
          const objUrl = URL.createObjectURL(blob)
          objectUrls.push(objUrl)
          img.src = objUrl
          img.removeAttribute('crossorigin')
        } catch {
          /* keep original src — may work with session cookie */
        }
      }
    }

    void run()

    return () => {
      cancelled = true
      objectUrls.forEach((u) => URL.revokeObjectURL(u))
    }
  }, [content, emailId, isHTML])

  // Optional: log broken remote images without removing them (newsletter logos)
  React.useEffect(() => {
    if (!containerRef.current || !isHTML) return
    const images = containerRef.current.querySelectorAll('img')
    const handleImageError = (e: Event) => {
      const img = e.target as HTMLImageElement
      if (img.src.startsWith('blob:')) return
      console.warn('Image failed to load:', img.getAttribute('src') || img.src)
    }
    images.forEach((img) => img.addEventListener('error', handleImageError))
    return () => images.forEach((img) => img.removeEventListener('error', handleImageError))
  }, [content, isHTML])
  
  if (isHTML) {
    // Process HTML to handle images properly
    let processedHTML = content.replace(/\/api\/business\/email\//g, '/api/email/')

    // Replace relative image URLs with absolute URLs if needed
    // Handle cid: references (these should already be replaced by backend, but handle edge cases)
    if (emailId) {
      processedHTML = processedHTML.replace(
        /src=["']cid:([^"']+)["']/gi,
        (match, cid) => {
          // If backend didn't replace it, we'll need to handle it client-side
          // For now, keep the cid: reference - backend should handle this
          return match
        }
      )
    }
    
    // Sanitize HTML content - allow safe HTML tags and attributes
    // ALLOWED_URI_REGEXP must allow: https?, data:, cid:, and relative paths (/api/...)
    // so internal/embedded email images (proxy URLs) are not stripped
    const sanitizedHTML = DOMPurify.sanitize(processedHTML, {
      ALLOWED_TAGS: [
        'p', 'br', 'div', 'span', 'strong', 'em', 'b', 'i', 'u', 'a',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li',
        'img', 'table', 'thead', 'tbody', 'tfoot', 'tr', 'td', 'th',
        'blockquote', 'pre', 'code', 'hr', 'style', 'center', 'font',
        'caption', 'colgroup', 'col', 'picture', 'source',
        's', 'strike', 'del', 'ins', 'sub', 'sup', 'small', 'wbr',
      ],
      ALLOWED_ATTR: [
        'href', 'title', 'alt', 'src', 'srcset', 'sizes', 'width', 'height', 'style',
        'class', 'id', 'align', 'colspan', 'rowspan', 'loading', 'decoding',
        'bgcolor', 'background', 'border', 'cellpadding', 'cellspacing', 'valign',
        'face', 'color', 'size', 'media', 'type', 'referrerpolicy',
      ],
      ALLOWED_URI_REGEXP: /^(?:(?:(?:f|ht)tps?|mailto|tel|callto|sms|cid|xmpp|data|blob):|\/)/i,
      ALLOW_UNKNOWN_PROTOCOLS: true,
      ALLOW_DATA_ATTR: false,
      KEEP_CONTENT: true,
      ADD_ATTR: ['target', 'rel'],
      ADD_TAGS: [],
    })
    
    return (
      <>
        <style>{`
          .email-body-html-wrap {
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
          }
          .email-body-html {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.65;
            font-size: 15px;
            overflow-wrap: anywhere;
            word-break: break-word;
          }
          @media (max-width: 767px) {
            .email-body-html {
              font-size: 16px;
            }
          }
          .email-body-html img {
            max-width: 100%;
            height: auto;
            border-radius: 2px;
            margin: 4px 0;
            vertical-align: middle;
            object-fit: contain;
          }
          .email-body-html table {
            max-width: 100%;
            width: auto;
            border-collapse: separate;
            border-spacing: 0;
            margin: 0;
          }
          .email-body-html table td,
          .email-body-html table th {
            vertical-align: top;
          }
          .email-body-html blockquote {
            border-left: 4px solid #3b82f6;
            padding-left: 16px;
            margin: 12px 0;
            color: rgba(0, 0, 0, 0.7);
          }
          .dark .email-body-html blockquote {
            color: rgba(255, 255, 255, 0.7);
            border-left-color: #60a5fa;
          }
          .email-body-html pre {
            background: rgba(0, 0, 0, 0.05);
            padding: 12px;
            border-radius: 4px;
            overflow-x: auto;
          }
          .dark .email-body-html pre {
            background: rgba(255, 255, 255, 0.05);
          }
          .email-body-html img[src^="http"] {
            image-rendering: auto;
          }
          .email-body-html img[src=""],
          .email-body-html img:not([src]) {
            display: none;
          }
          .email-body-html a {
            color: #3b82f6;
            text-decoration: underline;
          }
          .email-body-html a:hover {
            color: #2563eb;
          }
          .dark .email-body-html a {
            color: #93c5fd;
          }
          .dark .email-body-html a:hover {
            color: #bfdbfe;
          }
        `}</style>
        <div className="email-body-html-wrap min-w-0">
          <div
            ref={containerRef}
            className="email-body-html max-w-none text-brand-text dark:text-white"
            dangerouslySetInnerHTML={{ __html: sanitizedHTML }}
          />
        </div>
      </>
    )
  } else {
    const safePlain = emailPlainBodyForCustomerDisplay(content)
    return (
      <div className="whitespace-pre-wrap text-brand-text dark:text-white font-sans text-sm leading-relaxed">
        {safePlain || '—'}
      </div>
    )
  }
}

interface AIAnalysis {
  intent?: string
  urgency?: 'low' | 'medium' | 'high'
  suggested_action?: string
  summary?: string
  suggested_reply?: string
  contact_info?: {
    phone?: string | null
    company?: string | null
    website?: string | null
    location?: string | null
    budget?: string | null
    timeline?: string | null
  }
}

const AI_PANEL_EXPANDED_KEY = 'fikiri:inbox-ai-panel-expanded'

function hasAiPanelContent(a: AIAnalysis | null, loading: boolean): boolean {
  if (loading) return true
  if (!a) return false
  return Boolean(
    a.summary ||
      a.intent ||
      a.urgency ||
      a.suggested_action ||
      a.suggested_reply ||
      (a.contact_info &&
        Object.values(a.contact_info).some(
          (v) => v != null && String(v).trim() !== ''
        ))
  )
}

export const EmailInbox: React.FC = () => {
  const { user } = useAuth()
  const { addToast } = useToast()
  const queryClient = useQueryClient()
  const [selectedEmail, setSelectedEmail] = useState<Email | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiAnalysis, setAiAnalysis] = useState<AIAnalysis | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [showRawSnippets, setShowRawSnippets] = useState(false)
  const showInboxTechnical = canShowInboxTechnicalDetails({ role: user?.role })
  const [filter, setFilter] = useState<'all' | 'unread' | 'read'>('all')
  const [replyText, setReplyText] = useState('')
  const [showReplyComposer, setShowReplyComposer] = useState(false)
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [loadingAttachments, setLoadingAttachments] = useState(false)
  const [previewAttachmentId, setPreviewAttachmentId] = useState<string | null>(null)
  const [emailLimit, setEmailLimit] = useState(50) // Initial page size; use "Load more" for additional pages
  const [loadingMore, setLoadingMore] = useState(false)
  const [syncInboxPending, setSyncInboxPending] = useState(false)
  const [isNarrowViewport, setIsNarrowViewport] = useState(false)
  const [aiPanelExpanded, setAiPanelExpanded] = useState(() => {
    if (typeof window === 'undefined') return false
    try {
      return localStorage.getItem(AI_PANEL_EXPANDED_KEY) === '1'
    } catch {
      return false
    }
  })
  const markReadAttemptedRef = useRef<Set<string>>(new Set())

  useEffect(() => {
    try {
      localStorage.setItem(AI_PANEL_EXPANDED_KEY, aiPanelExpanded ? '1' : '0')
    } catch {
      // ignore
    }
  }, [aiPanelExpanded])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const mq = window.matchMedia('(max-width: 1023px)')
    const update = () => setIsNarrowViewport(mq.matches)
    update()
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])

  const hideListOnMobile = isNarrowViewport && !!selectedEmail
  const hideDetailOnMobile = isNarrowViewport && !selectedEmail

  // Reset email limit when filter changes
  useEffect(() => {
    setEmailLimit(50)
  }, [filter])

  const loadAttachments = useCallback(async (emailId: string) => {
    setLoadingAttachments(true)
    try {
      const list = await apiClient.getEmailAttachments(emailId)
      if (list && Array.isArray(list)) {
        setAttachments(list)
      } else {
        setAttachments([])
      }
    } catch (error) {
      console.error('Failed to load attachments:', error)
      setAttachments([])
    } finally {
      setLoadingAttachments(false)
    }
  }, [])

  // Load attachments when email is selected (must run after loadAttachments exists)
  useEffect(() => {
    if (selectedEmail?.id) {
      void loadAttachments(selectedEmail.id)
    } else {
      setAttachments([])
      setPreviewAttachmentId(null)
    }
  }, [selectedEmail?.id, loadAttachments])

  useEffect(() => {
    if (attachments.length === 0) {
      setPreviewAttachmentId(null)
      return
    }
    const preferred = attachments.find((att) => canPreviewAttachment(att.mime_type))
    setPreviewAttachmentId(preferred?.attachment_id ?? null)
  }, [attachments])

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  // Check Gmail connection status with caching
  const { data: gmailStatus, isLoading: checkingConnection } = useQuery({
    queryKey: ['gmail-connection', user?.id],
    queryFn: async () => {
      const status = await apiClient.getGmailConnectionStatus()
      return {
        connected: status?.connected === true,
        status
      }
    },
    enabled: !!user,
    staleTime: 2 * 60 * 1000, // 2 minutes - connection status doesn't change often
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: false,
    refetchOnMount: false,
  })

  const gmailConnected = gmailStatus?.connected ?? null

  // Mark as read in Gmail when opening an unread message (gmail.modify scope demo)
  useEffect(() => {
    const id = selectedEmail?.id
    const unread = selectedEmail?.unread
    if (!id || !unread || gmailConnected !== true || !user?.id) return
    if (markReadAttemptedRef.current.has(id)) return
    markReadAttemptedRef.current.add(id)

    let cancelled = false
    ;(async () => {
      try {
        await apiClient.markEmailRead(id)
        if (cancelled) return
        setSelectedEmail((prev) => (prev && prev.id === id ? { ...prev, unread: false } : prev))
        queryClient.invalidateQueries({ queryKey: ['emails', user.id] })
      } catch {
        markReadAttemptedRef.current.delete(id)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [selectedEmail?.id, selectedEmail?.unread, gmailConnected, user?.id, queryClient])

  const {
    data: emailDetail,
    isFetching: detailFetching
  } = useQuery({
    queryKey: ['email-detail', user?.id, selectedEmail?.id],
    queryFn: () => apiClient.getEmailMessage(selectedEmail!.id),
    enabled: Boolean(user && selectedEmail?.id && gmailConnected === true),
    staleTime: 2 * 60 * 1000,
    gcTime: 15 * 60 * 1000,
    refetchOnWindowFocus: false
  })

  const displayBody =
    (emailDetail?.body && String(emailDetail.body).trim() !== '')
      ? emailDetail.body
      : (selectedEmail?.body && String(selectedEmail.body).trim() !== '')
        ? selectedEmail.body
        : ''

  // Load emails with React Query caching - prefer synced emails for speed
  const { 
    data: emailsData, 
    isLoading: loading, 
    isFetching,
    refetch: refetchEmails 
  } = useQuery({
    queryKey: ['emails', user?.id, filter, emailLimit],
    queryFn: async () => {
      // Live Gmail API (use_synced: false) so read/unread matches Gmail; local DB can lag until sync
      const data = await apiClient.getEmails({
        filter,
        limit: emailLimit,
        use_synced: false,
        include_body: false,
      })
      return { ...data, source: data?.source ?? 'gmail_api' }
    },
    enabled: !!user && gmailConnected === true,
    staleTime: 1 * 60 * 1000, // 1 minute - emails are fresh for 1 minute
    gcTime: 15 * 60 * 1000, // 15 minutes - keep in cache for 15 minutes
    refetchInterval: 2 * 60 * 1000, // Auto-refresh every 2 minutes
    refetchOnWindowFocus: true,
    refetchOnMount: true,
    refetchOnReconnect: true, // Refetch if network reconnected
    placeholderData: (previousData) => previousData, // Show cached data while fetching
  })

  const emails = emailsData?.emails || emailsData || []
  const hasMore = emailsData?.pagination?.has_more || (emails.length >= emailLimit && emails.length % emailLimit === 0)
  
  // Load more emails function
  const loadMoreEmails = useCallback(async () => {
    if (loadingMore || !hasMore) return
    
    setLoadingMore(true)
    try {
      const newLimit = emailLimit + 25
      setEmailLimit(newLimit)
      // Query will automatically refetch with new limit
      await refetchEmails()
    } catch (error) {
      console.error('Failed to load more emails:', error)
      addToast({ type: 'error', title: 'Failed to load more emails' })
    } finally {
      setLoadingMore(false)
    }
  }, [emailLimit, hasMore, loadingMore, refetchEmails, addToast])

  // Manual refresh function
  const handleRefresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['emails', user?.id] })
    queryClient.invalidateQueries({ queryKey: ['email-detail', user?.id] })
    refetchEmails()
  }, [queryClient, user?.id, refetchEmails])

  const handleSyncInbox = useCallback(async () => {
    if (!gmailConnected) {
      addToast({
        type: 'info',
        title: 'Gmail not connected',
        message: 'Connect Gmail under Integrations to sync your inbox.',
      })
      return
    }
    setSyncInboxPending(true)
    try {
      await apiClient.triggerGmailSync()
      addToast({
        type: 'success',
        title: 'Gmail sync started',
        message: 'New messages will appear after sync completes.',
      })
      queryClient.invalidateQueries({ queryKey: ['emails', user?.id] })
      queryClient.invalidateQueries({ queryKey: ['gmail-sync-status', user?.id] })
      setTimeout(() => refetchEmails(), 3000)
      setTimeout(() => refetchEmails(), 15000)
    } catch (error: unknown) {
      const err = error as { response?: { data?: { message?: string } }; message?: string }
      const message =
        err?.response?.data?.message || err?.message || 'Could not start Gmail sync.'
      addToast({ type: 'error', title: 'Sync failed', message })
    } finally {
      setSyncInboxPending(false)
    }
  }, [gmailConnected, addToast, queryClient, user?.id, refetchEmails])

  const analyzeEmail = async (email: Email) => {
    const content = displayBody || email.body || email.snippet
    if (!content?.trim()) {
      addToast({ type: 'error', title: 'No email content to analyze' })
      return
    }

    setAiLoading(true)
    setAiAnalysis(null)
    
    try {
      const data = await apiClient.analyzeEmail(
        email.id,
        email.subject,
        content,
        email.from
      )
      setAiAnalysis(data)
      setAiPanelExpanded(true)
    } catch (error) {
      console.error('Error analyzing email:', error)
      addToast({ type: 'error', title: 'AI analysis unavailable', message: 'The AI assistant is currently unavailable.' })
    } finally {
      setAiLoading(false)
    }
  }

  const generateReply = async (email: Email) => {
    const content = displayBody || email.body || email.snippet
    if (!content?.trim()) {
      addToast({ type: 'error', title: 'No email content to reply to' })
      return
    }

    setAiLoading(true)
    
    try {
      const data = await apiClient.generateReply(
        email.id,
        email.subject,
        content,
        email.from
      )
      const reply = data?.reply || data?.data?.reply || data?.suggested_reply
      if (reply) {
        setAiAnalysis((prev) => ({ ...prev, suggested_reply: reply }))
        setReplyText(reply)
        setAiPanelExpanded(true)
        addToast({ type: 'success', title: 'Reply generated', message: 'AI has generated a suggested reply.' })
      } else {
        addToast({ type: 'warning', title: 'No reply generated', message: 'AI could not generate a reply for this email.' })
      }
    } catch (error) {
      console.error('Error generating reply:', error)
      addToast({ type: 'error', title: 'Reply generation unavailable', message: 'The AI assistant is currently unavailable.' })
    } finally {
      setAiLoading(false)
    }
  }

  const handleArchive = async (email: Email) => {
    if (!confirm('Are you sure you want to archive this email?')) {
      return
    }

    try {
      await apiClient.archiveEmail(email.id)
      // Clear selection if this was the selected email
      if (selectedEmail?.id === email.id) {
        setSelectedEmail(null)
        setAiAnalysis(null)
      }
      addToast({ type: 'success', title: 'Email archived', message: 'The email has been archived successfully.' })
      // Invalidate cache and refetch to reflect the change
      queryClient.invalidateQueries({ queryKey: ['emails', user?.id] })
      refetchEmails()
    } catch (error: any) {
      console.error('Error archiving email:', error)
      const errorMessage = error?.response?.data?.message || error?.message || 'Failed to archive email'
      addToast({ type: 'error', title: 'Archive failed', message: errorMessage })
    }
  }

  const handleReply = (email: Email) => {
    // Extract reply-to email
    const replyTo = email.from.includes('<') 
      ? email.from.match(/<(.+)>/)?.[1] || email.from
      : email.from
    
    setReplyText(`Re: ${email.subject}\n\n`)
    setShowReplyComposer(true)
  }

  const handleSendReply = async (email: Email) => {
    if (!replyText.trim()) {
      addToast({ type: 'error', title: 'Empty reply', message: 'Please enter a reply message.' })
      return
    }

    try {
      // Extract reply-to email
      const replyTo = email.from.includes('<') 
        ? email.from.match(/<(.+)>/)?.[1] || email.from
        : email.from
      
      const subject = email.subject.startsWith('Re:') ? email.subject : `Re: ${email.subject}`
      
      await apiClient.sendEmail({
        to: replyTo,
        subject: subject,
        body: replyText
      })
      
      addToast({ type: 'success', title: 'Reply sent', message: 'Your reply has been sent successfully.' })
      setShowReplyComposer(false)
      setReplyText('')
      // Invalidate cache and refetch to show the sent reply
      queryClient.invalidateQueries({ queryKey: ['emails', user?.id] })
      refetchEmails()
    } catch (error: any) {
      console.error('Error sending reply:', error)
      const errorMessage = error?.response?.data?.message || error?.message || 'Failed to send reply'
      addToast({ type: 'error', title: 'Send failed', message: errorMessage })
    }
  }

  const handleUseSuggestedReply = () => {
    if (aiAnalysis?.suggested_reply) {
      setReplyText(aiAnalysis.suggested_reply)
      setShowReplyComposer(true)
      addToast({ type: 'info', title: 'Reply loaded', message: 'Suggested reply loaded. Edit if needed and click Send.' })
    }
  }

  // Optimized: memoize filter results and toLowerCase() calls
  const filteredEmails = useMemo(() => {
    if (!searchQuery && filter === 'all') return emails
    
    const searchLower = searchQuery.toLowerCase()
    return emails.filter((email: Email) => {
      const snippetPlain = emailSnippetToCustomerPlainText(email.snippet || '', { maxLen: 50_000 })
      const matchesSearch = !searchQuery || 
        email.subject.toLowerCase().includes(searchLower) ||
        email.from.toLowerCase().includes(searchLower) ||
        snippetPlain.toLowerCase().includes(searchLower) ||
        email.snippet.toLowerCase().includes(searchLower)
      
      const matchesFilter = filter === 'all' || 
        (filter === 'unread' && email.unread) ||
        (filter === 'read' && !email.unread)
      
      return matchesSearch && matchesFilter
    })
  }, [emails, searchQuery, filter])

  const getAttachmentDownloadUrl = useCallback(
    (attachmentId: string) => {
      if (!selectedEmail?.id) return '#'
      return `/api/email/${selectedEmail.id}/attachments/${attachmentId}/download`
    },
    [selectedEmail?.id]
  )

  const selectedPreviewAttachment = useMemo(() => {
    if (!previewAttachmentId) return null
    return attachments.find((att) => att.attachment_id === previewAttachmentId) || null
  }, [attachments, previewAttachmentId])

  const hasPreviewableAttachment = useMemo(
    () => attachments.some((a) => canPreviewAttachment(a.mime_type)),
    [attachments]
  )

  // Show loading state while checking connection
  if (checkingConnection && gmailConnected === null) {
    return (
      <div className="flex items-center justify-center h-full min-h-[60vh]">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-brand-primary mx-auto mb-4" />
          <p className="text-brand-text/70 dark:text-gray-400">Checking Gmail connection...</p>
        </div>
      </div>
    )
  }

  // Show appropriate message based on auth and Gmail connection status
  if (!user) {
    return (
      <div className="flex items-center justify-center h-full min-h-[60vh]">
        <div className="max-w-md p-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 text-center">
          <Mail className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h2 className="text-2xl font-semibold text-brand-text dark:text-white mb-2">Sign in to view your inbox</h2>
          <p className="text-brand-text/70 dark:text-gray-400 mb-6">
            Connect your Gmail account to access your inbox with AI-powered features.
          </p>
          <Link
            to="/login"
            className="inline-flex items-center px-4 py-2 bg-brand-primary text-white rounded-lg hover:bg-brand-secondary transition-colors"
          >
            Sign In
          </Link>
        </div>
      </div>
    )
  }

  // If Gmail is not connected, show connection prompt
  // Only show this if we've actually checked and confirmed it's not connected
  // Don't show if we're still checking or if gmailConnected is null (haven't checked yet)
  if (gmailConnected === false && !loading && !checkingConnection) {
    return (
      <div className="flex items-center justify-center h-full min-h-[60vh]">
        <div className="max-w-md p-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 text-center">
          <Mail className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h2 className="text-2xl font-semibold text-brand-text dark:text-white mb-2">Gmail not connected</h2>
          <p className="text-brand-text/70 dark:text-gray-400 mb-6">
            Please connect your Gmail account in Integrations to view your inbox.
          </p>
          <Link
            to="/integrations/gmail"
            className="inline-flex items-center px-4 py-2 bg-brand-primary text-white rounded-lg hover:bg-brand-secondary transition-colors"
          >
            Connect Gmail
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div
      className="flex w-full min-h-0 flex-col overflow-hidden rounded-lg border border-brand-text/10 bg-brand-background dark:border-gray-700 dark:bg-gray-900 h-[calc(100dvh-11rem)] max-h-[calc(100dvh-11rem)] lg:h-[calc(100dvh-8rem)] lg:max-h-[calc(100dvh-8rem)]"
      role="main"
      aria-label="Email inbox"
    >
      {/* Top: narrow list (left) + wide reading pane (right) */}
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden lg:flex-row lg:min-h-0">
      {/* Left: message list — fixed width on desktop so the reading column gets most space */}
      <div
        className={`min-h-0 flex w-full flex-col border-brand-text/10 dark:border-gray-700 lg:w-[min(22rem,32vw)] lg:max-w-[360px] lg:shrink-0 lg:border-r ${
          hideListOnMobile ? 'hidden' : 'flex'
        } lg:flex`}
      >
        {/* Header */}
        <div className="shrink-0 border-b border-brand-text/10 p-3 sm:p-4 dark:border-gray-700">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2 sm:mb-4">
            <h2 className="text-lg font-bold text-brand-text dark:text-white sm:text-xl">Inbox</h2>
            <div className="flex shrink-0 items-center gap-1">
              <button
                type="button"
                onClick={handleSyncInbox}
                disabled={syncInboxPending || loading || isFetching || gmailConnected !== true}
                className="inline-flex min-h-[44px] items-center gap-1.5 rounded-lg border border-brand-text/15 px-2.5 py-2 text-xs font-medium text-brand-text hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
                title="Pull latest messages from Gmail"
              >
                <Activity className={`h-4 w-4 shrink-0 ${syncInboxPending ? 'animate-pulse' : ''}`} />
                <span className="hidden sm:inline">Sync inbox</span>
                <span className="sm:hidden">Sync</span>
              </button>
              <button
                type="button"
                onClick={handleRefresh}
                disabled={loading || isFetching}
                className="flex h-11 w-11 items-center justify-center rounded-lg text-brand-text/70 transition-colors hover:bg-gray-50 disabled:opacity-50 dark:text-gray-400 dark:hover:bg-gray-800"
                title="Refresh list"
                aria-label="Refresh inbox list"
              >
                <RefreshCw className={`h-5 w-5 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>

          {/* Search */}
          <div className="relative mb-3 sm:mb-4">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-brand-text/50 dark:text-gray-500" />
            <input
              type="search"
              enterKeyHint="search"
              placeholder="Search emails..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              autoComplete="off"
              className="min-h-[44px] w-full rounded-lg border border-brand-text/20 bg-white py-2 pl-10 pr-4 text-base text-brand-text focus:outline-none focus:ring-2 focus:ring-brand-primary dark:border-gray-700 dark:bg-gray-800 dark:text-white sm:text-sm"
            />
          </div>

          {/* Filters */}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setFilter('all')}
              className={`min-h-[44px] flex-1 rounded-lg px-3 py-2 text-xs font-medium transition-colors touch-manipulation sm:flex-none sm:px-3 sm:py-1.5 ${
                filter === 'all'
                  ? 'bg-brand-primary text-white'
                  : 'bg-gray-50 text-brand-text/70 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700'
              }`}
            >
              All
            </button>
            <button
              type="button"
              onClick={() => setFilter('unread')}
              className={`min-h-[44px] flex-1 rounded-lg px-3 py-2 text-xs font-medium transition-colors touch-manipulation sm:flex-none sm:px-3 sm:py-1.5 ${
                filter === 'unread'
                  ? 'bg-brand-primary text-white'
                  : 'bg-gray-50 text-brand-text/70 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700'
              }`}
            >
              Unread
            </button>
            <button
              type="button"
              onClick={() => setFilter('read')}
              className={`min-h-[44px] flex-1 rounded-lg px-3 py-2 text-xs font-medium transition-colors touch-manipulation sm:flex-none sm:px-3 sm:py-1.5 ${
                filter === 'read'
                  ? 'bg-brand-primary text-white'
                  : 'bg-gray-50 text-brand-text/70 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700'
              }`}
            >
              Read
            </button>
          </div>

          {showInboxTechnical ? (
            <label className="mt-2 flex cursor-pointer items-center gap-2 text-[11px] text-amber-900/85 dark:text-amber-200/90">
              <input
                type="checkbox"
                className="rounded border-amber-400 text-amber-700 focus:ring-amber-500 dark:border-amber-600 dark:bg-gray-900"
                checked={showRawSnippets}
                onChange={(e) => setShowRawSnippets(e.target.checked)}
              />
              Show raw snippet source (internal / debug)
            </label>
          ) : null}
        </div>

        {/* Email List */}
        <div className="flex-1 overflow-y-auto">
          {loading && emails.length === 0 ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-brand-primary" />
            </div>
          ) : filteredEmails.length === 0 ? (
            <EmptyState
              icon={Mail}
              title={emails.length === 0 && gmailConnected === true ? "No emails yet" : emails.length === 0 ? "No emails found" : "No emails match your search"}
              description={emails.length === 0 && gmailConnected === true
                ? "Your inbox is empty. New emails will appear here once they arrive."
                : emails.length === 0
                ? "No emails found. Make sure Gmail is connected and synced."
                : "Try adjusting your search or filter criteria."
              }
            />
          ) : (
            <>
              <div className="divide-y divide-gray-200/80 dark:divide-gray-700/80">
                {filteredEmails.map((email: Email) => {
                  const isSelected = selectedEmail?.id === email.id
                  const preview = emailSnippetToCustomerPlainText(email.snippet || '', { maxLen: 140 })
                  return (
                    <button
                      type="button"
                      key={email.id}
                      aria-selected={isSelected}
                      onClick={() => {
                        setSelectedEmail(email)
                        setAiAnalysis(null)
                      }}
                      className={`w-full touch-manipulation text-left transition-colors ${
                        isSelected
                          ? 'border-l-4 border-l-sky-600 bg-sky-50 shadow-[inset_0_0_0_1px_rgba(14,165,233,0.12)] dark:border-l-sky-500 dark:bg-sky-950/45 dark:shadow-[inset_0_0_0_1px_rgba(56,189,248,0.15)]'
                          : 'border-l-4 border-l-transparent hover:bg-gray-50 active:bg-gray-100 dark:hover:bg-gray-800/90 dark:active:bg-gray-800'
                      } px-3 py-2.5 sm:py-3`}
                    >
                      <div className="flex min-h-[44px] items-start gap-2.5">
                        <div
                          className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-slate-200 to-slate-300 text-[10px] font-semibold text-slate-800 shadow-sm dark:from-slate-600 dark:to-slate-700 dark:text-slate-100"
                          aria-hidden
                        >
                          {senderInitials(email.from_name, email.from)}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-baseline justify-between gap-2">
                            <span
                              className={`min-w-0 truncate text-sm ${
                                email.unread
                                  ? 'font-semibold text-gray-900 dark:text-gray-50'
                                  : 'font-medium text-gray-700 dark:text-gray-300'
                              }`}
                            >
                              {email.from_name || email.from}
                            </span>
                            <time
                              className="shrink-0 text-xs tabular-nums text-gray-500 dark:text-gray-500"
                              dateTime={email.date}
                            >
                              {formatInboxListDate(email.date)}
                            </time>
                          </div>
                          <p
                            className={`mt-0.5 line-clamp-2 text-sm leading-snug ${
                              email.unread
                                ? 'text-gray-900 dark:text-gray-100'
                                : 'text-gray-600 dark:text-gray-400'
                            }`}
                          >
                            <span className={email.unread ? 'font-semibold' : 'font-normal'}>
                              {email.subject || '(No subject)'}
                            </span>
                            {preview ? (
                              <span className="font-normal text-gray-500 dark:text-gray-500">
                                {' '}
                                — {preview}
                              </span>
                            ) : null}
                          </p>
                          {showInboxTechnical && showRawSnippets && email.snippet?.trim() ? (
                            <pre
                              className="mt-1 max-h-20 overflow-auto rounded border border-amber-200/80 bg-amber-50/90 p-1.5 text-left font-mono text-[10px] leading-tight text-amber-950 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-100"
                              aria-label="Raw snippet (internal)"
                            >
                              {email.snippet}
                            </pre>
                          ) : null}
                        </div>
                      </div>
                    </button>
                  )
                })}
              </div>
              
              {/* Load More Button */}
              {hasMore && (
                <div className="p-4 border-t border-brand-text/10 dark:border-gray-700">
                  <button
                    type="button"
                    onClick={loadMoreEmails}
                    disabled={loadingMore || isFetching}
                    className="flex min-h-[48px] w-full items-center justify-center gap-2 rounded-lg bg-gray-50 px-4 py-3 text-brand-text transition-colors hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700 touch-manipulation"
                  >
                    {loadingMore || isFetching ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span>Loading more...</span>
                      </>
                    ) : (
                      <span>Load More Emails</span>
                    )}
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Right: message + reply — uses all remaining width above the AI strip */}
      <div
        className={`min-h-0 min-w-0 flex flex-1 flex-col overflow-hidden border-brand-text/10 bg-white dark:border-gray-700 dark:bg-gray-950/40 lg:min-w-0 ${
          hideDetailOnMobile ? 'hidden' : 'flex'
        } lg:flex`}
      >
        {selectedEmail ? (
            <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
              {/* Message header + toolbar */}
              <div className="shrink-0 border-b border-gray-200 bg-white px-3 py-3 sm:px-5 dark:border-gray-700 dark:bg-gray-900/90">
                <div className="flex items-start gap-2">
                  {isNarrowViewport && (
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedEmail(null)
                        setAiAnalysis(null)
                        setShowReplyComposer(false)
                      }}
                      className="mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-brand-text transition-colors hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800 touch-manipulation"
                      aria-label="Back to inbox"
                    >
                      <ChevronLeft className="h-6 w-6" />
                    </button>
                  )}
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-3">
                      <h2 className="break-words text-base font-semibold leading-snug text-gray-900 dark:text-white sm:text-lg">
                        {selectedEmail.subject || '(No subject)'}
                      </h2>
                      <time
                        className="shrink-0 pt-0.5 text-xs tabular-nums text-gray-500 dark:text-gray-400"
                        dateTime={selectedEmail.date}
                      >
                        {new Date(selectedEmail.date).toLocaleString()}
                      </time>
                    </div>
                    <div className="mt-3 flex items-start gap-3">
                      <div
                        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-sky-500 to-indigo-600 text-xs font-semibold text-white shadow-sm"
                        aria-hidden
                      >
                        {senderInitials(selectedEmail.from_name, selectedEmail.from)}
                      </div>
                      <div className="min-w-0 flex-1 pt-0.5">
                        <p className="truncate text-sm font-semibold text-gray-900 dark:text-gray-100">
                          {(selectedEmail.from_name || selectedEmail.from.split('<')[0]).trim() || 'Unknown'}
                        </p>
                        <p className="truncate text-xs text-gray-500 dark:text-gray-400">
                          {selectedEmail.from.includes('<')
                            ? selectedEmail.from.match(/<([^>]+)>/)?.[1] || selectedEmail.from
                            : selectedEmail.from}
                        </p>
                      </div>
                    </div>
                    <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-gray-100 pt-3 dark:border-gray-700/90">
                      <button
                        type="button"
                        onClick={() => analyzeEmail(selectedEmail)}
                        disabled={aiLoading}
                        className="inline-flex min-h-[40px] items-center gap-2 rounded-md bg-brand-primary px-3 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-brand-primary/90 disabled:opacity-50 touch-manipulation"
                      >
                        <Sparkles className="h-4 w-4 shrink-0" />
                        {aiLoading ? 'Analyzing…' : 'AI Analyze'}
                      </button>
                      <button
                        type="button"
                        onClick={() => generateReply(selectedEmail)}
                        disabled={aiLoading}
                        className="inline-flex min-h-[40px] items-center gap-2 rounded-md border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-800 shadow-sm transition-colors hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:hover:bg-gray-700 touch-manipulation"
                      >
                        <Sparkles className="h-4 w-4 shrink-0 text-brand-primary" />
                        Suggest reply
                      </button>
                      <button
                        type="button"
                        onClick={() => handleReply(selectedEmail)}
                        className="inline-flex min-h-[40px] items-center gap-2 rounded-md border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-800 shadow-sm transition-colors hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:hover:bg-gray-700 touch-manipulation"
                      >
                        <Reply className="h-4 w-4 shrink-0" />
                        Reply
                      </button>
                      <button
                        type="button"
                        onClick={() => handleArchive(selectedEmail)}
                        className="inline-flex min-h-[40px] items-center gap-2 rounded-md border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-800 shadow-sm transition-colors hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:hover:bg-gray-700 touch-manipulation"
                      >
                        <Archive className="h-4 w-4 shrink-0" />
                        Archive
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          addToast({ type: 'info', title: 'More options', message: 'Additional options coming soon.' })
                        }}
                        className="inline-flex min-h-[40px] min-w-[40px] items-center justify-center rounded-md border border-gray-200 bg-white p-2 text-gray-600 shadow-sm hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700 touch-manipulation"
                        title="More"
                        aria-label="More actions"
                      >
                        <MoreVertical className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>

            {/* Email Body or Reply Composer */}
            {showReplyComposer ? (
              <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-4 sm:p-6">
                <div className="rounded-lg border border-brand-text/20 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
                  <div className="mb-4">
                    <p className="mb-2 block text-sm font-medium text-brand-text dark:text-white">
                      To: {selectedEmail.from_name || selectedEmail.from}
                    </p>
                    <p className="mb-2 block text-sm font-medium text-brand-text dark:text-white">
                      Subject: {selectedEmail.subject.startsWith('Re:') ? selectedEmail.subject : `Re: ${selectedEmail.subject}`}
                    </p>
                  </div>
                  <textarea
                    aria-label="Reply message"
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    placeholder="Type your reply..."
                    className="min-h-[200px] w-full rounded-lg border border-brand-text/20 bg-white p-3 text-base text-brand-text focus:outline-none focus:ring-2 focus:ring-brand-primary dark:border-gray-700 dark:bg-gray-900 dark:text-white sm:min-h-[16rem] sm:text-sm"
                  />
                  <div className="mt-4 flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => handleSendReply(selectedEmail)}
                      className="flex min-h-[44px] min-w-[44px] flex-1 items-center justify-center gap-2 rounded-lg bg-brand-primary px-4 py-2.5 text-white transition-colors hover:bg-brand-primary/90 sm:flex-initial touch-manipulation"
                    >
                      <Send className="h-4 w-4 shrink-0" />
                      Send
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setShowReplyComposer(false)
                        setReplyText('')
                      }}
                      className="flex min-h-[44px] min-w-[44px] flex-1 items-center justify-center rounded-lg border border-brand-text/20 bg-white px-4 py-2.5 text-brand-text transition-colors hover:bg-brand-background/50 dark:border-gray-700 dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700 sm:flex-initial touch-manipulation"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden overscroll-contain p-4 sm:p-5">
                <div className="mx-auto w-full max-w-full">
                {detailFetching && !displayBody ? (
                  <div className="flex items-center gap-2 text-brand-text/70 dark:text-gray-400 py-8">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    <span>Loading message…</span>
                  </div>
                ) : displayBody ? (
                  <EmailBodyRenderer content={displayBody} emailId={selectedEmail.id} />
                ) : (
                  <div className="text-brand-text/70 dark:text-gray-400">
                    <p className="whitespace-pre-wrap text-[15px] leading-relaxed">
                      {emailSnippetToCustomerPlainText(selectedEmail.snippet || '', {
                        maxLen: 2000,
                        preserveNewlines: true,
                      })}
                    </p>
                    <p className="mt-4 text-sm italic">
                      Full email content not available. Connect Gmail and sync to view complete emails.
                    </p>
                    {showInboxTechnical && showRawSnippets && selectedEmail.snippet?.trim() ? (
                      <details className="mt-4 rounded-lg border border-amber-200/80 bg-amber-50/90 p-3 dark:border-amber-900/50 dark:bg-amber-950/35">
                        <summary className="cursor-pointer text-xs font-medium text-amber-950 dark:text-amber-100">
                          Raw snippet (internal)
                        </summary>
                        <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap break-words font-mono text-[11px] text-amber-950 dark:text-amber-100">
                          {selectedEmail.snippet}
                        </pre>
                      </details>
                    ) : null}
                  </div>
                )}

                {/* Attachments Section */}
                {loadingAttachments ? (
                  <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <div className="flex items-center gap-2 text-sm text-brand-text/70 dark:text-gray-400">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Loading attachments...
                    </div>
                  </div>
                ) : attachments.length > 0 && (
                  <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                    <h3 className="font-semibold text-brand-text dark:text-white mb-3 flex items-center gap-2">
                      <Paperclip className="h-4 w-4" />
                      Attachments ({attachments.length})
                    </h3>
                    {!hasPreviewableAttachment ? (
                      <p className="mb-3 rounded-md border border-dashed border-gray-300 bg-white/80 px-3 py-2 text-xs text-brand-text/75 dark:border-gray-600 dark:bg-gray-900/40 dark:text-gray-300">
                        Inline preview is not available for these file types. Use{' '}
                        <span className="font-medium">Open</span> or <span className="font-medium">Download</span> for
                        each attachment.
                      </p>
                    ) : null}
                    <div className="space-y-2">
                      {attachments.map((att) => {
                        const url = getAttachmentDownloadUrl(att.attachment_id)
                        const previewable = canPreviewAttachment(att.mime_type)
                        const isPreviewSelected = previewAttachmentId === att.attachment_id
                        return (
                          <div
                            key={att.id}
                            className={`rounded-lg border bg-white p-3 transition-colors dark:bg-gray-700 ${
                              isPreviewSelected
                                ? 'border-brand-primary/50'
                                : 'border-gray-200 dark:border-gray-600'
                            }`}
                          >
                            <div className="flex items-start gap-3">
                              <div className="flex-shrink-0 w-10 h-10 bg-brand-primary/10 dark:bg-brand-primary/20 rounded-lg flex items-center justify-center">
                                <Paperclip className="h-5 w-5 text-brand-primary" />
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-brand-text dark:text-white truncate">
                                  {att.filename}
                                </p>
                                <p className="text-xs text-brand-text/60 dark:text-gray-400 break-all">
                                  {att.mime_type || 'unknown'} • {formatBytes(att.size)}
                                </p>
                                {hasPreviewableAttachment && !previewable ? (
                                  <p className="mt-1.5 text-xs text-gray-500 dark:text-gray-400">
                                    Preview not supported for this file type. Use Open or Download.
                                  </p>
                                ) : null}
                              </div>
                              <div className="flex items-center gap-1.5">
                                {previewable ? (
                                  <button
                                    type="button"
                                    onClick={() => setPreviewAttachmentId(att.attachment_id)}
                                    className={`rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors ${
                                      isPreviewSelected
                                        ? 'bg-brand-primary text-white'
                                        : 'bg-brand-primary/10 text-brand-primary hover:bg-brand-primary/20'
                                    }`}
                                  >
                                    Preview
                                  </button>
                                ) : null}
                                <a
                                  href={url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center gap-1 rounded-md border border-gray-200 px-2.5 py-1.5 text-xs font-medium text-brand-text hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-600"
                                >
                                  <ExternalLink className="h-3.5 w-3.5" />
                                  Open
                                </a>
                                <a
                                  href={url}
                                  download={att.filename}
                                  className="inline-flex items-center gap-1 rounded-md border border-gray-200 px-2.5 py-1.5 text-xs font-medium text-brand-text hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-600"
                                >
                                  <Download className="h-3.5 w-3.5" />
                                  Download
                                </a>
                              </div>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                    {selectedPreviewAttachment && (
                      <div className="mt-4 rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-600 dark:bg-gray-700/60">
                        <div className="mb-2 flex items-center gap-2 text-xs text-brand-text/70 dark:text-gray-300">
                          <FileText className="h-3.5 w-3.5" />
                          <span className="truncate">
                            Previewing {selectedPreviewAttachment.filename}
                          </span>
                        </div>
                        {isImageMime(selectedPreviewAttachment.mime_type) ? (
                          <img
                            src={getAttachmentDownloadUrl(selectedPreviewAttachment.attachment_id)}
                            alt={selectedPreviewAttachment.filename}
                            className="max-h-80 w-auto max-w-full rounded border border-gray-200 dark:border-gray-600"
                            loading="lazy"
                          />
                        ) : isAudioMime(selectedPreviewAttachment.mime_type) ? (
                          <audio
                            controls
                            preload="metadata"
                            className="w-full"
                            src={getAttachmentDownloadUrl(selectedPreviewAttachment.attachment_id)}
                          />
                        ) : isVideoMime(selectedPreviewAttachment.mime_type) ? (
                          <video
                            controls
                            preload="metadata"
                            className="max-h-80 w-full rounded border border-gray-200 dark:border-gray-600"
                            src={getAttachmentDownloadUrl(selectedPreviewAttachment.attachment_id)}
                          />
                        ) : isPdfMime(selectedPreviewAttachment.mime_type) ? (
                          <iframe
                            title={selectedPreviewAttachment.filename}
                            className="h-72 w-full rounded border border-gray-200 dark:border-gray-600"
                            src={getAttachmentDownloadUrl(selectedPreviewAttachment.attachment_id)}
                          />
                        ) : (
                          <p className="text-sm text-brand-text/70 dark:text-gray-400">
                            Preview not supported for this file type. Use Open or Download.
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )}
                </div>
              </div>
            )}
            </div>
        ) : (
          <div className="flex min-h-[12rem] flex-1 items-center justify-center p-4">
            <EmptyState
              icon={Mail}
              title="Select an email"
              description="Choose an email from the list to view its contents and use AI assistance."
            />
          </div>
        )}
      </div>
      </div>

      {selectedEmail ? (
        <aside
          className="shrink-0 border-t border-gray-200 bg-gray-50 shadow-[inset_0_1px_0_0_rgba(0,0,0,0.04)] dark:border-gray-700 dark:bg-gray-900/50 dark:shadow-[inset_0_1px_0_0_rgba(255,255,255,0.04)]"
          aria-label="AI analysis"
        >
          <button
            type="button"
            onClick={() => setAiPanelExpanded((e) => !e)}
            className="flex w-full min-h-[48px] items-center justify-between gap-2 border-b border-gray-200/90 bg-gray-100/80 px-3 py-2.5 text-left transition-colors hover:bg-gray-100 dark:border-gray-700 dark:bg-gray-900/80 dark:hover:bg-gray-900/90 sm:px-4"
            aria-expanded={aiPanelExpanded}
            aria-controls="inbox-ai-analysis-panel"
            id="inbox-ai-analysis-toggle"
          >
            <div className="flex min-w-0 items-center gap-2">
              <Sparkles className="h-5 w-5 shrink-0 text-brand-primary" />
              <div className="min-w-0">
                <h4 className="text-sm font-semibold text-brand-text dark:text-white">AI analysis</h4>
                <p className="truncate text-xs text-gray-500 dark:text-gray-400">
                  {aiPanelExpanded
                    ? 'Tap to collapse and give the message more room'
                    : aiLoading
                      ? 'Working…'
                      : hasAiPanelContent(aiAnalysis, false)
                        ? 'Results ready — open to view'
                        : 'Use AI Analyze or Suggest reply in the toolbar above'}
                </p>
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {aiLoading ? (
                <Loader2 className="h-4 w-4 animate-spin text-brand-primary" aria-hidden />
              ) : hasAiPanelContent(aiAnalysis, false) ? (
                <span className="hidden rounded-full bg-emerald-500/15 px-2 py-0.5 text-[11px] font-medium text-emerald-800 dark:text-emerald-300 sm:inline">
                  Ready
                </span>
              ) : null}
              {aiPanelExpanded ? (
                <ChevronDown className="h-5 w-5 shrink-0 text-gray-500 dark:text-gray-400" aria-hidden />
              ) : (
                <ChevronUp className="h-5 w-5 shrink-0 text-gray-500 dark:text-gray-400" aria-hidden />
              )}
            </div>
          </button>

          <div
            id="inbox-ai-analysis-panel"
            role="region"
            aria-labelledby="inbox-ai-analysis-toggle"
            className="grid transition-[grid-template-rows] duration-200 ease-in-out"
            style={{ gridTemplateRows: aiPanelExpanded ? '1fr' : '0fr' }}
          >
            <div className="min-h-0 overflow-hidden">
              <div
                className="max-h-[min(44vh,26rem)] overflow-y-auto overscroll-contain border-t border-transparent px-3 py-3 sm:px-4 sm:py-4 lg:max-h-[min(40vh,24rem)] lg:overflow-x-auto lg:overflow-y-hidden"
                aria-hidden={!aiPanelExpanded}
              >
                <div className="flex min-h-full flex-col gap-4 lg:flex-row lg:gap-6 lg:pr-1">
                  {aiLoading ? (
                    <div className="flex items-center gap-2 text-brand-text/70 dark:text-gray-400">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Analyzing email...</span>
                    </div>
                  ) : aiAnalysis ? (
                    <>
                      {aiAnalysis.summary ? (
                        <div className="min-w-0 shrink-0 lg:max-w-[28%] lg:border-r lg:border-gray-200/80 lg:pr-6 dark:lg:border-gray-700/80">
                          <p className="mb-1 text-sm font-medium text-brand-text dark:text-white">Summary</p>
                          <p className="text-sm text-brand-text/70 dark:text-gray-400">{aiAnalysis.summary}</p>
                        </div>
                      ) : null}

                      <div className="flex min-w-0 flex-1 flex-wrap gap-x-6 gap-y-3 lg:flex-nowrap lg:items-start">
                        {aiAnalysis.intent ? (
                          <div className="min-w-[8rem]">
                            <p className="mb-1 text-sm font-medium text-brand-text dark:text-white">Intent</p>
                            <span className="inline-block rounded bg-brand-primary/10 px-2 py-1 text-xs text-brand-primary">
                              {aiAnalysis.intent}
                            </span>
                          </div>
                        ) : null}

                        {aiAnalysis.urgency ? (
                          <div className="min-w-[8rem]">
                            <p className="mb-1 text-sm font-medium text-brand-text dark:text-white">Urgency</p>
                            <span
                              className={`inline-block rounded px-2 py-1 text-xs ${
                                aiAnalysis.urgency === 'high'
                                  ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                                  : aiAnalysis.urgency === 'medium'
                                    ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                                    : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                              }`}
                            >
                              {aiAnalysis.urgency.toUpperCase()}
                            </span>
                          </div>
                        ) : null}

                        {aiAnalysis.suggested_action ? (
                          <div className="min-w-0 flex-1 basis-[14rem] lg:max-w-md">
                            <p className="mb-1 text-sm font-medium text-brand-text dark:text-white">Suggested action</p>
                            <p className="text-sm text-brand-text/70 dark:text-gray-400">{aiAnalysis.suggested_action}</p>
                          </div>
                        ) : null}

                        {(() => {
                          if (!aiAnalysis.contact_info) return null
                          const entries = [
                            { label: 'Phone', value: aiAnalysis.contact_info?.phone },
                            { label: 'Company', value: aiAnalysis.contact_info?.company },
                            { label: 'Website', value: aiAnalysis.contact_info?.website },
                            { label: 'Location', value: aiAnalysis.contact_info?.location },
                            { label: 'Budget', value: aiAnalysis.contact_info?.budget },
                            { label: 'Timeline', value: aiAnalysis.contact_info?.timeline },
                          ].filter((entry) => entry.value)
                          if (entries.length === 0) return null
                          return (
                            <div className="min-w-0 flex-1 basis-[16rem] lg:max-w-sm">
                              <p className="mb-2 text-sm font-medium text-brand-text dark:text-white">Contact info</p>
                              <div className="grid grid-cols-1 gap-2 text-sm text-brand-text/70 dark:text-gray-400 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
                                {entries.map((entry) => (
                                  <div key={entry.label} className="flex gap-2">
                                    <span className="font-medium text-brand-text dark:text-white">{entry.label}:</span>
                                    <span className="truncate">{entry.value}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )
                        })()}
                      </div>

                      {aiAnalysis.suggested_reply ? (
                        <div className="min-w-0 shrink-0 border-t border-gray-200/90 pt-3 dark:border-gray-700 lg:min-w-[min(24rem,28vw)] lg:border-l lg:border-t-0 lg:pl-6 lg:pt-0">
                          <div className="rounded-lg border border-brand-text/20 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
                            <p className="mb-2 text-sm font-medium text-brand-text dark:text-white">Suggested reply</p>
                            <div className="mb-3 whitespace-pre-wrap text-sm text-brand-text/80 dark:text-gray-300">
                              {aiAnalysis.suggested_reply}
                            </div>
                            <button
                              type="button"
                              onClick={handleUseSuggestedReply}
                              className="min-h-[44px] rounded-lg bg-brand-primary px-4 py-2.5 text-sm text-white transition-colors hover:bg-brand-primary/90 touch-manipulation"
                            >
                              Use this reply
                            </button>
                          </div>
                        </div>
                      ) : null}
                    </>
                  ) : (
                    <div className="text-sm text-brand-text/60 dark:text-gray-500">
                      Use <span className="font-medium text-brand-text/80 dark:text-gray-300">AI Analyze</span> or{' '}
                      <span className="font-medium text-brand-text/80 dark:text-gray-300">Suggest reply</span> in the
                      toolbar above.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </aside>
      ) : null}
    </div>
  )
}
