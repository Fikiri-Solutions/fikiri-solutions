import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { Suspense, useMemo, lazy } from 'react'
import { HelmetProvider } from 'react-helmet-async'
import { Dashboard } from './pages/Dashboard'
import { Login } from './pages/Login'
import { Signup } from './pages/Signup'
import { ForgotPassword } from './pages/ForgotPassword'
import { ResetPassword } from './pages/ResetPassword'
import { TermsOfService } from './pages/TermsOfService'
import { PrivacyPolicy } from './pages/PrivacyPolicy'
import { Onboarding } from './pages/Onboarding'
import { Services } from './pages/Services'
import { CRM } from './pages/CRM'
import { AIAssistant } from './pages/AIAssistant'
import { Automations } from './pages/Automations'
import { ChatbotBuilder } from './pages/ChatbotBuilder'
import { GmailConnect } from './pages/GmailConnect'
import { OutlookConnect } from './pages/OutlookConnect'
import { Integrations } from './pages/Integrations'
import { EmailInbox } from './pages/EmailInbox'
import { GmailStatusCheck } from './pages/GmailStatusCheck'
import { NotFoundPage, ErrorPage } from './pages/ErrorPages'
import { ServicesLanding } from './pages/ServicesLanding'
import { AIAssistantLanding } from './pages/AIAssistantLanding'
import { LandscapingLanding } from './pages/LandscapingLanding'
import { RestaurantLanding } from './pages/RestaurantLanding'
import { MedicalLanding } from './pages/MedicalLanding'
import { Layout } from './components/Layout'
import { UsageAnalytics } from './pages/UsageAnalytics'
import { About } from './pages/About'
import { Contact } from './pages/Contact'
import { PrivacySettings } from './components/PrivacySettings'
import LandingPage from './pages/LandingPage'
import InstallPage from './pages/Install'
import RadiantLandingPage from './pages/RadiantLandingPage'
import PricingPage from './pages/PricingPage'
import { BillingPage } from './pages/BillingPage'
import { QueryProvider } from './providers/QueryProvider'
import { ToastProvider } from './components/Toast'
import { ThemeProvider } from './contexts/ThemeContext'
import { CustomizationProvider } from './contexts/CustomizationContext'
import { ActivityProvider } from './contexts/ActivityContext'
import { AuthProvider } from './contexts/AuthContext'
import { ScrollToTop } from './components/ScrollToTop'
import { ErrorBoundary } from './components/ErrorBoundary'
import { PageLoader } from './components/PageLoader'
import { ProtectedRoute, AuthRoute, OnboardingRoute } from './components/RouteGuard'
import { LandingThemeGuard } from './components/LandingThemeGuard'
import { getFeatureConfig } from './config'
import { useWarmRoutes } from './hooks/useWarmRoutes'
import { AccessibilityProvider } from './components/AccessibilityProvider'

const Analytics = lazy(async () => {
  const module = await import('@vercel/analytics/react')
  return { default: module.Analytics }
})

const SpeedInsights = lazy(async () => {
  const module = await import('@vercel/speed-insights/react')
  return { default: module.SpeedInsights }
})

function App() {
  const features = getFeatureConfig()
  useWarmRoutes() // Warm up routes after first paint
  const showObservability = useMemo(() => {
    if (import.meta.env.PROD) {
      return true
    }
    return import.meta.env.VITE_ENABLE_ANALYTICS === 'true'
  }, [])

  return (
    <ErrorBoundary>
      <HelmetProvider>
        <AccessibilityProvider>
          <Router
            future={{
              v7_startTransition: true,
              v7_relativeSplatPath: true,
            }}
          >
          <ThemeProvider>
            <LandingThemeGuard />
            <CustomizationProvider>
              <ActivityProvider>
                <AuthProvider>
                  <QueryProvider>
                    <ToastProvider>
                      <ScrollToTop />
                      <div className="min-h-screen bg-white dark:bg-gray-900 transition-colors duration-300">
                        <Suspense fallback={<PageLoader />}>
                          <Routes>
                          {/* Public routes - no authentication required */}
                          <Route path="/" element={<RadiantLandingPage />} />
                          <Route path="/landing-classic" element={<LandingPage />} />
                          <Route path="/pricing" element={<PricingPage />} />
                          <Route path="/services-landing" element={<ServicesLanding />} />
                          <Route path="/ai-landing" element={<AIAssistantLanding />} />
                          <Route path="/industries/landscaping" element={<LandscapingLanding />} />
                          <Route path="/industries/restaurant" element={<RestaurantLanding />} />
                          <Route path="/industries/medical" element={<MedicalLanding />} />
                          <Route path="/about" element={<About />} />
                          <Route path="/contact" element={<Contact />} />
                          <Route path="/install" element={<InstallPage />} />
                          <Route path="/terms" element={<TermsOfService />} />
                          <Route path="/privacy" element={<PrivacyPolicy />} />
                          <Route path="/error" element={<ErrorPage />} />
                          
                          {/* Legacy onboarding-flow redirects */}
                          <Route path="/onboarding-flow" element={<Navigate to="/onboarding" replace />} />
                          <Route path="/onboarding-flow/:step" element={<Navigate to="/onboarding" replace />} />
                          <Route path="/onboarding-flow/sync" element={<Navigate to="/onboarding/2" replace />} />
                          
                          {/* Authentication routes */}
                          <Route path="/login" element={
                            <AuthRoute>
                              <Login />
                            </AuthRoute>
                          } />
                          <Route path="/signup" element={
                            <AuthRoute>
                              <Signup />
                            </AuthRoute>
                          } />
                          <Route path="/forgot-password" element={
                            <AuthRoute>
                              <ForgotPassword />
                            </AuthRoute>
                          } />
                          <Route path="/reset-password" element={
                            <AuthRoute>
                              <ResetPassword />
                            </AuthRoute>
                          } />
                          
                          {/* Onboarding routes - require authentication but not completed onboarding */}
                          {features.showOnboarding && (
                            <>
                              <Route path="/onboarding" element={
                                <OnboardingRoute>
                                  <Onboarding />
                                </OnboardingRoute>
                              } />
                              <Route path="/onboarding/:step" element={
                                <OnboardingRoute>
                                  <Onboarding />
                                </OnboardingRoute>
                              } />
                            </>
                          )}
                          
                          {/* Protected routes - require authentication and completed onboarding */}
                          <Route path="/home" element={
                            <ProtectedRoute>
                              <Layout><Dashboard /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/dashboard" element={
                            <ProtectedRoute>
                              <Layout><Dashboard /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/services" element={
                            <ProtectedRoute>
                              <Layout><Services /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/crm" element={
                            <ProtectedRoute>
                              <Layout><CRM /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/ai" element={
                            <ProtectedRoute>
                              <Layout><AIAssistant /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/assistant" element={
                            <ProtectedRoute>
                              <Layout><AIAssistant /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/industry" element={
                            <ProtectedRoute>
                              <Layout><UsageAnalytics /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/analytics" element={
                            <ProtectedRoute>
                              <Layout><UsageAnalytics /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/automations" element={
                            <ProtectedRoute>
                              <Layout><Automations /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/ai/chatbot-builder" element={
                            <ProtectedRoute>
                              <Layout><ChatbotBuilder /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/integrations" element={<Navigate to="/automations" replace />} />
                          <Route path="/integrations/gmail" element={
                            <ProtectedRoute>
                              <Layout><GmailConnect /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/integrations/outlook" element={
                            <ProtectedRoute>
                              <Layout><OutlookConnect /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/billing" element={
                            <ProtectedRoute>
                              <Layout><BillingPage /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/inbox" element={
                            <Layout><EmailInbox /></Layout>
                          } />
                          <Route path="/gmail-status" element={
                            <ProtectedRoute>
                              <Layout><GmailStatusCheck /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/privacy-settings" element={
                            <ProtectedRoute>
                              <Layout><PrivacySettings /></Layout>
                            </ProtectedRoute>
                          } />
                          
                          {/* 404 route */}
                          <Route path="*" element={<NotFoundPage />} />
                        </Routes>
                      </Suspense>
                    </div>
                    {showObservability && (
                      <Suspense fallback={null}>
                        <Analytics />
                        <SpeedInsights />
                      </Suspense>
                    )}
                    </ToastProvider>
                  </QueryProvider>
                </AuthProvider>
              </ActivityProvider>
            </CustomizationProvider>
          </ThemeProvider>
        </Router>
        </AccessibilityProvider>
      </HelmetProvider>
    </ErrorBoundary>
  )
}

export default App
// DEPLOYMENT MARKER: Tue Sep 16 18:04:02 EDT 2025 - Force Vercel rebuild
// UI/UX Changes: Industry AI, FeatureStatus, BackToTop, Test Attributes
