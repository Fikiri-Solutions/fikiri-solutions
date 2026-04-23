import React, { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Menu, X, Palette, LogOut, User } from 'lucide-react'
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

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [customizationOpen, setCustomizationOpen] = useState(false)
  const [accountManagementOpen, setAccountManagementOpen] = useState(false)
  const location = useLocation()
  const { customization } = useCustomization()
  const { user, logout } = useAuth()

  // Persist sidebar state in localStorage
  useEffect(() => {
    const savedSidebarState = localStorage.getItem('sidebarOpen')
    if (savedSidebarState !== null) {
      setSidebarOpen(JSON.parse(savedSidebarState))
    }
  }, [])

  useEffect(() => {
    localStorage.setItem('sidebarOpen', JSON.stringify(sidebarOpen))
  }, [sidebarOpen])

  // Close sidebar on mobile when route changes
  useEffect(() => {
    if (window.innerWidth < 1024) {
      setSidebarOpen(false)
    }
  }, [location.pathname])

  // Handle sign out
  const handleSignOut = () => {
    logout()
  }

  const navigation = getDashboardSidebarNav(user)

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900 transition-colors duration-300">
      {/* Mobile sidebar */}
      <div className={`fixed inset-0 z-50 lg:hidden ${sidebarOpen ? 'block' : 'hidden'}`}>
        <div className="fixed inset-0 bg-gray-600 bg-opacity-75 dark:bg-gray-900 dark:bg-opacity-75" onClick={() => setSidebarOpen(false)} />
        <div className="fixed inset-y-0 left-0 flex w-64 flex-col bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transition-colors duration-300">
          <div className="flex h-16 items-center justify-between px-4">
            <Link to="/dashboard" className="flex items-center space-x-2 hover:opacity-80 transition-opacity duration-200">
              <FikiriLogo 
                size="lg" 
                variant="full" 
                animated={true}
                className="hover:scale-105 transition-transform duration-200"
              />
            </Link>
            <button onClick={() => setSidebarOpen(false)} className="text-brand-text dark:text-gray-300 hover:text-brand-primary dark:hover:text-white">
              <X className="h-6 w-6" />
            </button>
          </div>
          <nav className="flex-1 px-4 py-4">
            {navigation.map((item) => (
              <Link
                key={item.href}
                to={item.href}
                className={`flex min-h-[44px] items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors duration-200 ${
                  isDashboardNavItemActive(location.pathname, item.href)
                    ? 'bg-brand-accent/20 dark:bg-brand-accent/20 text-brand-primary dark:text-brand-accent'
                    : 'text-brand-text dark:text-gray-300 hover:bg-brand-accent/10 dark:hover:bg-gray-700'
                }`}
                onClick={() => setSidebarOpen(false)}
              >
                <item.icon className="mr-3 h-5 w-5" />
                {item.name}
              </Link>
            ))}
          </nav>
          <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 px-4 py-3">
            <LegalFooterLinks
              className="text-xs text-gray-500 dark:text-gray-400"
              linkClassName="text-gray-600 hover:text-brand-primary hover:underline dark:text-gray-300 dark:hover:text-brand-accent"
            />
          </div>
        </div>
      </div>

      {/* Desktop sidebar */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
        <div className="flex flex-col flex-grow bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transition-colors duration-300">
          <div className="flex h-16 items-center px-4">
            <Link to="/dashboard" className="flex items-center space-x-2 hover:opacity-80 transition-opacity duration-200">
              <FikiriLogo 
                size="lg" 
                variant="full" 
                animated={true}
                className="hover:scale-105 transition-transform duration-200"
              />
            </Link>
          </div>
          <nav className="flex-1 px-4 py-4">
            {navigation.map((item) => (
              <Link
                key={item.href}
                to={item.href}
                className={`flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors duration-200 ${
                  isDashboardNavItemActive(location.pathname, item.href)
                    ? 'bg-brand-accent/20 dark:bg-brand-accent/20 text-brand-primary dark:text-brand-accent'
                    : 'text-brand-text dark:text-gray-300 hover:bg-brand-accent/10 dark:hover:bg-gray-700'
                }`}
              >
                <item.icon className="mr-3 h-5 w-5" />
                {item.name}
              </Link>
            ))}
          </nav>
          <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 px-4 py-3">
            <LegalFooterLinks
              className="text-xs text-gray-500 dark:text-gray-400"
              linkClassName="text-gray-600 hover:text-brand-primary hover:underline dark:text-gray-300 dark:hover:text-brand-accent"
            />
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top bar */}
        <div className="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-x-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 shadow-sm sm:gap-x-6 sm:px-6 lg:px-8 transition-colors duration-300">
          <button
            type="button"
            className="lg:hidden flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-brand-text dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-brand-primary dark:hover:text-white transition-colors"
            onClick={() => setSidebarOpen(true)}
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
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-brand-text hover:bg-gray-100 hover:text-brand-primary dark:text-gray-300 dark:hover:bg-gray-700 dark:hover:text-white transition-colors"
                title="Customize appearance"
                aria-label="Customize appearance"
              >
                <Palette className="h-5 w-5" />
              </button>
              <button
                type="button"
                onClick={() => setAccountManagementOpen(true)}
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-brand-text hover:bg-gray-100 hover:text-brand-primary dark:text-gray-300 dark:hover:bg-gray-700 dark:hover:text-white transition-colors"
                title="Account settings"
                aria-label="Account settings"
              >
                <User className="h-5 w-5" />
              </button>
              <button 
                type="button"
                onClick={handleSignOut}
                className="flex h-11 min-w-[44px] shrink-0 items-center gap-1.5 rounded-lg px-2 text-sm font-medium text-brand-text hover:bg-gray-100 hover:text-brand-primary dark:text-gray-300 dark:hover:bg-gray-700 dark:hover:text-white transition-colors"
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
