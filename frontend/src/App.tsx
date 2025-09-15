import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Dashboard } from './pages/Dashboard'
import { Login } from './pages/Login'
import { Onboarding } from './pages/Onboarding'
import { Services } from './pages/Services'
import { CRM } from './pages/CRM'
import { AIAssistant } from './pages/AIAssistant'
import { Layout } from './components/Layout'
import { QueryProvider } from './providers/QueryProvider'
import { ScrollToTop } from './components/ScrollToTop'
import { getFeatureConfig } from './config'

function App() {
  const features = getFeatureConfig()

  return (
    <QueryProvider>
      <Router>
        <ScrollToTop />
        <div className="min-h-screen bg-gray-50">
          <Routes>
            <Route path="/login" element={<Login />} />
            {features.showOnboarding && <Route path="/onboarding" element={<Onboarding />} />}
            <Route path="/" element={<Layout><Dashboard /></Layout>} />
            <Route path="/services" element={<Layout><Services /></Layout>} />
            <Route path="/crm" element={<Layout><CRM /></Layout>} />
            <Route path="/ai" element={<Layout><AIAssistant /></Layout>} />
          </Routes>
        </div>
      </Router>
    </QueryProvider>
  )
}

export default App
