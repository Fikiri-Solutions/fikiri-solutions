import React, { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Mail, Users, Brain, Settings, Menu, X, Palette, LogOut, BarChart3, Shield, Zap, User, PlugZap, BookOpen, CreditCard } from 'lucide-react'
import { MobileBottomNav } from './MobileBottomNav'
import { ThemeToggle } from './ThemeToggle'
import { CustomizationPanel } from './CustomizationPanel'
import { BackToTop } from './BackToTop'
import { AccountManagement } from './AccountManagement'
import { OnboardingWizard } from './OnboardingWizard'
import { useCustomization } from '../contexts/CustomizationContext'
import { useTheme } from '../contexts/ThemeContext'
import { useAuth } from '../contexts/AuthContext'
import { FikiriLogo } from './FikiriLogo'

interface LayoutProps {
  children: React.ReactNode
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [customizationOpen, setCustomizationOpen] = useState(false)
  const [accountManagementOpen, setAccountManagementOpen] = useState(false)
  const [onboardingWizardOpen, setOnboardingWizardOpen] = useState(false)
  const location = useLocation()
  const { customization } = useCustomization()
  const { resolvedTheme } = useTheme()
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

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: Mail },
    { name: 'Inbox', href: '/inbox', icon: Mail },
    { name: 'Services', href: '/services', icon: Settings },
    { name: 'Integrations', href: '/integrations', icon: PlugZap },
    { name: 'Automations', href: '/automations', icon: Zap },
    { name: 'CRM', href: '/crm', icon: Users },
    { name: 'AI Assistant', href: '/ai', icon: Brain },
    { name: 'Chatbot Builder', href: '/ai/chatbot-builder', icon: BookOpen },
    { name: 'Usage Analytics', href: '/industry', icon: BarChart3 },
    { name: 'Billing', href: '/billing', icon: CreditCard },
    { name: 'Privacy', href: '/privacy', icon: Shield },
  ]

  // Add onboarding link if not completed
  if (user && !user.onboarding_completed) {
    navigation.unshift({ name: 'Complete Setup', href: '#', icon: Zap })
  }

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
              item.href === '#' ? (
                <button
                  key={item.name}
                  onClick={() => {
                    setOnboardingWizardOpen(true)
                    setSidebarOpen(false)
                  }}
                  className="flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors duration-200 text-brand-text dark:text-gray-300 hover:bg-brand-accent/10 dark:hover:bg-gray-700"
                >
                  <item.icon className="mr-3 h-5 w-5" />
                  {item.name}
                </button>
              ) : (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors duration-200 ${
                    location.pathname === item.href
                      ? 'bg-brand-accent/20 dark:bg-brand-accent/20 text-brand-primary dark:text-brand-accent'
                      : 'text-brand-text dark:text-gray-300 hover:bg-brand-accent/10 dark:hover:bg-gray-700'
                  }`}
                  onClick={() => setSidebarOpen(false)}
                >
                  <item.icon className="mr-3 h-5 w-5" />
                  {item.name}
                </Link>
              )
            ))}
          </nav>
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
              item.href === '#' ? (
                <button
                  key={item.name}
                  onClick={() => setOnboardingWizardOpen(true)}
                  className="flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors duration-200 text-brand-text dark:text-gray-300 hover:bg-brand-accent/10 dark:hover:bg-gray-700"
                >
                  <item.icon className="mr-3 h-5 w-5" />
                  {item.name}
                </button>
              ) : (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors duration-200 ${
                    location.pathname === item.href
                      ? 'bg-brand-accent/20 dark:bg-brand-accent/20 text-brand-primary dark:text-brand-accent'
                      : 'text-brand-text dark:text-gray-300 hover:bg-brand-accent/10 dark:hover:bg-gray-700'
                  }`}
                >
                  <item.icon className="mr-3 h-5 w-5" />
                  {item.name}
                </Link>
              )
            ))}
          </nav>
        </div>
      </div>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top bar */}
        <div className="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-x-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 shadow-sm sm:gap-x-6 sm:px-6 lg:px-8 transition-colors duration-300">
          <button
            type="button"
            className="-m-2.5 p-2.5 text-brand-text dark:text-gray-300 hover:text-brand-primary dark:hover:text-white lg:hidden transition-colors"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-6 w-6" />
          </button>
          <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
            <div className="flex flex-1"></div>
            <div className="flex items-center gap-x-4 lg:gap-x-6">
              <ThemeToggle />
              <button
                onClick={() => setCustomizationOpen(true)}
                className="p-2 text-brand-text hover:text-brand-primary dark:text-gray-300 dark:hover:text-white transition-colors"
                title="Customize appearance"
              >
                <Palette className="h-5 w-5" />
              </button>
              <button
                onClick={() => setAccountManagementOpen(true)}
                className="p-2 text-brand-text hover:text-brand-primary dark:text-gray-300 dark:hover:text-white transition-colors"
                title="Account settings"
              >
                <User className="h-5 w-5" />
              </button>
              <button 
                onClick={handleSignOut}
                className="flex items-center gap-2 text-sm font-medium text-brand-text hover:text-brand-primary dark:text-gray-300 dark:hover:text-white transition-colors"
              >
                <LogOut className="h-4 w-4" />
                Sign out
              </button>
            </div>
          </div>
        </div>

        {/* Page content */}
        <main id="main-content" className="py-6 pb-20 lg:pb-6">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            {children}
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
      
      {/* Onboarding Wizard */}
      <OnboardingWizard 
        isOpen={onboardingWizardOpen} 
        onClose={() => setOnboardingWizardOpen(false)}
        onComplete={() => setOnboardingWizardOpen(false)}
      />
      
      {/* Back to Top Button */}
      <BackToTop />
    </div>
  )
}
