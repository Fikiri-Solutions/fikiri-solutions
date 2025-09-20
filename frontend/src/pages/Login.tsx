import React, { useState, useEffect } from 'react'
import { Mail, Lock, ArrowRight, Zap, Sparkles, Shield, Rocket, Github, Chrome, UserPlus, Eye, EyeOff } from 'lucide-react'
import { useUserActivityTracking } from '../contexts/ActivityContext'
import { FikiriLogo } from '../components/FikiriLogo'
import { motion } from 'framer-motion'

export const Login: React.FC = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [emailError, setEmailError] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 })
  const { trackLogin } = useUserActivityTracking()

  // Track mouse position for interactive background
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMousePosition({ x: e.clientX, y: e.clientY })
    }
    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [])

  const validateEmail = (email: string) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return emailRegex.test(email)
  }

  const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setEmail(value)
    setEmailError('')
    
    if (value && !validateEmail(value)) {
      setEmailError('Please enter a valid email address')
    }
  }

  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setPassword(value)
    setPasswordError('')
    
    if (value && value.length < 6) {
      setPasswordError('Password must be at least 6 characters')
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')
    
    try {
      // Implement login API call
      
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      // Simulate validation
      if (!email || !password) {
        throw new Error('Please enter both email and password')
      }
      
      // For demo purposes, allow any valid email/password combination
      if (validateEmail(email) && password.length >= 6) {
        // Track successful login
        trackLogin(email, 'email')
        
        // Redirect to dashboard
        window.location.href = '/'
        return
      }
      
      // TODO: Implement real authentication API
      throw new Error('Authentication service not yet implemented')
    } catch (error) {
      // Login failed
      setError(error instanceof Error ? error.message : 'Login failed. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen relative overflow-hidden fikiri-gradient-animated">
      {/* Enhanced Animated Background Elements */}
      <div className="absolute inset-0">
        {/* Floating orbs with brand colors */}
        <motion.div 
          className="absolute w-72 h-72 bg-brand-accent/20 rounded-full blur-3xl"
          animate={{
            x: mousePosition.x * 0.1,
            y: mousePosition.y * 0.1,
            scale: [1, 1.1, 1],
          }}
          transition={{
            duration: 4,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        <motion.div 
          className="absolute w-96 h-96 bg-brand-secondary/20 rounded-full blur-3xl"
          animate={{
            x: mousePosition.x * 0.05,
            y: mousePosition.y * 0.05,
            scale: [1.1, 1, 1.1],
          }}
          transition={{
            duration: 6,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        <motion.div 
          className="absolute w-64 h-64 bg-brand-primary/20 rounded-full blur-3xl"
          animate={{
            x: mousePosition.x * 0.08,
            y: mousePosition.y * 0.1,
            scale: [1, 1.2, 1],
          }}
          transition={{
            duration: 5,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        
        {/* Geometric shapes */}
        <motion.div
          className="absolute top-20 left-20 w-32 h-32 border-2 border-white/10 rounded-lg"
          animate={{
            rotate: [0, 90, 180, 270, 360],
            scale: [1, 1.1, 1],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: "linear"
          }}
        />
        <motion.div
          className="absolute bottom-32 right-32 w-24 h-24 bg-brand-accent/10 rounded-full"
          animate={{
            y: [-20, 20, -20],
            x: [-10, 10, -10],
          }}
          transition={{
            duration: 7,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        <motion.div
          className="absolute top-1/2 right-20 w-16 h-16 border-2 border-brand-secondary/20 rounded-full"
          animate={{
            rotate: [0, 180, 360],
            scale: [1, 1.2, 1],
          }}
          transition={{
            duration: 6,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        
        {/* Grid pattern */}
        <div className="absolute inset-0 opacity-20" style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.1'%3E%3Ccircle cx='30' cy='30' r='1'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`
        }} />
        
        {/* Floating particles */}
        {[...Array(30)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-2 h-2 bg-white/30 rounded-full"
            animate={{
              y: [-20, 20, -20],
              x: [-10, 10, -10],
              opacity: [0.3, 0.8, 0.3],
            }}
            transition={{
              duration: 3 + Math.random() * 2,
              repeat: Infinity,
              ease: "easeInOut",
              delay: Math.random() * 2,
            }}
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
            }}
          />
        ))}
      </div>

      {/* Main Content */}
      <div className="relative z-10 min-h-screen flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full">
          {/* Logo and Branding */}
          <motion.div 
            className="text-center mb-8"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="flex items-center justify-center mb-6">
              <FikiriLogo size="xl" variant="white" className="mx-auto" />
            </div>
            <motion.h1 
              className="text-5xl font-bold text-white mb-2 font-serif tracking-tight"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
            >
              Fikiri Solutions
            </motion.h1>
            <motion.p 
              className="text-xl text-white/90 mb-1 font-medium"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
            >
              AI-Powered Business Automation
            </motion.p>
            <motion.p 
              className="text-sm text-white/70 font-light"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
            >
              Transform your business with intelligent automation
            </motion.p>
          </motion.div>

          {/* Login Form */}
          <motion.div 
            className="bg-white/10 backdrop-blur-xl rounded-3xl p-8 shadow-2xl border border-white/20"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.5 }}
          >
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-white text-center mb-2 font-serif">
                Welcome Back
              </h2>
              <p className="text-gray-300 text-center text-sm font-light">
                Sign in to continue your automation journey
              </p>
            </div>
            
            <form className="space-y-6" onSubmit={handleSubmit}>
              {error && (
                <div className="bg-red-500/20 border border-red-500/50 rounded-xl p-4 backdrop-blur-sm">
                  <p className="text-sm text-red-200">{error}</p>
                </div>
              )}
              
              <div className="space-y-4">
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-200 mb-2">
                    Email Address
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                      <Mail className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                      id="email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      required
                      className={`w-full pl-12 pr-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-accent focus:border-transparent transition-all duration-200 backdrop-blur-sm ${emailError ? 'border-brand-error focus:ring-brand-error' : ''}`}
                      placeholder="Enter your email"
                      value={email}
                      onChange={handleEmailChange}
                    />
                  </div>
                  {emailError && (
                    <p className="mt-2 text-sm text-red-300">{emailError}</p>
                  )}
                </div>
                
                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-gray-200 mb-2">
                    Password
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                      <Lock className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                      id="password"
                      name="password"
                      type={showPassword ? "text" : "password"}
                      autoComplete="current-password"
                      required
                      className={`w-full pl-12 pr-12 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-accent focus:border-transparent transition-all duration-200 backdrop-blur-sm ${passwordError ? 'border-brand-error focus:ring-brand-error' : ''}`}
                      placeholder="Enter your password"
                      value={password}
                      onChange={handlePasswordChange}
                    />
                    <button
                      type="button"
                      className="absolute inset-y-0 right-0 pr-4 flex items-center"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? (
                        <EyeOff className="h-5 w-5 text-gray-400 hover:text-gray-300" />
                      ) : (
                        <Eye className="h-5 w-5 text-gray-400 hover:text-gray-300" />
                      )}
                    </button>
                  </div>
                  {passwordError && (
                    <p className="mt-2 text-sm text-red-300">{passwordError}</p>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <input
                    id="remember-me"
                    name="remember-me"
                    type="checkbox"
                    className="h-4 w-4 text-brand-accent focus:ring-brand-accent border-gray-300 rounded bg-white/10"
                  />
                  <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-200">
                    Remember me
                  </label>
                </div>

                <div className="text-sm">
                  <a href="#" className="font-medium text-white hover:text-gray-200 transition-colors">
                    Forgot password?
                  </a>
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex justify-center items-center py-3 px-4 border border-transparent rounded-xl shadow-sm text-sm font-medium text-white bg-gradient-to-r from-brand-primary to-brand-secondary hover:from-brand-secondary hover:to-brand-primary focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-accent disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 transform hover:scale-105"
              >
                {isLoading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Signing in...
                  </>
                ) : (
                  <>
                    Sign In
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </button>
            </form>

            {/* Social Login Options */}
            <div className="mt-6">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/20" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-transparent text-gray-300">Or continue with</span>
                </div>
              </div>

              <div className="mt-6 grid grid-cols-2 gap-3">
                <button
                  type="button"
                  className="w-full inline-flex justify-center py-3 px-4 border border-white/20 rounded-xl shadow-sm bg-white/10 text-sm font-medium text-white hover:bg-white/20 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-accent transition-all duration-200"
                >
                  <Chrome className="h-5 w-5 mr-2" />
                  Gmail
                </button>

                <button
                  type="button"
                  className="w-full inline-flex justify-center py-3 px-4 border border-white/20 rounded-xl shadow-sm bg-white/10 text-sm font-medium text-white hover:bg-white/20 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-accent transition-all duration-200"
                >
                  <Github className="h-5 w-5 mr-2" />
                  GitHub
                </button>
              </div>
            </div>

            {/* Sign Up Button */}
            <div className="mt-6 text-center">
              <button
                type="button"
                onClick={() => window.location.href = '/signup'}
                className="w-full inline-flex justify-center items-center py-3 px-4 border border-white/30 rounded-xl shadow-sm bg-white/20 text-sm font-medium text-white hover:bg-white/30 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-accent transition-all duration-200"
              >
                <UserPlus className="h-5 w-5 mr-2" />
                Create New Account
              </button>
            </div>

            {/* Features Preview */}
            <div className="mt-8 pt-6 border-t border-white/20">
              <p className="text-xs text-gray-400 text-center mb-4">Powered by AI</p>
              <div className="flex justify-center space-x-6">
                <div className="flex items-center space-x-2 text-white/80">
                  <Shield className="h-4 w-4 text-brand-accent" />
                  <span className="text-xs">Secure</span>
                </div>
                <div className="flex items-center space-x-2 text-white/80">
                  <Rocket className="h-4 w-4 text-brand-secondary" />
                  <span className="text-xs">Fast</span>
                </div>
                <div className="flex items-center space-x-2 text-white/80">
                  <Zap className="h-4 w-4 text-brand-primary" />
                  <span className="text-xs">Smart</span>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}