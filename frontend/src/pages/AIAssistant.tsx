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

    try {
      // Call the real AI API
      const response = await apiClient.sendChatMessage(inputMessage.trim(), {
        conversation_history: messages.slice(-6) // Last 6 messages for context
      })
      
      const aiMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'ai',
        content: response.data?.response || 'I apologize, but I encountered an issue generating a response.',
        timestamp: new Date()
        // Classification data removed to prevent debug metadata display
      }

      setMessages(prev => [...prev, aiMessage])
    } catch (error) {
      // Failed to send message - provide helpful fallback response
      const fallbackResponse = getFallbackResponse(inputMessage.trim())
      const aiMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'ai',
        content: fallbackResponse,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, aiMessage])
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
      <div className="card h-96 flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                  message.type === 'user'
                    ? 'bg-brand-primary text-white'
                    : 'bg-brand-background dark:bg-gray-700 text-brand-text dark:text-gray-100 border border-brand-text/10'
                }`}
              >
                <div className="flex items-start space-x-2">
                  {message.type === 'ai' && (
                    <Bot className="h-4 w-4 mt-1 flex-shrink-0" />
                  )}
                  {message.type === 'user' && (
                    <User className="h-4 w-4 mt-1 flex-shrink-0" />
                  )}
                  <div className="flex-1">
                    <p className="text-sm">{message.content}</p>
                    <p className={`text-xs mt-1 ${
                      message.type === 'user' ? 'text-white/70' : 'text-brand-text/60 dark:text-gray-400'
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
              <div className="bg-brand-background dark:bg-gray-700 text-brand-text dark:text-gray-100 max-w-xs lg:max-w-md px-4 py-2 rounded-lg border border-brand-text/10">
                <div className="flex items-start space-x-2">
                  <Bot className="h-4 w-4 mt-1 flex-shrink-0" />
                  <div className="flex-1">
                    <div className="flex items-center space-x-1">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-brand-accent rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-brand-accent rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 bg-brand-accent rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                      <span className="text-sm text-brand-text/60 dark:text-gray-400 ml-2">AI is typing...</span>
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
              <div className="bg-brand-background dark:bg-gray-700 text-brand-text dark:text-gray-100 px-4 py-2 rounded-lg border border-brand-text/10">
                <div className="flex items-center space-x-2">
                  <Bot className="h-4 w-4" />
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-brand-accent rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-brand-accent rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                    <div className="w-2 h-2 bg-brand-accent rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-brand-text/10 dark:border-gray-700 p-4">
          <div className="flex space-x-4">
            <div className="flex-1">
              <input
                type="text"
                className="input-field"
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
              className="bg-brand-primary hover:bg-brand-secondary text-white px-4 py-2 rounded-lg font-medium transition-all duration-200 flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
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
          className="bg-brand-background dark:bg-gray-800 rounded-lg shadow-md p-4 border border-brand-text/10 hover:shadow-lg transition-all duration-200 text-left"
        >
          <div className="flex items-center space-x-3">
            <Mail className="h-6 w-6 text-brand-primary" />
            <div>
              <h3 className="text-sm font-medium text-brand-text dark:text-white">Email Response</h3>
              <p className="text-xs text-brand-text/70 dark:text-gray-400">Generate professional email replies</p>
            </div>
          </div>
        </button>

        <button
          onClick={() => setInputMessage('Analyze my leads and suggest priorities')}
          className="bg-brand-background dark:bg-gray-800 rounded-lg shadow-md p-4 border border-brand-text/10 hover:shadow-lg transition-all duration-200 text-left"
        >
          <div className="flex items-center space-x-3">
            <Users className="h-6 w-6 text-brand-secondary" />
            <div>
              <h3 className="text-sm font-medium text-brand-text dark:text-white">Lead Analysis</h3>
              <p className="text-xs text-brand-text/70 dark:text-gray-400">Get insights on your leads</p>
            </div>
          </div>
        </button>

        <button
          onClick={() => setInputMessage('Set up automated workflows')}
          className="bg-brand-background dark:bg-gray-800 rounded-lg shadow-md p-4 border border-brand-text/10 hover:shadow-lg transition-all duration-200 text-left"
        >
          <div className="flex items-center space-x-3">
            <Zap className="h-6 w-6 text-brand-accent" />
            <div>
              <h3 className="text-sm font-medium text-brand-text dark:text-white">Automation</h3>
              <p className="text-xs text-brand-text/70 dark:text-gray-400">Configure business workflows</p>
            </div>
          </div>
        </button>
      </div>
    </div>
  )
}
