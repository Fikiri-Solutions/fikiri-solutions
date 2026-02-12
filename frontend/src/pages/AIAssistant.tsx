import React, { useState, useEffect, useRef } from 'react'
import { Brain, Send, Bot, User, Clock, Zap, Mail, Users, Wifi, WifiOff, Inbox, MessageSquare, Sparkles, Loader2, RefreshCw } from 'lucide-react'
import { apiClient, AIResponse, LeadData } from '../services/apiClient'
import { StatusIcon } from '../components/StatusIcon'
import { EmptyState } from '../components/EmptyState'
import { useWebSocket } from '../hooks/useWebSocket'
import { useToast } from '../components/Toast'

interface ChatMessage {
  id: string
  type: 'user' | 'ai'
  content: string
  timestamp: Date
  isTyping?: boolean
  // Classification removed to prevent debug metadata display
}

// Fallback responses for when backend is not available
const getFallbackResponse = (message: string): string => {
  const lowerMessage = message.toLowerCase()
  
  if (lowerMessage.includes('contact') || lowerMessage.includes('email') || lowerMessage.includes('phone')) {
    return 'You can contact Fikiri Solutions at:\n\n📧 Email: info@fikirisolutions.com\n🌐 Website: https://fikirisolutions.com\n📞 Phone: Available through our contact form\n\nWe specialize in AI-powered business automation for landscaping, restaurants, and medical practices.'
  }
  
  if (lowerMessage.includes('price') || lowerMessage.includes('cost') || lowerMessage.includes('pricing')) {
    return 'Our pricing varies based on your specific needs:\n\n• **Starter Plan**: $39/month - Basic email automation\n• **Growth Plan**: $79/month - Advanced CRM + automation\n• **Business Plan**: $199/month - White-label options\n• **Enterprise Plan**: $399/month - Custom solutions\n\nContact us for a personalized quote based on your industry and requirements.'
  }
  
  if (lowerMessage.includes('service') || lowerMessage.includes('what do you do')) {
    return 'Fikiri Solutions provides AI-powered business automation:\n\n🏢 **Email Automation**: Smart email responses and workflows\n📊 **CRM Management**: Lead tracking and analysis\n🤖 **AI Assistant**: Intelligent business support\n🏭 **Industry Solutions**: Specialized for landscaping, restaurants, and medical practices\n\nWe help businesses streamline operations and increase efficiency.'
  }
  
  if (lowerMessage.includes('help') || lowerMessage.includes('assist')) {
    return 'I can help you with:\n\n• Email automation setup\n• Lead analysis and prioritization\n• CRM configuration\n• Business process optimization\n• Industry-specific solutions\n\nWhat specific area would you like assistance with?'
  }
  
  return 'I\'m here to help with Fikiri Solutions\' services including email automation, CRM management, and business process optimization. Could you please provide more details about what you\'d like assistance with?'
}

// Function to format AI responses with better spacing and structure
const formatAIResponse = (content: string): string => {
  return content
    .replace(/\n\n/g, '\n\n') // Ensure proper paragraph spacing
    .replace(/\*\*(.*?)\*\*/g, '**$1**') // Preserve bold formatting
    .replace(/• /g, '• ') // Ensure consistent bullet points
    .replace(/([.!?])\s*([A-Z])/g, '$1\n\n$2') // Add spacing after sentences
    .replace(/\n{3,}/g, '\n\n') // Limit to max 2 newlines
}

// Function to simulate typing effect
const simulateTyping = async (text: string, onUpdate: (text: string) => void, speed: number = 30) => {
  let currentText = ''
  const words = text.split(' ')
  
  for (let i = 0; i < words.length; i++) {
    currentText += (i > 0 ? ' ' : '') + words[i]
    onUpdate(currentText)
    await new Promise(resolve => setTimeout(resolve, speed))
  }
}

export const AIAssistant: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [aiStatus, setAiStatus] = useState<AIResponse | null>(null)
  const [isTyping, setIsTyping] = useState(false)
  const [leadInbox, setLeadInbox] = useState<LeadData[]>([])
  const [selectedLead, setSelectedLead] = useState<LeadData | null>(null)
  const [inboxLoading, setInboxLoading] = useState(false)
  const [suggestedReply, setSuggestedReply] = useState('')
  const [suggestionLoading, setSuggestionLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { isConnected } = useWebSocket()
  const { addToast } = useToast()

  useEffect(() => {
    fetchAIStatus()
    // Add welcome message
    setMessages([{
      id: '1',
      type: 'ai',
      content: 'Hello! I\'m your Fikiri Solutions AI Assistant. I can help you with email automation, lead analysis, CRM management, and business process optimization. I have knowledge about our services including industry-specific automation for landscaping, restaurants, and medical practices. How can I assist you today?',
      timestamp: new Date()
    }])
  }, [])

  const loadLeadInbox = async () => {
    setInboxLoading(true)
    try {
      const leads = await apiClient.getLeads()
      setLeadInbox(leads)
      setSelectedLead(leads[0] ?? null)
    } catch (err) {
      addToast({ type: 'error', title: 'Load Failed', message: 'Unable to load AI inbox. Using cached data.' })
    } finally {
      setInboxLoading(false)
    }
  }

  useEffect(() => {
    loadLeadInbox()
  }, [])  

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const fetchAIStatus = async () => {
    try {
      const status = await apiClient.testAIAssistant()
      setAiStatus(status)
    } catch (error) {
      // Failed to fetch AI status
    }
  }

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: inputMessage.trim(),
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsLoading(true)
    setError(null)

    // Create a placeholder AI message for typing effect
    const aiMessageId = (Date.now() + 1).toString()
    const placeholderMessage: ChatMessage = {
      id: aiMessageId,
      type: 'ai',
      content: '',
      timestamp: new Date(),
      isTyping: true
    }

    setMessages(prev => [...prev, placeholderMessage])

    try {
      // Call the real AI API
      const response = await apiClient.sendChatMessage(inputMessage.trim(), {
        conversation_history: messages.slice(-6) // Last 6 messages for context
      })
      
      // sendChatMessage already unwraps the response, so access response.response directly
      const rawResponse = response?.response || response?.data?.response || 'I apologize, but I encountered an issue generating a response.'
      const formattedResponse = formatAIResponse(rawResponse)

      // Simulate typing effect by updating the existing placeholder message
      await simulateTyping(formattedResponse, (currentText) => {
        setMessages(prev => prev.map(msg => 
          msg.id === aiMessageId 
            ? { ...msg, content: currentText, isTyping: false }
            : msg
        ))
      }, 25) // 25ms per word for natural typing speed

    } catch (error) {
      // Failed to send message - provide helpful fallback response
      const fallbackResponse = getFallbackResponse(inputMessage.trim())
      const formattedFallback = formatAIResponse(fallbackResponse)
      
      // Simulate typing effect for fallback response
      await simulateTyping(formattedFallback, (currentText) => {
        setMessages(prev => prev.map(msg => 
          msg.id === aiMessageId 
            ? { ...msg, content: currentText, isTyping: false }
            : msg
        ))
      }, 25)
      
      setError(null) // Clear error since we provided a fallback
    } finally {
      setIsLoading(false)
    }
  }

  const handleSelectLead = (lead: LeadData) => {
    setSelectedLead(lead)
    setSuggestedReply('')
  }

  const buildReplyPrompt = (lead: LeadData) => {
    return `You are Fikiri Solutions' AI email assistant. Write a concise, friendly reply to ${lead.name} (${lead.email}) who is interested in our services. 
Lead context:
- Score: ${lead.score}
- Stage: ${lead.stage}
- Source: ${lead.source}
Response should include a next step and keep tone professional but warm.`
  }

  const handleGenerateReply = async () => {
    if (!selectedLead) return
    setSuggestionLoading(true)
    try {
      const response = await apiClient.sendChatMessage(buildReplyPrompt(selectedLead))
      // sendChatMessage already unwraps the response, so access response.response directly
      const text = response?.response || response?.data?.response || 'Unable to generate a reply right now.'
      setSuggestedReply(text)
      addToast({ type: 'success', title: 'Reply Drafted', message: 'Suggested reply drafted' })
    } catch (err) {
      addToast({ type: 'error', title: 'Generation Failed', message: 'Failed to generate reply. Try again.' })
    } finally {
      setSuggestionLoading(false)
    }
  }

  const handleSendReply = async () => {
    if (!suggestedReply) {
      addToast({ type: 'warning', title: 'No Reply', message: 'Generate or edit a reply before sending.' })
      return
    }
    if (!selectedLead) {
      addToast({ type: 'warning', title: 'No Lead Selected', message: 'Please select a lead to send an email to.' })
      return
    }

    try {
      setIsLoading(true)
      const result = await apiClient.sendEmail({
        to: selectedLead.email,
        subject: `Re: Inquiry from ${selectedLead.name}`,
        body: suggestedReply
      })
      
      addToast({ type: 'success', title: 'Email Sent', message: 'Email sent successfully!' })
      setSuggestedReply('') // Clear the reply after sending
      
      // Optionally refresh the lead inbox
      loadLeadInbox()
    } catch (error: any) {
      const errorMessage = error?.response?.data?.error || error?.message || 'Failed to send email'
      addToast({ type: 'error', title: 'Send Failed', message: errorMessage })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-brand-text dark:text-white">AI Assistant</h1>
          <p className="mt-1 text-sm text-brand-text/70 dark:text-gray-400">
            Get intelligent help with email responses, lead analysis, and business automation.
          </p>
        </div>
        
        {/* AI Status & Connection */}
        <div className="flex items-center space-x-4">
          {/* Real-time Connection Status */}
          <div className="flex items-center space-x-2">
            {isConnected ? (
              <Wifi className="h-4 w-4 text-green-500" />
            ) : (
              <WifiOff className="h-4 w-4 text-red-500" />
            )}
            <span className={`text-sm font-medium ${
              isConnected ? 'text-green-600' : 'text-red-600'
            }`}>
              {isConnected ? 'Real-time Connected' : 'Offline Mode'}
            </span>
          </div>
          
          {/* AI Status */}
          {aiStatus && (
            <div className="flex items-center space-x-2">
              <StatusIcon 
                status={aiStatus.stats.enabled ? 'active' : 'inactive'} 
                size="md" 
              />
              <span className={`text-sm font-medium ${
                aiStatus.stats.enabled ? 'text-green-600' : 'text-gray-600'
              }`}>
                {aiStatus.stats.enabled ? 'AI Active' : 'AI Inactive'}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-600">
            <strong>Error:</strong> {error}
          </p>
        </div>
      )}


      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Lead Inbox */}
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-xs uppercase tracking-wide text-brand-text/60 dark:text-gray-400">Lead inbox</p>
              <h2 className="text-xl font-semibold text-brand-text dark:text-white">Classified by AI</h2>
            </div>
            <button
              onClick={loadLeadInbox}
              className="text-sm text-brand-primary hover:text-brand-secondary inline-flex items-center gap-2"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
          </div>
          <div className="space-y-3 max-h-[520px] overflow-y-auto pr-1">
            {inboxLoading ? (
              <div className="flex items-center justify-center py-12 text-brand-text/60">
                <Loader2 className="h-5 w-5 animate-spin mr-2" />
                Loading inbox…
              </div>
            ) : leadInbox.length === 0 ? (
              <EmptyState
                icon={Inbox}
                title="No leads yet"
                description="Connect Gmail or forms to start capturing leads automatically."
              />
            ) : (
              leadInbox.map((lead) => {
                const sentiment =
                  lead.score >= 7 ? { label: 'Hot', classes: 'bg-red-100 text-red-700' } :
                  lead.score >= 4 ? { label: 'Warm', classes: 'bg-amber-100 text-amber-700' } :
                  { label: 'Cold', classes: 'bg-blue-100 text-blue-700' }

                return (
                  <button
                    key={lead.id}
                    onClick={() => handleSelectLead(lead)}
                    className={`w-full text-left rounded-xl border px-4 py-3 transition ${
                      selectedLead?.id === lead.id
                        ? 'border-brand-primary shadow-md ring-2 ring-brand-primary/40 bg-brand-accent/10'
                        : 'border-brand-text/10 hover:border-brand-primary/50'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-semibold text-brand-text dark:text-white">{lead.name}</p>
                        <p className="text-xs text-brand-text/60 dark:text-gray-400">{lead.email}</p>
                      </div>
                      <span className={`text-xs font-semibold px-2 py-1 rounded-full ${sentiment.classes}`}>
                        {sentiment.label}
                      </span>
                    </div>
                    <div className="mt-3 flex items-center justify-between text-xs text-brand-text/60 dark:text-gray-400">
                      <span className="inline-flex items-center gap-1">
                        <Users className="h-3.5 w-3.5" />
                        {lead.stage}
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <Mail className="h-3.5 w-3.5" />
                        {lead.source || 'Inbox'}
                      </span>
                    </div>
                  </button>
                )
              })
            )}
          </div>
        </div>

        {/* Suggested Replies */}
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm p-6 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-xs uppercase tracking-wide text-brand-text/60 dark:text-gray-400">AI drafts</p>
              <h2 className="text-xl font-semibold text-brand-text dark:text-white">Suggested reply</h2>
            </div>
            {selectedLead && (
              <span className="inline-flex items-center gap-2 text-xs text-brand-text/60 dark:text-gray-400">
                <MessageSquare className="h-3.5 w-3.5" />
                {selectedLead.stage}
              </span>
            )}
          </div>

          {selectedLead ? (
            <>
              <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/30 p-4 mb-4 space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-semibold text-brand-text dark:text-white">{selectedLead.name}</span>
                  <span className="text-brand-text/60 dark:text-gray-400">{selectedLead.company || 'Unknown company'}</span>
                </div>
                <p className="text-xs text-brand-text/60 dark:text-gray-400 break-words">{selectedLead.email}</p>
                <div className="flex items-center gap-2 text-xs text-brand-text/70 dark:text-gray-400">
                  <Sparkles className="h-3.5 w-3.5" />
                  Lead score {selectedLead.score}/10 · Source: {selectedLead.source || 'Inbox'}
                </div>
              </div>

              <textarea
                rows={12}
                value={suggestedReply}
                onChange={(e) => setSuggestedReply(e.target.value)}
                className="flex-1 rounded-xl border border-brand-text/10 dark:border-gray-700 focus:ring-brand-primary focus:border-brand-primary bg-white dark:bg-gray-900 text-brand-text dark:text-gray-100 p-4 text-sm"
                placeholder="Generate an AI reply or start typing your own..."
              />

              <div className="mt-4 flex items-center justify-between gap-3">
                <button
                  onClick={handleGenerateReply}
                  disabled={suggestionLoading}
                  className="inline-flex items-center gap-2 rounded-xl border border-brand-primary/40 px-4 py-2 text-sm font-medium text-brand-primary hover:bg-brand-primary/10 disabled:opacity-50"
                >
                  {suggestionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                  Generate reply
                </button>
                <button
                  onClick={handleSendReply}
                  className="inline-flex items-center gap-2 rounded-xl bg-brand-primary px-4 py-2 text-sm font-medium text-white hover:bg-brand-secondary"
                >
                  <Send className="h-4 w-4" />
                  Send email
                </button>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-center text-brand-text/60 dark:text-gray-400">
              Select a lead to generate a tailored reply.
            </div>
          )}
        </div>

        {/* Chat Console */}
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm flex flex-col h-[620px]">
          <div className="flex items-center justify-between px-6 py-4 border-b border-brand-text/10 dark:border-gray-700">
            <div>
              <p className="text-xs uppercase tracking-wide text-brand-text/60 dark:text-gray-400">AI console</p>
              <h2 className="text-lg font-semibold text-brand-text dark:text-white">Conversational control</h2>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-lg px-6 py-4 rounded-2xl shadow-sm ${
                    message.type === 'user'
                      ? 'bg-gradient-to-r from-orange-500 to-orange-600 text-white'
                      : 'bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-700 dark:to-gray-600 text-gray-800 dark:text-gray-100 border border-gray-200 dark:border-gray-600'
                  }`}
                >
                  <div className="flex items-start space-x-3">
                    {message.type === 'ai' && (
                      <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-r from-orange-400 to-orange-500 rounded-full flex items-center justify-center">
                        <Bot className="h-4 w-4 text-white" />
                      </div>
                    )}
                    {message.type === 'user' && (
                      <div className="flex-shrink-0 w-8 h-8 bg-white/20 rounded-full flex items-center justify-center">
                        <User className="h-4 w-4 text-white" />
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
                      <p className={`text-xs mt-2 ${
                        message.type === 'user' ? 'text-white/70' : 'text-gray-500 dark:text-gray-400'
                      }`}>
                        {message.timestamp.toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {isTyping && (
              <div className="flex justify-start">
                <div className="bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-700 dark:to-gray-600 text-gray-800 dark:text-gray-100 max-w-lg px-6 py-4 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-600">
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-r from-orange-400 to-orange-500 rounded-full flex items-center justify-center">
                      <Bot className="h-4 w-4 text-white" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center space-x-1">
                        <div className="w-2 h-2 bg-orange-500 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-orange-500 rounded-full animate-bounce delay-75"></div>
                        <div className="w-2 h-2 bg-orange-500 rounded-full animate-bounce delay-150"></div>
                        <span className="text-xs text-gray-500 dark:text-gray-300 ml-2">AI assistant is typing…</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
          <div className="border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/40 p-4">
            <div className="flex flex-col space-y-3">
              <textarea
                rows={3}
                className="w-full rounded-xl border border-gray-300 dark:border-gray-600 focus:ring-2 focus:ring-orange-500 focus:border-orange-500 p-4 text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                placeholder="Ask the AI assistant anything... e.g., 'Draft a response to Acme Corp lead'"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
              />
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-400">
                  <div className="flex items-center space-x-2">
                    <Brain className="h-4 w-4" />
                    <span>AI model: Universal Assistant</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Zap className="h-4 w-4" />
                    <span>Context-aware responses enabled</span>
                  </div>
                </div>
                <button
                  onClick={handleSendMessage}
                  disabled={isLoading || !inputMessage.trim()}
                  className={`inline-flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-xl shadow-sm ${
                    isLoading || !inputMessage.trim()
                      ? 'bg-gray-300 text-gray-600 cursor-not-allowed'
                      : 'bg-gradient-to-r from-orange-500 to-orange-600 text-white hover:shadow-lg hover:translate-y-[-1px] transition'
                  }`}
                >
                  {isLoading ? (
                    <div className="flex items-center space-x-2">
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      <span>Sending...</span>
                    </div>
                  ) : (
                    <>
                      <Send className="h-4 w-4 mr-2" />
                      Send to AI Assistant
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
      {/* Quick Actions */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <button
          onClick={() => setInputMessage('Help me write a professional email response')}
          className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 border border-gray-200 dark:border-gray-700 hover:shadow-lg hover:border-orange-300 dark:hover:border-orange-600 transition-all duration-200 text-left group"
        >
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 bg-gradient-to-r from-orange-100 to-orange-200 dark:from-orange-900 dark:to-orange-800 rounded-xl flex items-center justify-center group-hover:from-orange-200 group-hover:to-orange-300 dark:group-hover:from-orange-800 dark:group-hover:to-orange-700 transition-all duration-200">
              <Mail className="h-6 w-6 text-orange-600 dark:text-orange-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Email Response</h3>
              <p className="text-xs text-gray-600 dark:text-gray-400">Generate professional email replies</p>
            </div>
          </div>
        </button>

        <button
          onClick={() => setInputMessage('Analyze my leads and suggest priorities')}
          className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 border border-gray-200 dark:border-gray-700 hover:shadow-lg hover:border-orange-300 dark:hover:border-orange-600 transition-all duration-200 text-left group"
        >
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 bg-gradient-to-r from-orange-100 to-orange-200 dark:from-orange-900 dark:to-orange-800 rounded-xl flex items-center justify-center group-hover:from-orange-200 group-hover:to-orange-300 dark:group-hover:from-orange-800 dark:group-hover:to-orange-700 transition-all duration-200">
              <Users className="h-6 w-6 text-orange-600 dark:text-orange-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Lead Analysis</h3>
              <p className="text-xs text-gray-600 dark:text-gray-400">Get insights on your leads</p>
            </div>
          </div>
        </button>

        <button
          onClick={() => setInputMessage('Set up automated workflows')}
          className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 border border-gray-200 dark:border-gray-700 hover:shadow-lg hover:border-orange-300 dark:hover:border-orange-600 transition-all duration-200 text-left group"
        >
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 bg-gradient-to-r from-orange-100 to-orange-200 dark:from-orange-900 dark:to-orange-800 rounded-xl flex items-center justify-center group-hover:from-orange-200 group-hover:to-orange-300 dark:group-hover:from-orange-800 dark:group-hover:to-orange-700 transition-all duration-200">
              <Zap className="h-6 w-6 text-orange-600 dark:text-orange-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Automation</h3>
              <p className="text-xs text-gray-600 dark:text-gray-400">Configure business workflows</p>
            </div>
          </div>
        </button>
      </div>
    </div>
  )
}
