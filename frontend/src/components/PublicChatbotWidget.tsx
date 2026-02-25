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
    const apiKey = import.meta.env.VITE_CHATBOT_API_KEY
    if (!apiKey) return

    if (window.__fikiriWidgetLoaded) return
    window.__fikiriWidgetLoaded = true

    const scriptUrl = import.meta.env.VITE_CHATBOT_SDK_URL || DEFAULT_SDK_URL
    const initWidget = () => {
      if (!window.Fikiri) return
      try {
        window.Fikiri.init({
          apiKey,
          apiUrl: config.apiUrl,
          features: ['chatbot', 'leadCapture'],
          debug: false
        })
        window.Fikiri.Chatbot.show({
          position: 'bottom-right'
        })
      } catch (err) {
        // No-op: public widget should not break landing pages
      }
    }

    if (window.Fikiri) {
      initWidget()
      return
    }

    const existing = document.querySelector(`script[src="${scriptUrl}"]`)
    if (existing) {
      existing.addEventListener('load', initWidget)
      return
    }

    const script = document.createElement('script')
    script.src = scriptUrl
    script.async = true
    script.onload = initWidget
    document.body.appendChild(script)
  }, [])

  return null
}
