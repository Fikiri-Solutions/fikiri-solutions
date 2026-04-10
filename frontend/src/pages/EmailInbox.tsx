import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Mail, Search, Sparkles, Send, Reply, Archive, MoreVertical, Loader2, RefreshCw, Paperclip, Download, Activity, ChevronLeft } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../contexts/AuthContext'
import { apiClient } from '../services/apiClient'
import { useToast } from '../components/Toast'
import { EmptyState } from '../components/EmptyState'
import DOMPurify from 'dompurify'

interface Attachment {
  id: number
  attachment_id: string
  filename: string
  mime_type: string
  size: number
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

// Component to safely render email body (HTML or plain text)
const EmailBodyRenderer: React.FC<{ content: string; emailId?: string }> = ({ content, emailId }) => {
  const containerRef = React.useRef<HTMLDivElement>(null)
  
  // Check if content is HTML (contains HTML tags)
  const isHTML = /<[a-z][\s\S]*>/i.test(content)
  
  // Handle image loading errors after render
  React.useEffect(() => {
    if (!containerRef.current || !isHTML) return
    
    const images = containerRef.current.querySelectorAll('img')
    const handleImageError = (e: Event) => {
      const img = e.target as HTMLImageElement
      const originalSrc = img.getAttribute('src') || img.src
      console.warn('Image failed to load:', originalSrc, 'Error:', e)
      
      // Try to proxy external images if they're failing due to CORS
      if (originalSrc.startsWith('http://') || originalSrc.startsWith('https://')) {
        // Don't retry if we already tried proxying
        if (!img.dataset.proxyAttempted) {
          img.dataset.proxyAttempted = 'true'
          // Could proxy through backend, but for now just hide
          img.style.display = 'none'
          const placeholder = document.createElement('div')
          placeholder.className = 'inline-block px-2 py-1 bg-gray-100 dark:bg-gray-800 text-xs text-gray-500 dark:text-gray-400 rounded my-2'
          placeholder.textContent = '[Image not available - external image blocked]'
          img.parentNode?.insertBefore(placeholder, img)
          return
        }
      }
      
      // Hide broken images
      img.style.display = 'none'
      // Add a placeholder
      if (!img.parentElement?.querySelector('.image-placeholder')) {
        const placeholder = document.createElement('div')
        placeholder.className = 'image-placeholder inline-block px-2 py-1 bg-gray-100 dark:bg-gray-800 text-xs text-gray-500 dark:text-gray-400 rounded my-2'
        placeholder.textContent = '[Image not available]'
        img.parentNode?.insertBefore(placeholder, img)
      }
    }
    
    images.forEach(img => {
      img.addEventListener('error', handleImageError)
      // Add loading="lazy" + async decode so layout/paint isn't blocked on many images
      if (!img.hasAttribute('loading')) {
        img.setAttribute('loading', 'lazy')
      }
      if (!img.hasAttribute('decoding')) {
        img.setAttribute('decoding', 'async')
      }
      // Only add crossorigin for external images (not our proxy)
      const isExternalImage = img.src.startsWith('http://') || img.src.startsWith('https://')
      const isOurProxy = img.src.includes('/api/business/email/') || img.src.includes('/embedded-image/')
      if (isExternalImage && !isOurProxy && !img.hasAttribute('crossorigin')) {
        img.setAttribute('crossorigin', 'anonymous')
      }
      // Remove crossorigin from our proxy images (not needed and can cause issues)
      if (isOurProxy && img.hasAttribute('crossorigin')) {
        img.removeAttribute('crossorigin')
      }
      // Ensure proxy URLs are absolute
      if (img.src.startsWith('/api/business/email/') && emailId) {
        const baseUrl = window.location.origin
        if (!img.src.startsWith(baseUrl)) {
          img.src = baseUrl + img.src
        }
      }
      // Handle relative URLs that should be absolute
      if (img.src.startsWith('/api/') && !img.src.startsWith(window.location.origin)) {
        img.src = window.location.origin + img.src
      }
      // Try to fix broken src attributes
      const imgSrc = img.getAttribute('src') || img.src
      if (!imgSrc || imgSrc === 'undefined' || imgSrc === 'null' || imgSrc === '') {
        console.warn('Image has invalid src:', imgSrc)
        img.style.display = 'none'
      }
    })
    
    return () => {
      images.forEach(img => {
        img.removeEventListener('error', handleImageError)
      })
    }
  }, [content, emailId, isHTML])
  
  if (isHTML) {
    // Process HTML to handle images properly
    let processedHTML = content
    
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
        'img', 'table', 'thead', 'tbody', 'tr', 'td', 'th',
        'blockquote', 'pre', 'code', 'hr', 'style'
      ],
      ALLOWED_ATTR: [
        'href', 'title', 'alt', 'src', 'width', 'height', 'style',
        'class', 'id', 'align', 'colspan', 'rowspan', 'loading'
      ],
      // Allow http/https, data:, cid:, and relative paths (e.g. /api/business/email/.../embedded-image/...)
      ALLOWED_URI_REGEXP: /^(?:(?:(?:f|ht)tps?|mailto|tel|callto|sms|cid|xmpp|data|blob):|\/)/i,
      ALLOW_UNKNOWN_PROTOCOLS: true,
      ALLOW_DATA_ATTR: true,
      KEEP_CONTENT: true,
      ADD_ATTR: ['target', 'rel'],
      ADD_TAGS: []
    })
    
    return (
      <>
        <style>{`
          .email-body-html {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            font-size: 14px;
          }
          @media (max-width: 767px) {
            .email-body-html {
              font-size: 16px;
            }
          }
          .email-body-html img {
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            margin: 8px 0;
            display: block;
            object-fit: contain;
          }
          .email-body-html img[src^="http"] {
            /* Allow external images - browser will handle CORS */
            image-rendering: auto;
          }
          .email-body-html img[loading="lazy"] {
            /* Lazy load images */
            content-visibility: auto;
          }
          .email-body-html img[src^="/api/business/email"] {
            /* Embedded images from our proxy */
            image-rendering: auto;
          }
          /* Handle broken images */
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
          .email-body-html table {
            width: 100%;
            border-collapse: collapse;
            margin: 12px 0;
          }
          .email-body-html table td,
          .email-body-html table th {
            padding: 8px;
            border: 1px solid rgba(0, 0, 0, 0.1);
          }
          .dark .email-body-html table td,
          .dark .email-body-html table th {
            border-color: rgba(255, 255, 255, 0.12);
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
        `}</style>
        <div 
          ref={containerRef}
          className="email-body-html prose dark:prose-invert max-w-none text-brand-text dark:text-white"
          dangerouslySetInnerHTML={{ __html: sanitizedHTML }}
        />
      </>
    )
  } else {
    // Plain text - preserve whitespace
    return (
      <div className="whitespace-pre-wrap text-brand-text dark:text-white font-sans text-sm leading-relaxed">
        {content}
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

export const EmailInbox: React.FC = () => {
  const { user } = useAuth()
  const { addToast } = useToast()
  const queryClient = useQueryClient()
  const [selectedEmail, setSelectedEmail] = useState<Email | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiAnalysis, setAiAnalysis] = useState<AIAnalysis | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filter, setFilter] = useState<'all' | 'unread' | 'read'>('all')
  const [replyText, setReplyText] = useState('')
  const [showReplyComposer, setShowReplyComposer] = useState(false)
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [loadingAttachments, setLoadingAttachments] = useState(false)
  const [emailLimit, setEmailLimit] = useState(25) // Start with 25 emails
  const [loadingMore, setLoadingMore] = useState(false)
  const [syncInboxPending, setSyncInboxPending] = useState(false)
  const [isNarrowViewport, setIsNarrowViewport] = useState(false)

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
    setEmailLimit(25)
  }, [filter])

  // Load attachments when email is selected
  useEffect(() => {
    if (selectedEmail?.id) {
      loadAttachments(selectedEmail.id)
    } else {
      setAttachments([])
    }
  }, [selectedEmail?.id])

  const loadAttachments = async (emailId: string) => {
    setLoadingAttachments(true)
    try {
      const attachments = await apiClient.getEmailAttachments(emailId)
      if (attachments && Array.isArray(attachments)) {
        setAttachments(attachments)
      } else {
        setAttachments([])
      }
    } catch (error) {
      console.error('Failed to load attachments:', error)
      setAttachments([])
    } finally {
      setLoadingAttachments(false)
    }
  }

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
      // Try synced emails first (faster), fallback to Gmail API
      try {
        // First try synced emails
        const syncedData = await apiClient.getEmails({
          filter,
          limit: emailLimit,
          use_synced: true,
          include_body: false
        })
        if (syncedData?.emails && syncedData.emails.length > 0) {
          return { ...syncedData, source: 'synced' }
        }
      } catch (e) {
        // Fallback to Gmail API if synced fails
      }
      
      // Fallback to Gmail API
      const data = await apiClient.getEmails({ filter, limit: emailLimit, include_body: false })
      return { ...data, source: 'gmail_api' }
    },
    enabled: !!user && gmailConnected === true,
    staleTime: 1 * 60 * 1000, // 1 minute - emails are fresh for 1 minute
    gcTime: 15 * 60 * 1000, // 15 minutes - keep in cache for 15 minutes
    refetchInterval: 2 * 60 * 1000, // Auto-refresh every 2 minutes
    refetchOnWindowFocus: false, // Don't refetch on focus
    refetchOnMount: false, // Use cached data if available
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
      setTimeout(() => refetchEmails(), 2000)
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
        setAiAnalysis(prev => ({ ...prev, suggested_reply: reply }))
        setReplyText(reply)
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
      const matchesSearch = !searchQuery || 
        email.subject.toLowerCase().includes(searchLower) ||
        email.from.toLowerCase().includes(searchLower) ||
        email.snippet.toLowerCase().includes(searchLower)
      
      const matchesFilter = filter === 'all' || 
        (filter === 'unread' && email.unread) ||
        (filter === 'read' && !email.unread)
      
      return matchesSearch && matchesFilter
    })
  }, [emails, searchQuery, filter])

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
      {/* Email List Sidebar */}
      <div
        className={`min-h-0 w-full flex flex-col border-brand-text/10 dark:border-gray-700 lg:w-1/3 lg:border-r ${
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
              <div className="divide-y divide-brand-text/10 dark:divide-gray-700">
                {filteredEmails.map((email: Email) => (
                  <button
                    type="button"
                    key={email.id}
                    onClick={() => {
                      setSelectedEmail(email)
                      setAiAnalysis(null)
                    }}
                    className={`w-full touch-manipulation text-left p-4 transition-colors hover:bg-gray-50 active:bg-gray-100 dark:hover:bg-gray-800 dark:active:bg-gray-700/80 ${
                      selectedEmail?.id === email.id ? 'bg-brand-primary/10 dark:bg-brand-primary/20 border-l-4 border-brand-primary' : ''
                    } ${email.unread ? 'font-semibold' : ''}`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm truncate ${email.unread ? 'text-brand-text dark:text-white font-semibold' : 'text-brand-text/80 dark:text-gray-300'}`}>
                          {email.from_name || email.from}
                        </p>
                        <p className={`text-xs mt-1 truncate ${email.unread ? 'text-brand-text dark:text-white' : 'text-brand-text/60 dark:text-gray-400'}`}>
                          {email.subject || '(No subject)'}
                        </p>
                      </div>
                      {email.unread && (
                        <div className="ml-2 h-2 w-2 rounded-full bg-brand-primary flex-shrink-0 mt-1.5" />
                      )}
                    </div>
                    <p className="text-xs text-brand-text/60 dark:text-gray-500 line-clamp-2 mt-1">
                      {email.snippet}
                    </p>
                    <p className="text-xs text-brand-text/50 dark:text-gray-600 mt-2">
                      {new Date(email.date).toLocaleDateString()}
                    </p>
                  </button>
                ))}
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

      {/* Email View & AI Assistant */}
      <div
        className={`min-h-0 min-w-0 flex flex-1 flex-col overflow-hidden ${
          hideDetailOnMobile ? 'hidden' : 'flex'
        } lg:flex`}
      >
        {selectedEmail ? (
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            {/* Email Header */}
            <div className="shrink-0 border-b border-brand-text/10 p-4 sm:p-6 dark:border-gray-700">
              <div className="mb-4 flex items-start justify-between gap-2">
                <div className="flex min-w-0 flex-1 items-start gap-2 sm:gap-3">
                  {isNarrowViewport && (
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedEmail(null)
                        setAiAnalysis(null)
                        setShowReplyComposer(false)
                      }}
                      className="mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-brand-text transition-colors hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700 touch-manipulation"
                      aria-label="Back to inbox"
                    >
                      <ChevronLeft className="h-6 w-6" />
                    </button>
                  )}
                  <div className="min-w-0 flex-1">
                    <h3 className="mb-2 break-words text-lg font-bold text-brand-text dark:text-white sm:text-xl">
                      {selectedEmail.subject || '(No subject)'}
                    </h3>
                    <div className="flex flex-col gap-2 text-sm text-brand-text/70 dark:text-gray-400 sm:flex-row sm:flex-wrap sm:gap-x-4 sm:gap-y-1">
                      <div className="min-w-0 break-words">
                        <span className="font-medium">From:</span>{' '}
                        {selectedEmail.from_name || selectedEmail.from}
                      </div>
                      <div className="shrink-0">
                        <span className="font-medium">Date:</span>{' '}
                        {new Date(selectedEmail.date).toLocaleString()}
                      </div>
                    </div>
                  </div>
                </div>
                <div className="flex shrink-0 gap-1 sm:gap-2">
                  <button
                    type="button"
                    onClick={() => generateReply(selectedEmail)}
                    disabled={aiLoading}
                    className="flex h-11 w-11 items-center justify-center rounded-lg transition-colors hover:bg-gray-50 disabled:opacity-50 dark:hover:bg-gray-800 touch-manipulation"
                    title="Generate AI Reply"
                    aria-label="Generate AI reply"
                  >
                    <Sparkles className={`h-5 w-5 text-brand-primary ${aiLoading ? 'animate-pulse' : ''}`} />
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      addToast({ type: 'info', title: 'More options', message: 'Additional options coming soon.' })
                    }}
                    className="flex h-11 w-11 items-center justify-center rounded-lg transition-colors hover:bg-gray-50 dark:hover:bg-gray-800 touch-manipulation"
                    title="More options"
                    aria-label="More options"
                  >
                    <MoreVertical className="h-5 w-5 text-brand-text/70 dark:text-gray-400" />
                  </button>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => analyzeEmail(selectedEmail)}
                  disabled={aiLoading}
                  className="flex min-h-[44px] min-w-[44px] flex-1 items-center justify-center gap-2 rounded-lg bg-brand-primary px-4 py-2.5 text-white transition-colors hover:bg-brand-primary/90 disabled:opacity-50 sm:flex-initial touch-manipulation"
                >
                  <Sparkles className="h-4 w-4 shrink-0" />
                  {aiLoading ? 'Analyzing...' : 'AI Analyze'}
                </button>
                <button
                  type="button"
                  onClick={() => handleReply(selectedEmail)}
                  className="flex min-h-[44px] min-w-[44px] flex-1 items-center justify-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-brand-text transition-colors hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700 sm:flex-initial touch-manipulation"
                >
                  <Reply className="h-4 w-4 shrink-0" />
                  Reply
                </button>
                <button
                  type="button"
                  onClick={() => handleArchive(selectedEmail)}
                  className="flex min-h-[44px] min-w-[44px] flex-1 items-center justify-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-brand-text transition-colors hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700 sm:flex-initial touch-manipulation"
                >
                  <Archive className="h-4 w-4 shrink-0" />
                  Archive
                </button>
              </div>
            </div>

            {/* Email Body or Reply Composer */}
            {showReplyComposer ? (
              <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-4 sm:p-6">
                <div className="rounded-lg border border-brand-text/20 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
                  <div className="mb-4">
                    <label className="mb-2 block text-sm font-medium text-brand-text dark:text-white">
                      To: {selectedEmail.from_name || selectedEmail.from}
                    </label>
                    <label className="mb-2 block text-sm font-medium text-brand-text dark:text-white">
                      Subject: {selectedEmail.subject.startsWith('Re:') ? selectedEmail.subject : `Re: ${selectedEmail.subject}`}
                    </label>
                  </div>
                  <textarea
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
              <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden overscroll-contain p-4 sm:p-6">
                {detailFetching && !displayBody ? (
                  <div className="flex items-center gap-2 text-brand-text/70 dark:text-gray-400 py-8">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    <span>Loading message…</span>
                  </div>
                ) : displayBody ? (
                  <EmailBodyRenderer content={displayBody} emailId={selectedEmail.id} />
                ) : (
                  <div className="text-brand-text/70 dark:text-gray-400">
                    {selectedEmail.snippet}
                    <p className="mt-4 text-sm italic">
                      Full email content not available. Connect Gmail and sync to view complete emails.
                    </p>
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
                    <div className="space-y-2">
                      {attachments.map((att) => (
                        <a
                          key={att.id}
                          href={`/api/email/${selectedEmail.id}/attachments/${att.attachment_id}/download`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-3 p-3 bg-white dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg border border-gray-200 dark:border-gray-600 transition-colors group"
                        >
                          <div className="flex-shrink-0 w-10 h-10 bg-brand-primary/10 dark:bg-brand-primary/20 rounded-lg flex items-center justify-center">
                            <Paperclip className="h-5 w-5 text-brand-primary" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-brand-text dark:text-white truncate">
                              {att.filename}
                            </p>
                            <p className="text-xs text-brand-text/60 dark:text-gray-400">
                              {att.mime_type} • {formatBytes(att.size)}
                            </p>
                          </div>
                          <Download className="h-4 w-4 text-brand-text/50 dark:text-gray-400 group-hover:text-brand-primary transition-colors" />
                        </a>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* AI Assistant Panel */}
            <div className="shrink-0 border-t border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800/50 sm:p-6">
              <div className="flex items-center gap-2 mb-4">
                <Sparkles className="h-5 w-5 text-brand-primary" />
                <h4 className="font-semibold text-brand-text dark:text-white">AI Assistant</h4>
              </div>

              {aiLoading ? (
                <div className="flex items-center gap-2 text-brand-text/70 dark:text-gray-400">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Analyzing email...</span>
                </div>
              ) : aiAnalysis ? (
                <div className="space-y-4">
                  {aiAnalysis.summary && (
                    <div>
                      <p className="text-sm font-medium text-brand-text dark:text-white mb-1">Summary</p>
                      <p className="text-sm text-brand-text/70 dark:text-gray-400">{aiAnalysis.summary}</p>
                    </div>
                  )}
                  
                  {aiAnalysis.intent && (
                    <div>
                      <p className="text-sm font-medium text-brand-text dark:text-white mb-1">Intent</p>
                      <span className="inline-block px-2 py-1 bg-brand-primary/10 text-brand-primary rounded text-xs">
                        {aiAnalysis.intent}
                      </span>
                    </div>
                  )}

                  {aiAnalysis.urgency && (
                    <div>
                      <p className="text-sm font-medium text-brand-text dark:text-white mb-1">Urgency</p>
                      <span className={`inline-block px-2 py-1 rounded text-xs ${
                        aiAnalysis.urgency === 'high' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' :
                        aiAnalysis.urgency === 'medium' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' :
                        'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      }`}>
                        {aiAnalysis.urgency.toUpperCase()}
                      </span>
                    </div>
                  )}

                  {aiAnalysis.suggested_action && (
                    <div>
                      <p className="text-sm font-medium text-brand-text dark:text-white mb-1">Suggested Action</p>
                      <p className="text-sm text-brand-text/70 dark:text-gray-400">{aiAnalysis.suggested_action}</p>
                    </div>
                  )}

                  {aiAnalysis.contact_info && (
                    (() => {
                      const entries = [
                        { label: 'Phone', value: aiAnalysis.contact_info?.phone },
                        { label: 'Company', value: aiAnalysis.contact_info?.company },
                        { label: 'Website', value: aiAnalysis.contact_info?.website },
                        { label: 'Location', value: aiAnalysis.contact_info?.location },
                        { label: 'Budget', value: aiAnalysis.contact_info?.budget },
                        { label: 'Timeline', value: aiAnalysis.contact_info?.timeline }
                      ].filter(entry => entry.value)

                      if (entries.length === 0) return null

                      return (
                        <div>
                          <p className="text-sm font-medium text-brand-text dark:text-white mb-2">Extracted Contact Info</p>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm text-brand-text/70 dark:text-gray-400">
                            {entries.map(entry => (
                              <div key={entry.label} className="flex gap-2">
                                <span className="font-medium text-brand-text dark:text-white">{entry.label}:</span>
                                <span className="truncate">{entry.value}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )
                    })()
                  )}

                  {aiAnalysis.suggested_reply && (
                    <div className="mt-4 p-4 bg-white dark:bg-gray-800 border border-brand-text/20 dark:border-gray-700 rounded-lg">
                      <p className="text-sm font-medium text-brand-text dark:text-white mb-2">Suggested Reply</p>
                      <div className="text-sm text-brand-text/80 dark:text-gray-300 whitespace-pre-wrap mb-3">
                        {aiAnalysis.suggested_reply}
                      </div>
                      <button
                        type="button"
                        onClick={handleUseSuggestedReply}
                        className="min-h-[44px] rounded-lg bg-brand-primary px-4 py-2.5 text-sm text-white transition-colors hover:bg-brand-primary/90 touch-manipulation"
                      >
                        Use This Reply
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-sm text-brand-text/60 dark:text-gray-500">
                  Click "AI Analyze" to get insights about this email, or "Generate AI Reply" to create a suggested response.
                </div>
              )}
            </div>
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
  )
}
