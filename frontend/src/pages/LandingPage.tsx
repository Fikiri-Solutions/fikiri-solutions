import React, { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { motion, useInView } from 'framer-motion'
import { useRef } from 'react'
import SimpleAnimatedBackground from '../components/SimpleAnimatedBackground'
import { 
  ArrowRight, 
  Mail, 
  Users, 
  Brain, 
  BarChart3, 
  CheckCircle, 
  Play,
  Star
} from 'lucide-react'

const LandingPage: React.FC = () => {
  const navigate = useNavigate()

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

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-orange-900/20 to-red-900/20 text-white overflow-hidden relative">
      {/* Header Navigation */}
      <header className="relative z-20 w-full px-4 sm:px-6 lg:px-8 py-6">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <Link 
            to="/" 
            className="flex items-center space-x-3 hover:opacity-80 transition-opacity duration-200"
            aria-label="Fikiri Solutions - Return to homepage"
          >
            <div className="w-12 h-12 bg-gradient-to-r from-orange-600 to-red-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-2xl" aria-hidden="true">F</span>
            </div>
            <span className="text-2xl font-bold bg-gradient-to-r from-orange-400 via-red-500 to-orange-600 bg-clip-text text-transparent">
              Fikiri
            </span>
          </Link>
          
          <nav className="hidden md:flex items-center space-x-8">
            <a href="#features" className="text-gray-300 hover:text-white transition-colors">Features</a>
            <a href="#how-it-works" className="text-gray-300 hover:text-white transition-colors">How it works</a>
            <a href="#testimonials" className="text-gray-300 hover:text-white transition-colors">Testimonials</a>
            <a href="/pricing" className="text-gray-300 hover:text-white transition-colors">Pricing</a>
          </nav>

          <div className="flex items-center space-x-4">
            <button
              onClick={() => navigate('/login')}
              className="px-4 py-2 text-gray-300 hover:text-white transition-colors"
              aria-label="Sign in to your Fikiri account"
            >
              Sign in
            </button>
            <button
              onClick={() => navigate('/signup')}
              className="px-6 py-2 bg-gradient-to-r from-orange-600 to-red-600 text-white font-semibold rounded-lg hover:from-orange-700 hover:to-red-700 transition-all duration-300"
              aria-label="Get started with Fikiri Solutions - Create your account"
            >
              Get started
            </button>
          </div>
        </div>
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
            <h1 className="text-4xl sm:text-6xl lg:text-7xl font-bold mb-6 bg-gradient-to-r from-orange-400 via-red-500 to-orange-600 bg-clip-text text-transparent">
              The platform for
              <br />
              reliable automation
            </h1>
            <p className="text-xl sm:text-2xl text-gray-300 mb-8 max-w-3xl mx-auto">
              Save time, close more leads, and automate your workflows with Fikiri Solutions.
              <br />
              <span className="text-orange-400">Transform your business with intelligent automation.</span>
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={heroInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="flex flex-col sm:flex-row gap-4 justify-center items-center"
          >
            <button
              onClick={() => navigate('/onboarding-flow')}
              className="px-8 py-4 bg-gradient-to-r from-orange-600 to-red-600 text-white font-semibold rounded-lg hover:from-orange-700 hover:to-red-700 transition-all duration-300 transform hover:scale-105 flex items-center gap-2 shadow-lg"
              aria-label="Get started with Fikiri Solutions - Free trial"
            >
              Get Started Free
              <ArrowRight className="w-5 h-5" aria-hidden="true" />
            </button>
            <button 
              className="px-8 py-4 border border-gray-600 text-white font-semibold rounded-lg hover:bg-gray-800 transition-all duration-300 flex items-center gap-2"
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
                           <span className="text-gray-200 font-medium">{feature}</span>
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
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              Everything You Need to Automate Your Business
            </h2>
            <p className="text-xl text-gray-300 max-w-2xl mx-auto">
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
                <h3 className="text-xl font-semibold mb-2">{prop.title}</h3>
                <p className="text-gray-300">{prop.description}</p>
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
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              How It Works
            </h2>
            <p className="text-xl text-gray-300 max-w-2xl mx-auto">
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
                <h3 className="text-2xl font-semibold mb-4">{step.title}</h3>
                <p className="text-gray-300">{step.description}</p>
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
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              Trusted by Growing Businesses
            </h2>
            <p className="text-xl text-gray-300 max-w-2xl mx-auto">
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
                <p className="text-gray-300 mb-4 italic">"{testimonial.quote}"</p>
                <div>
                  <p className="font-semibold">{testimonial.name}</p>
                  <p className="text-gray-400 text-sm">{testimonial.company}</p>
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
            <p className="text-gray-400 mb-8">Powered by industry-leading technology</p>
            <div className="flex flex-wrap justify-center items-center gap-8 opacity-60">
              <div className="text-2xl font-bold">OpenAI</div>
              <div className="text-2xl font-bold">Google</div>
              <div className="text-2xl font-bold">Redis</div>
              <div className="text-2xl font-bold">Shopify</div>
              <div className="text-2xl font-bold">Microsoft</div>
              <div className="text-2xl font-bold">Stripe</div>
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
            <h2 className="text-3xl sm:text-4xl font-bold mb-6">
              Start Automating Today
            </h2>
            <p className="text-xl text-gray-300 mb-8">
              Free trial, no credit card required. Join thousands of businesses already saving time with AI.
            </p>
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={ctaInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
              transition={{ duration: 0.8, delay: 0.2 }}
              className="flex flex-col sm:flex-row gap-4 justify-center items-center"
            >
              <button
                onClick={() => navigate('/onboarding-flow')}
                className="px-8 py-4 bg-gradient-to-r from-orange-600 to-red-600 text-white font-semibold rounded-lg hover:from-orange-700 hover:to-red-700 transition-all duration-300 transform hover:scale-105 flex items-center gap-2 shadow-lg"
                aria-label="Get started with Fikiri Solutions - Free trial"
              >
                Get Started Free
                <ArrowRight className="w-5 h-5" aria-hidden="true" />
              </button>
              <button
                onClick={() => navigate('/signup')}
                className="px-8 py-4 border border-gray-600 text-white font-semibold rounded-lg hover:bg-gray-800 transition-all duration-300"
                aria-label="Create your Fikiri Solutions account"
              >
                Create Account
              </button>
            </motion.div>
            <p className="text-sm text-gray-400 mt-4">
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
              <h3 className="text-xl font-bold mb-4">Fikiri Solutions</h3>
              <p className="text-gray-400">
                AI-powered automation for small businesses
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Product</h4>
              <ul className="space-y-2 text-gray-400">
                <li><a href="/services" className="hover:text-white transition-colors">Services</a></li>
                <li><a href="/ai" className="hover:text-white transition-colors">AI Assistant</a></li>
                <li><a href="/crm" className="hover:text-white transition-colors">CRM</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Company</h4>
              <ul className="space-y-2 text-gray-400">
                <li><a href="/about" className="hover:text-white transition-colors">About</a></li>
                <li><a href="/privacy" className="hover:text-white transition-colors">Privacy</a></li>
                <li><a href="/terms" className="hover:text-white transition-colors">Terms</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Support</h4>
              <ul className="space-y-2 text-gray-400">
                <li><a href="/onboarding-flow" className="hover:text-white transition-colors">Get Started</a></li>
                <li><a href="/login" className="hover:text-white transition-colors">Sign In</a></li>
                <li><a href="/signup" className="hover:text-white transition-colors">Sign Up</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-8 pt-8 text-center text-gray-400">
            <p>&copy; 2024 Fikiri Solutions. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default LandingPage
// Force deployment update Mon Sep 22 21:23:21 EDT 2025
// Force Vercel deployment update Mon Sep 22 21:42:37 EDT 2025
