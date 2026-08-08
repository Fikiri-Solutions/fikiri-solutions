import React, { Suspense, lazy } from 'react'

/** Marketing-site chat only — not the tenant embed product (`PublicChatbotWidget`). */
export function isSiteChatWidgetEnabled(): boolean {
  const raw = (import.meta.env.VITE_SITE_CHAT_WIDGET_ENABLED || '').trim().toLowerCase()
  if (raw === 'false' || raw === '0' || raw === 'off') return false
  return true
}

const FikiriSiteChatWidget = lazy(() =>
  import('./FikiriSiteChatWidget').then((module) => ({
    default: module.FikiriSiteChatWidget,
  }))
)

/** Deferred so marketing cold loads do not pay for chat UI until after first paint. */
export const MarketingChatWidget: React.FC = () => {
  if (!isSiteChatWidgetEnabled()) return null
  return (
    <Suspense fallback={null}>
      <FikiriSiteChatWidget />
    </Suspense>
  )
}
