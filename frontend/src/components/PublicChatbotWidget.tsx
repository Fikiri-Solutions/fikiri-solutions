import { useEffect } from 'react'
import { config } from '../config'

declare global {
  interface Window {
    Fikiri?: any
    __fikiriWidgetLoaded?: boolean
  }
}

const DEFAULT_SDK_URL = '/integrations/universal/fikiri-sdk.js'

/** Same key Install page uses after POST /user/api-keys — avoids duplicating secrets in .env for local dev. */
const INSTALL_FLOW_STORAGE_KEY = 'fikiri-public-api-key'

/** SDK builds URLs as apiUrl + '/api/public/...'; config.apiUrl already ends with /api — strip it. */
function sdkApiOrigin(apiUrl: string): string {
  const trimmed = apiUrl.trim().replace(/\/+$/, '')
  return trimmed.replace(/\/api\/?$/i, '') || trimmed
}

function resolvePublicChatbotApiKey(): string {
  const fromEnv = (import.meta.env.VITE_CHATBOT_API_KEY || '').trim()
  if (fromEnv.startsWith('fik_')) return fromEnv
  if (import.meta.env.DEV && typeof window !== 'undefined') {
    const fromInstall = (localStorage.getItem(INSTALL_FLOW_STORAGE_KEY) || '').trim()
    if (fromInstall.startsWith('fik_')) return fromInstall
  }
  return ''
}

export const PublicChatbotWidget: React.FC = () => {
  useEffect(() => {
    const apiKey = resolvePublicChatbotApiKey()
    // Backend only accepts keys prefixed with fik_; skip placeholder/empty to avoid 401 spam
    if (!apiKey) return

    if (window.__fikiriWidgetLoaded) return
    window.__fikiriWidgetLoaded = true

    const scriptUrl = import.meta.env.VITE_CHATBOT_SDK_URL || DEFAULT_SDK_URL
    const initWidget = async () => {
      if (!window.Fikiri) return
      try {
        window.Fikiri.init({
          apiKey,
          apiUrl: sdkApiOrigin(config.apiUrl),
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
