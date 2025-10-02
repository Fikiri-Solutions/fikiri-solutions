import React, { useState, useEffect } from 'react'
import { Mail, Lock, ArrowRight, Zap, Shield, Rocket, Github, Chrome, UserPlus, Eye, EyeOff, Building2 } from 'lucide-react'
import { useUserActivityTracking } from '../contexts/ActivityContext'
import { useAuth } from '../contexts/AuthContext'
import { FikiriLogo } from '../components/FikiriLogo'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'

export const Login: React.FC = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [emailError, setEmailError] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [rememberMe, setRememberMe] = useState(false)
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 })
  const [isMicrosoftLoading, setIsMicrosoftLoading] = useState(false)
  const { trackLogin } = useUserActivityTracking()
  const { login, getRedirectPath } = useAuth()
  const navigate = useNavigate()

  // Load saved credentials on component mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      try {
        const savedEmail = localStorage.getItem('fikiri-remember-email')
        const savedPassword = localStorage.getItem('fikiri-remember-password')
        const savedRememberMe = localStorage.getItem('fikiri-remember-me')
        
        if (savedEmail && savedPassword && savedRememberMe === 'true') {
          setEmail(savedEmail)
          setPassword(savedPassword)
          setRememberMe(true)
        }
      } catch (error) {
        console.error('Error loading saved credentials:', error)
      }
    }
  }, [])

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
      // Validate inputs
      if (!email || !password) {
        throw new Error('Please enter both email and password')
      }
      
      if (!validateEmail(email)) {
        throw new Error('Please enter a valid email address')
      }
      
      if (password.length < 6) {
        throw new Error('Password must be at least 6 characters')
      }
      
      // Attempt login using auth context
      const result = await login(email, password)
      
      if (result.success) {
        // Handle remember me functionality
        if (typeof window !== 'undefined') {
          try {
            if (rememberMe) {
              localStorage.setItem('fikiri-remember-email', email)
              localStorage.setItem('fikiri-remember-password', password)
              localStorage.setItem('fikiri-remember-me', 'true')
            } else {
              localStorage.removeItem('fikiri-remember-email')
              localStorage.removeItem('fikiri-remember-password')
              localStorage.removeItem('fikiri-remember-me')
            }
          } catch (error) {
            console.error('Error saving credentials:', error)
          }
        }
        
        // Track successful login
        trackLogin(email, 'email')
        
        // Get the appropriate redirect path based on user state
        const redirectPath = getRedirectPath()
        navigate(redirectPath)
      } else {
        setError(result.error || 'Login failed. Please try again.')
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Login failed. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleMicrosoftLogin = async () => {
    setIsMicrosoftLoading(true)
    setError('')
    
    try {
      // Get user ID from localStorage or create a temporary one
      let userId = localStorage.getItem('fikiri-user-id')
      if (!userId) {
        userId = 'temp_' + Date.now()
        localStorage.setItem('fikiri-user-id', userId)
      }
      
      // Call Microsoft connect endpoint
      const response = await fetch('https://fikirisolutions.onrender.com/api/auth/microsoft/connect', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_id: userId })
      })
      
      const data = await response.json()
      
      if (data.success && data.auth_url) {
        // Track Microsoft login attempt
        trackLogin('microsoft', 'oauth')
        
        // Redirect to Microsoft OAuth
        window.location.href = data.auth_url
      } else {
        throw new Error(data.error || 'Failed to initiate Microsoft login')
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Microsoft login failed. Please try again.')
    } finally {
      setIsMicrosoftLoading(false)
    }
  }

  return (
    <div id="main-content" className="min-h-screen relative overflow-hidden fikiri-gradient-animated">
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
              <FikiriLogo size="xl" variant="full" className="mx-auto" />
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
              <p className="text-white text-center text-sm font-light opacity-80">
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
                      <Mail className="h-5 w-5 text-gray-500" />
                    </div>
                    <input
                      id="email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      required
                      className={`w-full pl-12 pr-4 py-3 bg-white border border-gray-300 rounded-xl text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-all duration-200 ${emailError ? 'border-red-500 focus:ring-red-500' : ''}`}
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
                      <Lock className="h-5 w-5 text-gray-500" />
                    </div>
                    <input
                      id="password"
                      name="password"
                      type={showPassword ? "text" : "password"}
                      autoComplete="current-password"
                      required
                      className={`w-full pl-12 pr-12 py-3 bg-white border border-gray-300 rounded-xl text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-all duration-200 ${passwordError ? 'border-red-500 focus:ring-red-500' : ''}`}
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
                        <EyeOff className="h-5 w-5 text-gray-500 hover:text-gray-700" />
                      ) : (
                        <Eye className="h-5 w-5 text-gray-500 hover:text-gray-700" />
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
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="h-4 w-4 text-brand-accent focus:ring-brand-accent border-gray-300 rounded bg-white/10"
                  />
                  <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-200">
                    Remember me
                  </label>
                </div>

                <div className="text-sm">
                  <button
                    type="button"
                    onClick={() => navigate('/forgot-password')}
                    className="font-medium text-white hover:text-gray-200 transition-colors"
                  >
                    Forgot password?
                  </button>
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
                    <span className="px-2 bg-transparent text-white opacity-70">Or continue with</span>
                  </div>
              </div>

              <div className="mt-6 grid grid-cols-3 gap-3">
                <button
                  type="button"
                  className="w-full inline-flex justify-center py-3 px-4 border border-white/20 rounded-xl shadow-sm bg-white/10 text-sm font-medium text-white hover:bg-white/20 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-accent transition-all duration-200"
                >
                  <Chrome className="h-5 w-5 mr-2" />
                  Gmail
                </button>

                <button
                  type="button"
                  onClick={handleMicrosoftLogin}
                  disabled={isMicrosoftLoading}
                  className="w-full inline-flex justify-center py-3 px-4 border border-white/20 rounded-xl shadow-sm bg-white/10 text-sm font-medium text-white hover:bg-white/20 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-accent transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Building2 className="h-5 w-5 mr-2" />
                  {isMicrosoftLoading ? 'Connecting...' : 'Microsoft'}
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
              <p className="text-xs text-white opacity-60 text-center mb-4">Powered by AI</p>
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
          </motion.div>

        </div>
      </div>
    </div>
  )
}