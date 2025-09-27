import React from 'react'
import { motion, useInView } from 'framer-motion'
import { useRef, useState } from 'react'
import SimpleAnimatedBackground from '../components/SimpleAnimatedBackground'
import { FikiriLogo } from '../components/FikiriLogo'
import DemoVideoModal from '../components/DemoVideoModal'
import { 
  ArrowRight, 
  Mail, 
  Users, 
  Brain, 
  BarChart3, 
  CheckCircle, 
  Play,
  Star,
  Menu,
  X
} from 'lucide-react'

const LandingPage: React.FC = () => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [isDemoVideoOpen, setIsDemoVideoOpen] = useState(false)

  const valueProps = [
    {
      icon: Mail,
      title: "Email Assistant",
      description: "Respond to leads instantly with AI-powered email automation"
    },
    {
      icon: Users,
      title: "CRM Automations",
      description: "Track and manage clients with intelligent workflow automation"
    },
    {
      icon: Brain,
      title: "AI Insights",
      description: "Predict opportunities and optimize your business processes"
    },
    {
      icon: BarChart3,
      title: "Seamless Integrations",
      description: "Connect with Gmail, Shopify, Outlook, and 50+ other tools"
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

  const testimonials = [
    {
      name: "Sarah Johnson",
      company: "Johnson Landscaping",
      quote: "Fikiri's AI assistant has transformed how we handle customer inquiries. Response time dropped from hours to minutes.",
      rating: 5
    },
    {
      name: "Mike Chen",
      company: "Chen's Restaurant Group", 
      quote: "The automation features saved us 20 hours per week. Our team can now focus on what matters most.",
      rating: 5
    },
    {
      name: "Dr. Emily Rodriguez",
      company: "Rodriguez Medical Practice",
      quote: "Patient communication has never been smoother. Fikiri handles appointment reminders and follow-ups perfectly.",
      rating: 5
    }
  ]

  const features = [
    "No credit card required",
    "14-day free trial",
    "Cancel anytime",
    "24/7 customer support"
  ]

  // Refs for scroll-triggered animations
  const heroRef = useRef(null)
  const valuePropsRef = useRef(null)
  const howItWorksRef = useRef(null)
  const testimonialsRef = useRef(null)
  const ctaRef = useRef(null)

  // Check if elements are in view
  const heroInView = useInView(heroRef, { once: true, margin: "-100px" })
  const valuePropsInView = useInView(valuePropsRef, { once: true, margin: "-100px" })
  const howItWorksInView = useInView(howItWorksRef, { once: true, margin: "-100px" })
  const testimonialsInView = useInView(testimonialsRef, { once: true, margin: "-100px" })
  const ctaInView = useInView(ctaRef, { once: true, margin: "-100px" })

  // Simple navigation handlers without router
  const handleGetStarted = () => {
    window.location.href = '/onboarding-flow'
  }

  const handleSignIn = () => {
    window.location.href = '/login'
  }

  const handleSignUp = () => {
    window.location.href = '/signup'
  }

  const handlePricing = () => {
    window.location.href = '/pricing'
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-orange-900/30 to-red-900/30 text-white overflow-hidden relative" style={{
      background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 20%, #FF6B35 40%, #D2691E 60%, #8B0000 80%, #991b1b 100%)'
    }}>
      {/* Header Navigation */}
      <header className="relative z-20 w-full px-4 sm:px-6 lg:px-8 py-6">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div 
            className="flex items-center space-x-3 hover:opacity-80 transition-opacity duration-200"
            aria-label="Fikiri Solutions - Return to homepage"
          >
            <FikiriLogo 
              size="xl" 
              variant="full" 
              animated={true}
              className="hover:scale-105 transition-transform duration-200"
            />
          </div>
          
          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-8">
            <a href="#features" className="text-white hover:text-orange-200 transition-colors">Features</a>
            <a href="#how-it-works" className="text-white hover:text-orange-200 transition-colors">How it works</a>
            <a href="#testimonials" className="text-white hover:text-orange-200 transition-colors">Testimonials</a>
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
                  href="#testimonials" 
                  className="block text-white hover:text-orange-200 transition-colors py-2"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Testimonials
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
              The platform for
              <br />
              reliable automation
            </h1>
            <p className="text-xl sm:text-2xl text-white mb-8 max-w-3xl mx-auto">
              Save time, close more leads, and automate your workflows with Fikiri Solutions.
              <br />
              <span className="text-orange-300 font-medium">Transform your business with intelligent automation.</span>
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
              onClick={() => setIsDemoVideoOpen(true)}
              className="px-8 py-4 border border-orange-400 text-white font-semibold rounded-lg hover:bg-orange-500/20 hover:border-orange-300 transition-all duration-300 flex items-center gap-2"
              aria-label="Watch Fikiri Solutions demo video"
            >
              <Play className="w-5 h-5" aria-hidden="true" />
              Watch Demo
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
              Everything You Need to Automate Your Business
            </h2>
            <p className="text-xl text-gray-100 max-w-2xl mx-auto">
              Powerful AI tools designed specifically for small businesses
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
              How It Works
            </h2>
            <p className="text-xl text-white max-w-2xl mx-auto">
              Get started in minutes, see results immediately
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

      {/* Social Proof Section */}
      <section ref={testimonialsRef} id="testimonials" className="relative z-10 py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={testimonialsInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl sm:text-4xl font-bold mb-4 bg-gradient-to-r from-orange-400 via-orange-500 to-blue-500 bg-clip-text text-transparent">
              Trusted by Growing Businesses
            </h2>
            <p className="text-xl text-white max-w-2xl mx-auto">
              Join thousands of businesses already automating with Fikiri
            </p>
          </motion.div>

          {/* Testimonials */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
            {testimonials.map((testimonial, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 30 }}
                animate={testimonialsInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6 border border-gray-700"
              >
                <div className="flex mb-4">
                  {[...Array(testimonial.rating)].map((_, i) => (
                    <Star key={i} className="w-5 h-5 text-yellow-400 fill-current" />
                  ))}
                </div>
                <p className="text-white mb-4 italic">"{testimonial.quote}"</p>
                <div>
                  <p className="font-semibold text-white">{testimonial.name}</p>
                  <p className="text-orange-200 text-sm">{testimonial.company}</p>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Tech Stack Logos */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={testimonialsInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
            transition={{ duration: 0.8 }}
            className="text-center"
          >
            <p className="text-white mb-8">Powered by industry-leading technology</p>
            <div className="flex flex-wrap justify-center items-center gap-8 opacity-80">
              <div className="text-2xl font-bold text-white">OpenAI</div>
              <div className="text-2xl font-bold text-white">Google</div>
              <div className="text-2xl font-bold text-white">Redis</div>
              <div className="text-2xl font-bold text-white">Shopify</div>
              <div className="text-2xl font-bold text-white">Microsoft</div>
              <div className="text-2xl font-bold text-white">Stripe</div>
            </div>
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
              Start Automating Today
            </h2>
            <p className="text-xl text-white mb-8">
              Free trial, no credit card required. Join thousands of businesses already saving time with AI.
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
            <p>&copy; 2024 Fikiri Solutions. All rights reserved.</p>
          </div>
        </div>
      </footer>

      {/* Demo Video Modal */}
      <DemoVideoModal 
        isOpen={isDemoVideoOpen}
        onClose={() => setIsDemoVideoOpen(false)}
        videoUrl="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4" // Replace with your Kling AI generated video URL
      />
    </div>
  )
}

export default LandingPage
