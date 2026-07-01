import React from 'react'
import { FikiriSiteChatWidget } from './FikiriSiteChatWidget'

/** Marketing-site chat only — not the tenant embed product (`PublicChatbotWidget`). */
export function isSiteChatWidgetEnabled(): boolean {
  const raw = (import.meta.env.VITE_SITE_CHAT_WIDGET_ENABLED || '').trim().toLowerCase()
  if (raw === 'false' || raw === '0' || raw === 'off') return false
  return true
}

export const MarketingChatWidget: React.FC = () => {
  if (!isSiteChatWidgetEnabled()) return null
  return <FikiriSiteChatWidget />
}
