import React, { useState, useEffect } from 'react'
import { Brain, Send, Bot, User, Clock, Zap, Mail, Users } from 'lucide-react'
import { apiClient, AIResponse } from '../services/apiClient'
import { StatusIcon } from '../components/StatusIcon'

interface ChatMessage {
  id: string
  type: 'user' | 'ai'
  content: string
  timestamp: Date
  classification?: {
    intent: string
    confidence: number
    suggested_action: string
    urgency: string
  }
}

export const AIAssistant: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [aiStatus, setAiStatus] = useState<AIResponse | null>(null)

  useEffect(() => {
    fetchAIStatus()
    // Add welcome message
    setMessages([{
      id: '1',
      type: 'ai',
      content: 'Hello! I\'m your AI Assistant. I can help you with email responses, lead analysis, and business automation. How can I assist you today?',
      timestamp: new Date()
    }])
  }, [])

  const fetchAIStatus = async () => {
    try {
      const status = await apiClient.testAIAssistant()
      setAiStatus(status)
    } catch (error) {
      console.error('Failed to fetch AI status:', error)
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
        content: response.response || 'I apologize, but I encountered an issue generating a response.',
        timestamp: new Date(),
        classification: response.classification || {
          intent: 'general_inquiry',
          confidence: 0.85,
          suggested_action: 'provide_information',
          urgency: 'normal'
        }
      }

      setMessages(prev => [...prev, aiMessage])
    } catch (error) {
      console.error('Failed to send message:', error)
      setError(apiClient.handleError(error))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">AI Assistant</h1>
          <p className="mt-1 text-sm text-gray-600">
            Get intelligent help with email responses, lead analysis, and business automation.
          </p>
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
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-900'
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
                      message.type === 'user' ? 'text-blue-100' : 'text-gray-500'
                    }`}>
                      {message.timestamp.toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ))}
          
          {/* Loading Indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 text-gray-900 px-4 py-2 rounded-lg">
                <div className="flex items-center space-x-2">
                  <Bot className="h-4 w-4" />
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-gray-200 p-4">
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
              className="btn-primary flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
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
          className="card hover:shadow-md transition-shadow duration-200 text-left"
        >
          <div className="flex items-center space-x-3">
            <Mail className="h-6 w-6 text-blue-600" />
            <div>
              <h3 className="text-sm font-medium text-gray-900">Email Response</h3>
              <p className="text-xs text-gray-500">Generate professional email replies</p>
            </div>
          </div>
        </button>

        <button
          onClick={() => setInputMessage('Analyze my leads and suggest priorities')}
          className="card hover:shadow-md transition-shadow duration-200 text-left"
        >
          <div className="flex items-center space-x-3">
            <Users className="h-6 w-6 text-green-600" />
            <div>
              <h3 className="text-sm font-medium text-gray-900">Lead Analysis</h3>
              <p className="text-xs text-gray-500">Get insights on your leads</p>
            </div>
          </div>
        </button>

        <button
          onClick={() => setInputMessage('Set up automated workflows')}
          className="card hover:shadow-md transition-shadow duration-200 text-left"
        >
          <div className="flex items-center space-x-3">
            <Zap className="h-6 w-6 text-yellow-600" />
            <div>
              <h3 className="text-sm font-medium text-gray-900">Automation</h3>
              <p className="text-xs text-gray-500">Configure business workflows</p>
            </div>
          </div>
        </button>
      </div>
    </div>
  )
}
