import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Dashboard } from './pages/Dashboard'
import { Login } from './pages/Login'
import { Onboarding } from './pages/Onboarding'
import { Services } from './pages/Services'
import { Layout } from './components/Layout'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="/" element={<Layout><Dashboard /></Layout>} />
          <Route path="/services" element={<Layout><Services /></Layout>} />
        </Routes>
      </div>
    </Router>
  )
}

export default App
