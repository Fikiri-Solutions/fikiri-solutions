import React, { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Menu, X, Palette, LogOut, User, ChevronsLeft, ChevronsRight } from 'lucide-react'
import { getDashboardSidebarNav, isDashboardNavItemActive } from '../navigation/dashboardNav'
import { MobileBottomNav } from './MobileBottomNav'
import { ThemeToggle } from './ThemeToggle'
import { CustomizationPanel } from './CustomizationPanel'
import { BackToTop } from './BackToTop'
import { AccountManagement } from './AccountManagement'
import { useCustomization } from '../contexts/CustomizationContext'
import { useAuth } from '../contexts/AuthContext'
import { FikiriLogo } from './FikiriLogo'
import { EmailVerificationBanner } from './EmailVerificationBanner'
import { SubscriptionGate } from './SubscriptionGate'
import { LegalFooterLinks } from './LegalFooterLinks'

interface LayoutProps {
  children: React.ReactNode
}

const SIDEBAR_COLLAPSED_KEY = 'fikiri:sidebar-collapsed'

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [customizationOpen, setCustomizationOpen] = useState(false)
  const [accountManagementOpen, setAccountManagementOpen] = useState(false)
  const location = useLocation()
  const { customization } = useCustomization()
  const { user, logout } = useAuth()

  useEffect(() => {
    try {
      if (localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === '1') {
        setSidebarCollapsed(true)
      }
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    try {
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, sidebarCollapsed ? '1' : '0')
    } catch {
      // ignore
    }
  }, [sidebarCollapsed])

  // Close mobile drawer when route changes
  useEffect(() => {
    if (typeof window !== 'undefined' && window.innerWidth < 1024) {
      setMobileMenuOpen(false)
    }
  }, [location.pathname])

  // Handle sign out
  const handleSignOut = () => {
    logout()
  }

  const navigation = getDashboardSidebarNav(user)

  return (
    <div className="mobile-layout-root min-h-screen bg-white dark:bg-gray-900 transition-colors duration-300">
      {/* Mobile sidebar */}
      <div className={`fixed inset-0 z-50 lg:hidden ${mobileMenuOpen ? 'block' : 'hidden'}`}>
        <div className="fixed inset-0 bg-gray-600 bg-opacity-75 dark:bg-gray-900 dark:bg-opacity-75" onClick={() => setMobileMenuOpen(false)} />
        <div className="fixed inset-y-0 left-0 flex w-64 flex-col bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transition-colors duration-300">
          <div className="flex h-16 items-center justify-between px-4">
            <Link to="/dashboard" className="flex min-w-0 max-w-[11rem] items-center hover:opacity-80 transition-opacity duration-200">
              <FikiriLogo 
                size="md" 
                variant="full" 
                animated={true}
                className="h-10 w-auto max-w-full hover:scale-105 transition-transform duration-200"
              />
            </Link>
            <button onClick={() => setMobileMenuOpen(false)} className="text-brand-text dark:text-gray-300 hover:text-brand-primary dark:hover:text-white">
              <X className="h-6 w-6" />
            </button>
          </div>
          <nav className="flex-1 px-4 py-4 overflow-y-auto">
            {navigation.map((item) => (
              <Link
                key={item.href}
                to={item.href}
                className={`flex min-h-[44px] items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors duration-200 ${
                  isDashboardNavItemActive(location.pathname, item.href)
                    ? 'bg-brand-accent/20 dark:bg-brand-accent/20 text-brand-primary dark:text-brand-accent'
                    : 'text-brand-text dark:text-gray-300 hover:bg-brand-accent/10 dark:hover:bg-gray-700'
                }`}
                onClick={() => setMobileMenuOpen(false)}
              >
                <item.icon className="mr-3 h-5 w-5" />
                {item.name}
              </Link>
            ))}
          </nav>
          <div className="border-t border-gray-200 dark:border-gray-700 px-4 py-3 space-y-2">
            <button
              type="button"
              onClick={() => {
                setCustomizationOpen(true)
                setMobileMenuOpen(false)
              }}
              className="w-full flex min-h-[44px] items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg text-brand-text dark:text-gray-300 hover:bg-brand-accent/10 dark:hover:bg-gray-700"
            >
              <Palette className="h-5 w-5" />
              Customize appearance
            </button>
            <button
              type="button"
              onClick={() => {
                setAccountManagementOpen(true)
                setMobileMenuOpen(false)
              }}
              className="w-full flex min-h-[44px] items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg text-brand-text dark:text-gray-300 hover:bg-brand-accent/10 dark:hover:bg-gray-700"
            >
              <User className="h-5 w-5" />
              Account settings
            </button>
            <button
              type="button"
              onClick={() => {
                setMobileMenuOpen(false)
                handleSignOut()
              }}
              className="w-full flex min-h-[44px] items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg text-brand-text dark:text-gray-300 hover:bg-brand-accent/10 dark:hover:bg-gray-700"
            >
              <LogOut className="h-5 w-5" />
              Sign out
            </button>
          </div>
          <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 px-4 py-3">
            <LegalFooterLinks
              className="text-xs text-gray-500 dark:text-gray-400"
              linkClassName="text-gray-600 hover:text-brand-primary hover:underline dark:text-gray-300 dark:hover:text-brand-accent"
            />
          </div>
        </div>
      </div>

      {/* Desktop sidebar */}
      <div
        className={`hidden lg:fixed lg:inset-y-0 lg:z-30 lg:flex lg:flex-col transition-[width] duration-200 ease-in-out ${
          sidebarCollapsed ? 'lg:w-20' : 'lg:w-64'
        }`}
      >
        <div className="flex min-h-0 flex-1 flex-col bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transition-colors duration-300">
          <div
            className={`shrink-0 border-b border-gray-200 dark:border-gray-700 ${
              sidebarCollapsed
                ? 'flex flex-col items-center gap-1.5 py-2.5 px-1'
                : 'flex h-16 items-center gap-1 px-3'
            }`}
          >
            {sidebarCollapsed ? (
              <>
                <button
                  type="button"
                  onClick={() => setSidebarCollapsed(false)}
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 hover:text-brand-primary dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white transition-colors"
                  aria-expanded={false}
                  aria-label="Expand navigation"
                  title="Expand sidebar"
                >
                  <ChevronsRight className="h-5 w-5" />
                </button>
                <Link
                  to="/dashboard"
                  className="flex items-center justify-center rounded-lg hover:opacity-80 transition-opacity"
                  title="Dashboard home"
                >
                  <FikiriLogo size="xs" variant="circle" animated={false} className="h-8 w-8 shrink-0" />
                </Link>
              </>
            ) : (
              <>
                <Link
                  to="/dashboard"
                  className="flex min-h-0 min-w-0 flex-1 items-center space-x-2 hover:opacity-80 transition-opacity duration-200"
                  title="Dashboard home"
                >
                  <FikiriLogo
                    size="lg"
                    variant="full"
                    animated={true}
                    className="min-w-0 hover:scale-105 transition-transform duration-200"
                  />
                </Link>
              </>
            )}
          </div>
          {!sidebarCollapsed && (
            <div className="shrink-0 px-3 pb-2">
              <button
                type="button"
                onClick={() => setSidebarCollapsed(true)}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 hover:text-brand-primary dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white transition-colors"
                aria-expanded={true}
                aria-label="Collapse navigation"
                title="Collapse sidebar"
              >
                <ChevronsLeft className="h-5 w-5" />
              </button>
            </div>
          )}
          <nav className={`flex-1 py-3 overflow-y-auto ${sidebarCollapsed ? 'px-1.5' : 'px-3'}`}>
            {navigation.map((item) => (
              <Link
                key={item.href}
                to={item.href}
                title={item.name}
                className={`flex items-center text-sm font-medium rounded-lg transition-colors duration-200 ${
                  sidebarCollapsed ? 'mb-0.5 justify-center px-2 py-2.5' : 'mb-0.5 px-3 py-2'
                } ${
                  isDashboardNavItemActive(location.pathname, item.href)
                    ? 'bg-brand-accent/20 dark:bg-brand-accent/20 text-brand-primary dark:text-brand-accent'
                    : 'text-brand-text dark:text-gray-300 hover:bg-brand-accent/10 dark:hover:bg-gray-700'
                }`}
              >
                <item.icon
                  className={`h-5 w-5 shrink-0 ${sidebarCollapsed ? '' : 'mr-3'}`}
                  aria-hidden
                />
                {sidebarCollapsed ? (
                  <span className="sr-only">{item.name}</span>
                ) : (
                  <span className="truncate">{item.name}</span>
                )}
              </Link>
            ))}
          </nav>
          {!sidebarCollapsed && (
            <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 px-3 py-3">
              <LegalFooterLinks
                className="text-xs text-gray-500 dark:text-gray-400"
                linkClassName="text-gray-600 hover:text-brand-primary hover:underline dark:text-gray-300 dark:hover:text-brand-accent"
              />
            </div>
          )}
        </div>
      </div>

      {/* Main content */}
      <div
        className={`transition-[padding] duration-200 ease-in-out ${
          sidebarCollapsed ? 'lg:pl-20' : 'lg:pl-64'
        }`}
      >
        {/* Top bar */}
        <div className="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-x-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 shadow-sm sm:gap-x-6 sm:px-6 lg:px-8 transition-colors duration-300">
          <button
            type="button"
            className="lg:hidden flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-brand-text dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-brand-primary dark:hover:text-white transition-colors"
            onClick={() => setMobileMenuOpen(true)}
            aria-label="Open menu"
          >
            <Menu className="h-6 w-6" />
          </button>
          <div className="flex min-w-0 flex-1 gap-x-2 self-stretch sm:gap-x-4 lg:gap-x-6">
            <div className="flex min-w-0 flex-1" />
            <div className="flex min-w-0 max-w-full items-center gap-x-1 overflow-x-auto overflow-y-hidden py-1 sm:gap-x-3 lg:gap-x-6 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
              <ThemeToggle />
              <button
                type="button"
                onClick={() => setCustomizationOpen(true)}
                className="hidden sm:flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-brand-text hover:bg-gray-100 hover:text-brand-primary dark:text-gray-300 dark:hover:bg-gray-700 dark:hover:text-white transition-colors"
                title="Customize appearance"
                aria-label="Customize appearance"
              >
                <Palette className="h-5 w-5" />
              </button>
              <button
                type="button"
                onClick={() => setAccountManagementOpen(true)}
                className="hidden sm:flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-brand-text hover:bg-gray-100 hover:text-brand-primary dark:text-gray-300 dark:hover:bg-gray-700 dark:hover:text-white transition-colors"
                title="Account settings"
                aria-label="Account settings"
              >
                <User className="h-5 w-5" />
              </button>
              <button 
                type="button"
                onClick={handleSignOut}
                className="hidden sm:flex h-11 min-w-[44px] shrink-0 items-center gap-1.5 rounded-lg px-2 text-sm font-medium text-brand-text hover:bg-gray-100 hover:text-brand-primary dark:text-gray-300 dark:hover:bg-gray-700 dark:hover:text-white transition-colors"
                aria-label="Sign out"
              >
                <LogOut className="h-4 w-4 shrink-0" />
                <span className="hidden sm:inline">Sign out</span>
              </button>
            </div>
          </div>
        </div>

        {/* Page content */}
        <main id="main-content" className="py-6 pb-20 lg:pb-6">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <EmailVerificationBanner user={user} />
            <SubscriptionGate>{children}</SubscriptionGate>
            <footer className="mt-10 border-t border-gray-200 pt-6 dark:border-gray-700">
              <LegalFooterLinks className="text-center text-xs text-gray-500 dark:text-gray-400" />
            </footer>
          </div>
        </main>
      </div>
      
      {/* Mobile Bottom Navigation */}
      <MobileBottomNav />
      
      {/* Customization Panel */}
      <CustomizationPanel 
        isOpen={customizationOpen} 
        onClose={() => setCustomizationOpen(false)} 
      />
      
      {/* Account Management Modal */}
      <AccountManagement 
        isOpen={accountManagementOpen} 
        onClose={() => setAccountManagementOpen(false)} 
      />
      
      {/* Back to Top Button */}
      <BackToTop />
    </div>
  )
}
