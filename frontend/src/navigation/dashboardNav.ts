import type { LucideIcon } from 'lucide-react'
import {
  BarChart3,
  BookOpen,
  Brain,
  CreditCard,
  LayoutDashboard,
  Mail,
  Package,
  PlugZap,
  Settings,
  Shield,
  Users,
  Zap,
} from 'lucide-react'

/**
 * Single source of truth for authenticated app navigation.
 * Layout (sidebar + drawer) and MobileBottomNav must derive from here so new routes
 * and copy stay consistent across desktop and mobile.
 */
export type DashboardNavItem = {
  name: string
  href: string
  icon: LucideIcon
}

const DASHBOARD_NAV_BASE: DashboardNavItem[] = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Inbox', href: '/inbox', icon: Mail },
  { name: 'Integrations', href: '/integrations/gmail', icon: PlugZap },
  { name: 'Services', href: '/services', icon: Settings },
  { name: 'Automations', href: '/automations', icon: Zap },
  { name: 'CRM', href: '/crm', icon: Users },
  { name: 'AI Assistant', href: '/ai', icon: Brain },
  { name: 'Import center', href: '/import-center', icon: Package },
  { name: 'Chatbot Builder', href: '/ai/chatbot-builder', icon: BookOpen },
  { name: 'Usage Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Billing', href: '/billing', icon: CreditCard },
  { name: 'Privacy', href: '/privacy-settings', icon: Shield },
]

export function getDashboardSidebarNav(
  user: { onboarding_completed?: boolean } | null | undefined
): DashboardNavItem[] {
  const items = [...DASHBOARD_NAV_BASE]
  if (user && !user.onboarding_completed) {
    items.unshift({ name: 'Complete Setup', href: '/onboarding', icon: Zap })
  }
  return items
}

/**
 * Mobile tab bar: max six primary destinations (thumb reach + scanability).
 * Secondary items (Inbox, Automations, Import, Chatbot, Billing, Privacy) stay in the drawer menu.
 * While onboarding is incomplete, Analytics is omitted so "Complete Setup" fits without crowding.
 */
const MOBILE_BOTTOM_HREFS_DEFAULT = [
  '/dashboard',
  '/services',
  '/integrations/gmail',
  '/crm',
  '/ai',
  '/analytics',
] as const

const MOBILE_BOTTOM_HREFS_ONBOARDING = [
  '/onboarding',
  '/dashboard',
  '/services',
  '/integrations/gmail',
  '/crm',
  '/ai',
] as const

/** Active state for sidebar and mobile tab bar (nested routes share parent highlight). */
export function isDashboardNavItemActive(pathname: string, href: string): boolean {
  if (href === '/dashboard') return pathname === '/dashboard' || pathname === '/home'
  if (href === '/onboarding') return pathname === '/onboarding' || pathname.startsWith('/onboarding/')
  if (href === '/ai')
    return pathname === '/ai' || pathname === '/assistant' || pathname.startsWith('/ai/')
  if (href === '/integrations/gmail') return pathname.startsWith('/integrations')
  if (href === '/analytics') return pathname === '/analytics' || pathname === '/industry'
  return pathname === href
}

export function getMobileBottomNavItems(
  user: { onboarding_completed?: boolean } | null | undefined
): DashboardNavItem[] {
  const hrefs =
    user && !user.onboarding_completed ? MOBILE_BOTTOM_HREFS_ONBOARDING : MOBILE_BOTTOM_HREFS_DEFAULT
  const all = getDashboardSidebarNav(user)
  return hrefs.map((href) => {
    const item = all.find((n) => n.href === href)
    if (!item) {
      throw new Error(`dashboardNav: missing nav item for href "${href}"`)
    }
    return item
  })
}
