import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Suspense } from 'react'
import { Analytics } from '@vercel/analytics/react'
import { SpeedInsights } from '@vercel/speed-insights/react'
import { Dashboard } from './pages/Dashboard'
import { Login } from './pages/Login'
import { Onboarding } from './pages/Onboarding'
import { Services } from './pages/Services'
import { CRM } from './pages/CRM'
import { AIAssistant } from './pages/AIAssistant'
import { NotFoundPage, ErrorPage } from './pages/ErrorPages'
import { ServicesLanding } from './pages/ServicesLanding'
import { AIAssistantLanding } from './pages/AIAssistantLanding'
import { LandscapingLanding } from './pages/LandscapingLanding'
import { RestaurantLanding } from './pages/RestaurantLanding'
import { MedicalLanding } from './pages/MedicalLanding'
import { RenderInspiredLanding } from './pages/RenderInspiredLanding'
import { Layout } from './components/Layout'
import { IndustryAutomation } from './components/IndustryAutomation'
import { PrivacySettings } from './components/PrivacySettings'
import { OnboardingFlow } from './pages/OnboardingFlow'
import { QueryProvider } from './providers/QueryProvider'
import { ToastProvider } from './components/Toast'
import { ThemeProvider } from './contexts/ThemeContext'
import { CustomizationProvider } from './contexts/CustomizationContext'
// import { ActivityProvider } from './contexts/ActivityContext'
import { ScrollToTop } from './components/ScrollToTop'
import { ErrorBoundary } from './components/ErrorBoundary'
import { PageLoader } from './components/PageLoader'
import { getFeatureConfig } from './config'

// Simple test component to isolate the issue
const TestComponent = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
          Fikiri Solutions - Test Mode
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          This is a minimal test to isolate the error.
        </p>
      </div>
    </div>
  )
}

function App() {
  const features = getFeatureConfig()

  return (
    <ErrorBoundary>
      <ThemeProvider>
        <CustomizationProvider>
          {/* <ActivityProvider> */}
            <QueryProvider>
              <ToastProvider>
              <Router>
                <ScrollToTop />
                <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-300">
                  <Suspense fallback={<PageLoader />}>
                    <Routes>
                      <Route path="/" element={<Layout><TestComponent /></Layout>} />
                      <Route path="/login" element={<Login />} />
                      <Route path="/dashboard" element={<Layout><Dashboard /></Layout>} />
                      <Route path="*" element={<NotFoundPage />} />
                    </Routes>
                  </Suspense>
                </div>
                <Analytics />
                <SpeedInsights />
              </Router>
            </ToastProvider>
          </QueryProvider>
          {/* </ActivityProvider> */}
        </CustomizationProvider>
      </ThemeProvider>
    </ErrorBoundary>
  )
}

export default App
// DEPLOYMENT MARKER: Tue Sep 16 18:04:02 EDT 2025 - Force Vercel rebuild
// UI/UX Changes: Industry AI, FeatureStatus, BackToTop, Test Attributes
