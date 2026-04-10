import { useEffect } from 'react'
import { config } from '../config'

declare global {
  interface Window {
    Fikiri?: any
    __fikiriWidgetLoaded?: boolean
  }
}

const DEFAULT_SDK_URL = '/integrations/universal/fikiri-sdk.js'

export const PublicChatbotWidget: React.FC = () => {
  useEffect(() => {
    const apiKey = (import.meta.env.VITE_CHATBOT_API_KEY || '').trim()
    // Backend only accepts keys prefixed with fik_; skip placeholder/empty to avoid 401 spam
    if (!apiKey || !apiKey.startsWith('fik_')) return

    if (window.__fikiriWidgetLoaded) return
    window.__fikiriWidgetLoaded = true

    const scriptUrl = import.meta.env.VITE_CHATBOT_SDK_URL || DEFAULT_SDK_URL
    const initWidget = async () => {
      if (!window.Fikiri) return
      try {
        window.Fikiri.init({
          apiKey,
          apiUrl: config.apiUrl,
          features: ['chatbot', 'leadCapture'],
          debug: false
        })
        if (typeof window.Fikiri.validatePublicApiKey === 'function') {
          const status = await window.Fikiri.validatePublicApiKey()
          if (status && status.valid === false) {
            if (import.meta.env.DEV) {
              console.warn('[Fikiri] Chatbot API key invalid:', status.error_code, status.message)
            }
            return
          }
        }
        window.Fikiri.Chatbot.show({
          position: 'bottom-right'
        })
      } catch {
        // No-op: public widget should not break landing pages
      }
    }

    if (window.Fikiri) {
      void initWidget()
      return
    }

    const existing = document.querySelector(`script[src="${scriptUrl}"]`)
    if (existing) {
      existing.addEventListener('load', () => void initWidget())
      return
    }

    const script = document.createElement('script')
    script.src = scriptUrl
    script.async = true
    script.onload = () => void initWidget()
    document.body.appendChild(script)
  }, [])

  return null
}
