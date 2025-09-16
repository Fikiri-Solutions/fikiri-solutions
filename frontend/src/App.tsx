import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
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
import { QueryProvider } from './providers/QueryProvider'
import { ToastProvider } from './components/Toast'
import { ThemeProvider } from './contexts/ThemeContext'
import { CustomizationProvider } from './contexts/CustomizationContext'
import { ScrollToTop } from './components/ScrollToTop'
import { getFeatureConfig } from './config'

function App() {
  const features = getFeatureConfig()

  return (
    <ThemeProvider>
      <CustomizationProvider>
        <QueryProvider>
          <ToastProvider>
            <Router>
              <ScrollToTop />
              <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-300">
                <Routes>
                  <Route path="/login" element={<Login />} />
                  {features.showOnboarding && <Route path="/onboarding" element={<Onboarding />} />}
                  <Route path="/" element={<Layout><Dashboard /></Layout>} />
                  <Route path="/services" element={<Layout><Services /></Layout>} />
                  <Route path="/services-landing" element={<ServicesLanding />} />
                  <Route path="/ai-landing" element={<AIAssistantLanding />} />
                  <Route path="/industries/landscaping" element={<LandscapingLanding />} />
                  <Route path="/industries/restaurant" element={<RestaurantLanding />} />
                  <Route path="/industries/medical" element={<MedicalLanding />} />
                  <Route path="/home" element={<RenderInspiredLanding />} />
                  <Route path="/crm" element={<Layout><CRM /></Layout>} />
                  <Route path="/ai" element={<Layout><AIAssistant /></Layout>} />
                  <Route path="/assistant" element={<Layout><AIAssistant /></Layout>} />
                  <Route path="/industry" element={<Layout><IndustryAutomation /></Layout>} />
                  <Route path="/error" element={<ErrorPage />} />
                  <Route path="*" element={<NotFoundPage />} />
                </Routes>
              </div>
              <Analytics />
              <SpeedInsights />
            </Router>
          </ToastProvider>
        </QueryProvider>
      </CustomizationProvider>
    </ThemeProvider>
  )
}

export default App
// DEPLOYMENT MARKER: Tue Sep 16 18:04:02 EDT 2025 - Force Vercel rebuild
// UI/UX Changes: Industry AI, FeatureStatus, BackToTop, Test Attributes
