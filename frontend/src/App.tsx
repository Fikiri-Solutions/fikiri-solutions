import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Suspense } from 'react'
import { Analytics } from '@vercel/analytics/react'
import { SpeedInsights } from '@vercel/speed-insights/react'
import { Dashboard } from './pages/Dashboard'
import { Login } from './pages/Login'
import { Signup } from './pages/Signup'
import { TermsOfService } from './pages/TermsOfService'
import { PrivacyPolicy } from './pages/PrivacyPolicy'
import { Onboarding } from './pages/Onboarding'
import { OnboardingFlow } from './pages/OnboardingFlow'
import { Services } from './pages/Services'
import { CRM } from './pages/CRM'
import { AIAssistant } from './pages/AIAssistant'
import { NotFoundPage, ErrorPage } from './pages/ErrorPages'
import { ServicesLanding } from './pages/ServicesLanding'
import { AIAssistantLanding } from './pages/AIAssistantLanding'
import { LandscapingLanding } from './pages/LandscapingLanding'
import { RestaurantLanding } from './pages/RestaurantLanding'
import { MedicalLanding } from './pages/MedicalLanding'
import { Layout } from './components/Layout'
import { IndustryAutomation } from './components/IndustryAutomation'
import { About } from './pages/About'
import { PrivacySettings } from './components/PrivacySettings'
import { PublicOnboardingFlow } from './pages/PublicOnboardingFlow'
import LandingPage from './pages/LandingPage'
import PricingPage from './pages/PricingPage'
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
import { getFeatureConfig } from './config'
import { useWarmRoutes } from './hooks/useWarmRoutes'

function App() {
  try {
    const features = getFeatureConfig()
    useWarmRoutes() // Warm up routes after first paint

    return (
      <ErrorBoundary>
        <Router>
          <ThemeProvider>
            <CustomizationProvider>
              <ActivityProvider>
                <AuthProvider>
                  <QueryProvider>
                    <ToastProvider>
                      <ScrollToTop />
                      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-300">
                        <Suspense fallback={<PageLoader />}>
                          <Routes>
                          {/* Public routes - no authentication required */}
                          <Route path="/" element={<LandingPage />} />
                          <Route path="/pricing" element={<PricingPage />} />
                          <Route path="/services-landing" element={<ServicesLanding />} />
                          <Route path="/ai-landing" element={<AIAssistantLanding />} />
                          <Route path="/industries/landscaping" element={<LandscapingLanding />} />
                          <Route path="/industries/restaurant" element={<RestaurantLanding />} />
                          <Route path="/industries/medical" element={<MedicalLanding />} />
                          <Route path="/terms" element={<TermsOfService />} />
                          <Route path="/privacy" element={<PrivacyPolicy />} />
                          <Route path="/error" element={<ErrorPage />} />
                          
                          {/* Pre-authentication onboarding flow */}
                          <Route path="/onboarding-flow" element={
                            <AuthRoute>
                              <PublicOnboardingFlow />
                            </AuthRoute>
                          } />
                          <Route path="/onboarding-flow/:step" element={
                            <AuthRoute>
                              <PublicOnboardingFlow />
                            </AuthRoute>
                          } />
                          
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
                          
                          {/* Onboarding routes - require authentication but not completed onboarding */}
                          {features.showOnboarding && (
                            <>
                              <Route path="/onboarding" element={
                                <OnboardingRoute>
                                  <OnboardingFlow />
                                </OnboardingRoute>
                              } />
                              <Route path="/onboarding/:step" element={
                                <OnboardingRoute>
                                  <OnboardingFlow />
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
                              <Layout><IndustryAutomation /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/about" element={
                            <ProtectedRoute>
                              <Layout><About /></Layout>
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
                    <Analytics />
                    <SpeedInsights />
                    </ToastProvider>
                  </QueryProvider>
                </AuthProvider>
              </ActivityProvider>
            </CustomizationProvider>
          </ThemeProvider>
        </Router>
      </ErrorBoundary>
    )
  } catch (error) {
    console.error('App component error:', error)
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center p-8">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Application Error</h1>
          <p className="text-gray-600 mb-4">Failed to initialize the application</p>
          <p className="text-sm text-gray-500">Error: {error.message}</p>
          <button 
            onClick={() => window.location.reload()} 
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Reload Page
          </button>
        </div>
      </div>
    )
  }
}

export default App
// DEPLOYMENT MARKER: Tue Sep 16 18:04:02 EDT 2025 - Force Vercel rebuild
// UI/UX Changes: Industry AI, FeatureStatus, BackToTop, Test Attributes
