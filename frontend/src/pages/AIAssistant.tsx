import React, { useState, useEffect, useRef } from 'react'
import { Brain, Send, Bot, User, Clock, Zap, Mail, Users, Wifi, WifiOff } from 'lucide-react'
import { apiClient, AIResponse } from '../services/apiClient'
import { StatusIcon } from '../components/StatusIcon'
import { useWebSocket } from '../hooks/useWebSocket'

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
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { isConnected } = useWebSocket()

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
      
      const rawResponse = response.data?.response || 'I apologize, but I encountered an issue generating a response.'
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

      {/* Chat Interface */}
      <div className="card h-[600px] flex flex-col bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-lg">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-lg lg:max-w-2xl px-6 py-4 rounded-2xl shadow-sm ${
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
                    <div className="prose prose-sm max-w-none">
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
                    </div>
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
          
          {/* Typing Indicator */}
          {isTyping && (
            <div className="flex justify-start">
              <div className="bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-700 dark:to-gray-600 text-gray-800 dark:text-gray-100 max-w-lg lg:max-w-2xl px-6 py-4 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-600">
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-r from-orange-400 to-orange-500 rounded-full flex items-center justify-center">
                    <Bot className="h-4 w-4 text-white" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-orange-500 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-orange-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 bg-orange-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                      <span className="text-sm text-gray-600 dark:text-gray-300">AI is thinking...</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          {/* Auto-scroll anchor */}
          <div ref={messagesEndRef} />
          
          {/* Loading Indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-700 dark:to-gray-600 text-gray-800 dark:text-gray-100 px-6 py-4 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-600">
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-r from-orange-400 to-orange-500 rounded-full flex items-center justify-center">
                    <Bot className="h-4 w-4 text-white" />
                  </div>
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-orange-500 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-orange-500 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                    <div className="w-2 h-2 bg-orange-500 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-gray-200 dark:border-gray-700 p-6 bg-gray-50 dark:bg-gray-900">
          <div className="flex space-x-4">
            <div className="flex-1">
              <input
                type="text"
                className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all duration-200"
                placeholder="Ask me anything about email responses, leads, or automation..."
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                disabled={isLoading}
              />
            </div>
            <button
              onClick={handleSendMessage}
              disabled={!inputMessage.trim() || isLoading}
              className="bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 text-white px-6 py-3 rounded-xl font-medium transition-all duration-200 flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl"
            >
              <Send className="h-4 w-4" />
              <span>Send</span>
            </button>
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
