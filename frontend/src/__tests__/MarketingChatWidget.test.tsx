import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MarketingChatWidget, isSiteChatWidgetEnabled } from '../components/MarketingChatWidget'

vi.mock('../components/FikiriSiteChatWidget', () => ({
  FikiriSiteChatWidget: () => <div data-testid="site-chat-widget">widget</div>,
}))

describe('MarketingChatWidget', () => {
  it('renders site widget when enabled', () => {
    vi.stubEnv('VITE_SITE_CHAT_WIDGET_ENABLED', 'true')
    expect(isSiteChatWidgetEnabled()).toBe(true)
    render(<MarketingChatWidget />)
    expect(screen.getByTestId('site-chat-widget')).toBeInTheDocument()
    vi.unstubAllEnvs()
  })

  it('hides widget when disabled via env', () => {
    vi.stubEnv('VITE_SITE_CHAT_WIDGET_ENABLED', 'false')
    expect(isSiteChatWidgetEnabled()).toBe(false)
    render(<MarketingChatWidget />)
    expect(screen.queryByTestId('site-chat-widget')).not.toBeInTheDocument()
    vi.unstubAllEnvs()
  })
})
