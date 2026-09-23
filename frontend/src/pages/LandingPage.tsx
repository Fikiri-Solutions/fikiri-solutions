import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useInView } from 'react-intersection-observer'
import { motion } from 'framer-motion'
import { 
  ArrowRight, 
  Mail, 
  Users, 
  Brain, 
  BarChart3, 
  CheckCircle, 
  Menu,
  X
} from 'lucide-react'
import { PageMeta } from '../components/PageMeta'
import FikiriLogo from '@/components/FikiriLogo'
import SimpleAnimatedBackground from '@/components/SimpleAnimatedBackground'
import LogoTicker from '@/components/LogoTicker'
import { useAuth } from '@/contexts/AuthContext'
import { MarketingChatWidget } from '../components/MarketingChatWidget'
import { clientPartnerships } from '@/lib/clientPartnerships'

const LandingPage: React.FC = () => {
  // State for mobile menu
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()
  
  // Handle logo click - go to dashboard if authenticated, home if not
  const handleLogoClick = (e: React.MouseEvent) => {
    e.preventDefault()
    if (isAuthenticated) {
      navigate('/dashboard')
    } else {
      navigate('/')
    }
  }

  const valueProps = [
    {
      icon: Mail,
      title: "Never miss a hot lead",
      description: "Reply to new inquiries instantly and follow up automatically, even when you’re on a job or in a meeting."
    },
    {
      icon: Users,
      title: "Keep every contact organized",
      description: "See every conversation and deal in one place so your team stops double‑emailing or dropping the ball."
    },
    {
      icon: Brain,
      title: "Know where to focus",
      description: "Spot your best leads and repeatable work so you invest time where it actually drives revenue."
    },
    {
      icon: BarChart3,
      title: "Scales with your team",
      description: "From solo operators to multi‑location teams, connect the tools you already use and grow without extra headcount."
    }
  ]

  const howItWorks = [
    {
      step: "01",
      title: "Connect Your Accounts",
      description: "Link your email, CRM, and other business tools in minutes"
    },
    {
      step: "02", 
      title: "Automate Workflows",
      description: "Set up intelligent automations that work 24/7 for your business"
    },
    {
      step: "03",
      title: "Scale Your Business",
      description: "Watch your efficiency soar as AI handles routine tasks"
    }
  ]

  const features = [
    "No credit card required",
    "7-day free trial",
    "Cancel anytime",
    "24/7 customer support"
  ]

  // Refs for scroll-triggered animations
  // Check if elements are in view
  const { ref: heroRef, inView: heroInView } = useInView({ triggerOnce: true })
  const { ref: valuePropsRef, inView: valuePropsInView } = useInView({ triggerOnce: true })
  const { ref: howItWorksRef, inView: howItWorksInView } = useInView({ triggerOnce: true })
  const { ref: testimonialsRef, inView: testimonialsInView } = useInView({ triggerOnce: true })
  const { ref: ctaRef, inView: ctaInView } = useInView({ triggerOnce: true })

  // Simple navigation handlers without router
  const handleGetStarted = () => {
    // Clear any existing auth state to ensure fresh onboarding flow
    if (typeof window !== 'undefined') {
      localStorage.removeItem('fikiri-user')
      localStorage.removeItem('fikiri-user-id')
      localStorage.removeItem('fikiri-onboarding-data')
      localStorage.removeItem('fikiri-onboarding-completed')
    }
    window.location.href = '/signup'
  }

  const handleSignIn = () => {
    // Clear any existing auth state to ensure fresh login flow
    if (typeof window !== 'undefined') {
      localStorage.removeItem('fikiri-user')
      localStorage.removeItem('fikiri-user-id')
      localStorage.removeItem('fikiri-onboarding-data')
      localStorage.removeItem('fikiri-onboarding-completed')
      localStorage.removeItem('fikiri-auth') // Also clear Zustand store key if it exists
    }
    // Use navigate instead of window.location to avoid RouteGuard issues
    navigate('/login')
  }

  const handleSignUp = () => {
    // Clear any existing auth state to ensure fresh signup flow
    if (typeof window !== 'undefined') {
      localStorage.removeItem('fikiri-user')
      localStorage.removeItem('fikiri-user-id')
      localStorage.removeItem('fikiri-onboarding-data')
      localStorage.removeItem('fikiri-onboarding-completed')
      localStorage.removeItem('fikiri-auth') // Also clear Zustand store key if it exists
    }
    // Use navigate instead of window.location to avoid RouteGuard issues
    navigate('/signup')
  }

  const handlePricing = () => {
    window.location.href = '/pricing'
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-orange-900/30 to-red-900/30 text-white overflow-hidden relative font-serif" style={{
      background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 20%, #FF6B35 40%, #D2691E 60%, #8B0000 80%, #991b1b 100%)'
    }}>
      <PageMeta route="/landing-classic" />
      {/* Header Navigation */}
      <header className="relative z-20 w-full px-4 sm:px-6 lg:px-8 py-6">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <Link 
            to={isAuthenticated ? "/dashboard" : "/"}
            onClick={handleLogoClick}
            className="flex items-center space-x-3 hover:opacity-80 transition-opacity duration-200 cursor-pointer"
            aria-label={isAuthenticated ? "Fikiri Solutions - Go to dashboard" : "Fikiri Solutions - Return to homepage"}
          >
            <FikiriLogo 
              size="xl" 
              variant="full" 
              animated={true}
              className="hover:scale-105 transition-transform duration-200"
            />
          </Link>
          
          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-8">
            <a href="#features" className="text-white hover:text-orange-200 transition-colors">Features</a>
            <a href="#how-it-works" className="text-white hover:text-orange-200 transition-colors">How it works</a>
            <a href="#client-partnerships" className="text-white hover:text-orange-200 transition-colors">Client Partnerships</a>
            <button 
              onClick={handlePricing}
              className="text-white hover:text-orange-200 transition-colors"
            >
              Pricing
            </button>
          </nav>

          {/* Desktop Auth Buttons */}
          <div className="hidden md:flex items-center space-x-4">
            <button
              onClick={handleSignIn}
              className="px-4 py-2 text-white hover:text-orange-200 transition-colors"
              aria-label="Sign in to your Fikiri account"
            >
              Sign in
            </button>
            <button
              onClick={handleSignUp}
              className="px-6 py-2 bg-gradient-to-r from-orange-600 to-red-600 text-white font-semibold rounded-lg hover:from-orange-700 hover:to-red-700 transition-all duration-300" style={{
                background: 'linear-gradient(to right, #FF6B35, #8B0000)'
              }}
              aria-label="Get started with Fikiri Solutions - Create your account"
            >
              Get started
            </button>
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="md:hidden p-2 text-white hover:text-orange-200 transition-colors"
            aria-label="Toggle mobile menu"
          >
            {isMobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>

        {/* Mobile Menu */}
        {isMobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden mt-4 bg-gray-900/95 backdrop-blur-sm rounded-lg border border-gray-700"
          >
            <div className="px-4 py-6 space-y-4">
              {/* Mobile Navigation Links */}
              <div className="space-y-3">
                <a 
                  href="#features" 
                  className="block text-white hover:text-orange-200 transition-colors py-2"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Features
                </a>
                <a 
                  href="#how-it-works" 
                  className="block text-white hover:text-orange-200 transition-colors py-2"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  How it works
                </a>
                <a 
                  href="#client-partnerships" 
                  className="block text-white hover:text-orange-200 transition-colors py-2"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Client Partnerships
                </a>
                <button 
                  onClick={() => {
                    handlePricing()
                    setIsMobileMenuOpen(false)
                  }}
                  className="block text-white hover:text-orange-200 transition-colors py-2"
                >
                  Pricing
                </button>
              </div>
              
              {/* Mobile Auth Buttons */}
              <div className="pt-4 border-t border-gray-700 space-y-3">
                <button
                  onClick={() => {
                    handleSignIn()
                    setIsMobileMenuOpen(false)
                  }}
                  className="w-full px-4 py-3 text-white hover:text-orange-200 transition-colors text-left"
                  aria-label="Sign in to your Fikiri account"
                >
                  Sign in
                </button>
                <button
                  onClick={() => {
                    handleSignUp()
                    setIsMobileMenuOpen(false)
                  }}
                  className="w-full px-6 py-3 bg-gradient-to-r from-orange-600 to-red-600 text-white font-semibold rounded-lg hover:from-orange-700 hover:to-red-700 transition-all duration-300" style={{
                    background: 'linear-gradient(to right, #FF6B35, #8B0000)'
                  }}
                  aria-label="Get started with Fikiri Solutions - Create your account"
                >
                  Get started
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </header>

             {/* Simple Animated Background - CSS-based mesh effect */}
             <SimpleAnimatedBackground />

      {/* Hero Section */}
      <section ref={heroRef} className="relative z-10 min-h-screen flex items-center justify-center px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={heroInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
            transition={{ duration: 0.8 }}
          >
            <h1 className="text-4xl sm:text-6xl lg:text-7xl font-bold mb-6 bg-gradient-to-r from-orange-400 via-orange-500 to-red-600 bg-clip-text text-transparent" style={{
              background: 'linear-gradient(to right, #FF6B35, #D2691E, #8B0000)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent'
            }}>
              Stop losing time
              <br />
              and high‑value leads
            </h1>
            <p className="text-xl sm:text-2xl text-white mb-8 max-w-3xl mx-auto">
              Fikiri handles the follow‑up, reminders, and busywork—so whether it’s just you or a team of 50+, no lead or customer slips through the cracks.
              <br />
              <span className="text-orange-300 font-medium">Built for owner‑operators, lean teams, and growing multi‑location businesses.</span>
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={heroInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="flex flex-col sm:flex-row gap-4 justify-center items-center"
          >
            <button
              onClick={handleGetStarted}
              className="px-8 py-4 bg-gradient-to-r from-orange-600 to-red-600 text-white font-semibold rounded-lg hover:from-orange-700 hover:to-red-700 transition-all duration-300 transform hover:scale-105 flex items-center gap-2 shadow-lg"
              aria-label="Get started with Fikiri Solutions - Free trial"
            >
              Get Started Free
              <ArrowRight className="w-5 h-5" aria-hidden="true" />
            </button>
            <button
              onClick={() => navigate('/intake')}
              className="px-8 py-4 border border-orange-400 text-white font-semibold rounded-lg hover:bg-orange-500/20 hover:border-orange-300 transition-all duration-300 flex items-center gap-2"
              aria-label="Start a workflow conversation with Fikiri Solutions"
            >
              Start a workflow conversation
              <ArrowRight className="w-5 h-5" aria-hidden="true" />
            </button>
          </motion.div>

                 <motion.div
                   initial={{ opacity: 0 }}
                   animate={heroInView ? { opacity: 1 } : { opacity: 0 }}
                   transition={{ duration: 0.8, delay: 0.4 }}
                   className="mt-12"
                 >
                   <div className="bg-gray-800/60 backdrop-blur-sm rounded-2xl p-6 border border-gray-700/50 max-w-4xl mx-auto">
                     <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                       {features.map((feature, index) => (
                         <div key={index} className="flex items-center gap-3 text-center sm:text-left">
                           <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0" />
                           <span className="text-white font-medium">{feature}</span>
                         </div>
                       ))}
                     </div>
                   </div>
                 </motion.div>
        </div>
      </section>

      {/* Value Proposition Section */}
      <section ref={valuePropsRef} id="features" className="relative z-10 py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={valuePropsInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl sm:text-4xl font-bold mb-4 bg-gradient-to-r from-orange-400 via-orange-500 to-red-600 bg-clip-text text-transparent" style={{
              background: 'linear-gradient(to right, #FF6B35, #D2691E, #8B0000)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent'
            }}>
              Automation that works for solo and scaling teams
            </h2>
            <p className="text-xl text-gray-100 max-w-2xl mx-auto">
              Powerful AI that feels light enough for one person to run, but strong enough to support a growing team.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {valueProps.map((prop, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 30 }}
                animate={valuePropsInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6 border border-gray-700 hover:border-orange-500 transition-all duration-300"
              >
                <div className="w-12 h-12 bg-gradient-to-r from-orange-500 to-red-500 rounded-lg flex items-center justify-center mb-4">
                  <prop.icon className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-xl font-semibold mb-2 bg-gradient-to-r from-orange-400 via-orange-500 to-red-600 bg-clip-text text-transparent" style={{
                  background: 'linear-gradient(to right, #FF6B35, #D2691E, #8B0000)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent'
                }}>{prop.title}</h3>
                <p className="text-gray-100">{prop.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section ref={howItWorksRef} id="how-it-works" className="relative z-10 py-20 px-4 sm:px-6 lg:px-8 bg-gray-800/30">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={howItWorksInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl sm:text-4xl font-bold mb-4 bg-gradient-to-r from-orange-400 via-orange-500 to-blue-500 bg-clip-text text-transparent">
              How it fits into your day
            </h2>
            <p className="text-xl text-white max-w-2xl mx-auto">
              Set it up once, then let it quietly handle the busywork—whether you’re answering emails yourself or managing a team.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {howItWorks.map((step, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 30 }}
                animate={howItWorksInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
                transition={{ duration: 0.8, delay: index * 0.2 }}
                className="text-center"
              >
                <div className="w-16 h-16 bg-gradient-to-r from-orange-500 to-red-500 rounded-full flex items-center justify-center mx-auto mb-6">
                  <span className="text-2xl font-bold">{step.step}</span>
                </div>
                <h3 className="text-2xl font-semibold mb-4 bg-gradient-to-r from-orange-400 via-orange-500 to-blue-500 bg-clip-text text-transparent">{step.title}</h3>
                <p className="text-white">{step.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Client Partnerships */}
      <section ref={testimonialsRef} id="client-partnerships" className="relative z-10 py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={testimonialsInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-orange-300">
              Client Partnerships
            </p>
            <h2 className="text-3xl sm:text-4xl font-bold mb-4 bg-gradient-to-r from-orange-400 via-orange-500 to-blue-500 bg-clip-text text-transparent">
              Real client work across different industries.
            </h2>
            <p className="text-xl text-white max-w-3xl mx-auto">
              Fikiri starts with consulting and workflow discovery. From there, we help businesses
              plan, build, and support practical systems around their real operations — from
              automation and CRM to product workflows, cloud support, and custom tools.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4 mb-16">
            {clientPartnerships.map((client, index) => (
              <motion.article
                key={client.name}
                initial={{ opacity: 0, y: 30 }}
                animate={testimonialsInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                className="flex flex-col rounded-xl border border-gray-700 bg-gray-800/50 p-6 backdrop-blur-sm"
              >
                {client.logoSrc ? (
                  <div
                    className={
                      client.darkLogoPlate
                        ? 'mb-4 flex h-24 items-center justify-center overflow-hidden rounded-lg bg-black p-3 ring-1 ring-white/10 sm:h-28'
                        : 'mb-4 flex h-24 items-center justify-center overflow-hidden rounded-lg bg-white p-3 ring-1 ring-white/20 sm:h-28'
                    }
                  >
                    <img
                      src={client.logoSrc}
                      alt={client.logoAlt}
                      className="h-full w-full object-contain"
                      loading="lazy"
                      decoding="async"
                    />
                  </div>
                ) : (
                  <div
                    className="mb-4 flex h-24 items-center justify-center rounded-lg bg-orange-500/15 ring-1 ring-orange-400/30 sm:h-28"
                    role="img"
                    aria-label={client.logoAlt}
                  >
                    <span className="text-2xl font-semibold tracking-widest text-orange-300">
                      {client.fallbackMark}
                    </span>
                  </div>
                )}
                <h3 className="text-lg font-semibold text-white">{client.name}</h3>
                <p className="mt-1 text-sm font-medium text-orange-300">{client.category}</p>
                <p className="mt-3 flex-1 text-sm leading-relaxed text-white/80">{client.summary}</p>
                <a
                  href={client.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-4 inline-flex min-h-[44px] items-center text-sm font-medium text-orange-300 hover:text-orange-200"
                >
                  Visit site
                  <span className="sr-only"> ({client.name})</span>
                  <span aria-hidden className="ml-1">→</span>
                </a>
              </motion.article>
            ))}
          </div>

          <div className="mb-16 flex flex-col items-center gap-4 text-center">
            <p className="max-w-2xl text-lg text-white">
              Have a workflow, customer follow-up, or software problem you are trying to solve?
            </p>
            <Link
              to="/intake"
              className="inline-flex min-h-[44px] items-center rounded-lg bg-gradient-to-r from-orange-600 to-red-600 px-6 py-3 font-semibold text-white transition-all hover:from-orange-700 hover:to-red-700"
            >
              Start a workflow conversation
            </Link>
          </div>

          {/* Tech Stack Logos */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={testimonialsInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
            transition={{ duration: 0.8 }}
            className="text-center"
          >
            <p className="text-white mb-4 font-medium text-lg">Integrates with industry-leading platforms</p>
            <LogoTicker speed={25} className="max-w-4xl mx-auto" />
            <p className="text-xs text-white/50 text-center mt-4">
              * Technology representations shown for reference. We integrate with these platforms via their public APIs.
            </p>
          </motion.div>
        </div>
      </section>

      {/* Final CTA Section */}
      <section ref={ctaRef} className="relative z-10 py-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-r from-orange-600/20 to-red-600/20">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={ctaInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
            transition={{ duration: 0.8 }}
          >
            <h2 className="text-3xl sm:text-4xl font-bold mb-6 bg-gradient-to-r from-orange-400 via-orange-500 to-blue-500 bg-clip-text text-transparent">
              Start automating without adding headcount
            </h2>
            <p className="text-xl text-white mb-8">
              7-day free trial, no credit card required. Works whether you’re on your own or running a team across locations.
            </p>
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={ctaInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
              transition={{ duration: 0.8, delay: 0.2 }}
              className="flex flex-col sm:flex-row gap-4 justify-center items-center"
            >
              <button
                onClick={handleGetStarted}
                className="px-8 py-4 bg-gradient-to-r from-orange-600 to-red-600 text-white font-semibold rounded-lg hover:from-orange-700 hover:to-red-700 transition-all duration-300 transform hover:scale-105 flex items-center gap-2 shadow-lg" style={{
                  background: 'linear-gradient(to right, #FF6B35, #8B0000)'
                }}
                aria-label="Get started with Fikiri Solutions - Free trial"
              >
                Get Started Free
                <ArrowRight className="w-5 h-5" aria-hidden="true" />
              </button>
              <button
                onClick={handleSignUp}
                className="px-8 py-4 border border-gray-600 text-white font-semibold rounded-lg hover:bg-gray-800 transition-all duration-300"
                aria-label="Create your Fikiri Solutions account"
              >
                Create Account
              </button>
            </motion.div>
            <p className="text-sm text-white mt-4">
              No setup fees • Cancel anytime • 24/7 support
            </p>
            <p className="text-xs text-white/70 mt-2 max-w-xl mx-auto">
              Automate email follow-up and routine admin so owners and managers can focus on higher‑value work.
            </p>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 py-12 px-4 sm:px-6 lg:px-8 border-t border-gray-800">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div>
              <h3 className="text-xl font-bold mb-4 bg-gradient-to-r from-orange-400 via-orange-500 to-blue-500 bg-clip-text text-transparent">Fikiri Solutions</h3>
              <p className="text-white">
                AI-powered automation for small businesses
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Product</h4>
              <ul className="space-y-2 text-white">
                <li><button onClick={() => window.location.href = '/services'} className="hover:text-orange-200 transition-colors">Services</button></li>
                <li><button onClick={() => window.location.href = '/ai'} className="hover:text-orange-200 transition-colors">AI Assistant</button></li>
                <li><button onClick={() => window.location.href = '/crm'} className="hover:text-orange-200 transition-colors">CRM</button></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Company</h4>
              <ul className="space-y-2 text-white">
                <li><button onClick={() => window.location.href = '/about'} className="hover:text-orange-200 transition-colors">About</button></li>
                <li><button onClick={() => window.location.href = '/privacy'} className="hover:text-orange-200 transition-colors">Privacy</button></li>
                <li><button onClick={() => window.location.href = '/terms'} className="hover:text-orange-200 transition-colors">Terms</button></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Support</h4>
              <ul className="space-y-2 text-white">
                <li><button onClick={handleGetStarted} className="hover:text-orange-200 transition-colors">Get Started</button></li>
                <li><button onClick={handleSignIn} className="hover:text-orange-200 transition-colors">Sign In</button></li>
                <li><button onClick={handleSignUp} className="hover:text-orange-200 transition-colors">Sign Up</button></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-8 pt-8 text-center text-white">
            <p>&copy; {new Date().getFullYear()} Fikiri Solutions LLC. All rights reserved.</p>
          </div>
        </div>
      </footer>

      <MarketingChatWidget />
    </div>
  )
}

export default LandingPage
// Force deployment update Mon Sep 22 21:23:21 EDT 2025
// Force Vercel deployment update Mon Sep 22 21:42:37 EDT 2025
// Fix landing page loading issue - Wed Sep 25 19:00:00 EDT 2025
