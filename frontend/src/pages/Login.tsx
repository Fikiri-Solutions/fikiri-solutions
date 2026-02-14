import React, { useState, useEffect, useTransition } from 'react'
import { Link } from 'react-router-dom'
import { Mail, Lock, ArrowRight, Zap, Shield, Rocket, Github, Chrome, UserPlus, Eye, EyeOff, Building2 } from 'lucide-react'
import { useUserActivityTracking } from '../contexts/ActivityContext'
import { useAuth } from '../contexts/AuthContext'
import { FikiriLogo } from '../components/FikiriLogo'
import { RadiantLayout } from '../components/radiant'
import { motion } from 'framer-motion'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { apiClient } from '../services/apiClient'

export const Login: React.FC = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [emailError, setEmailError] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [rememberMe, setRememberMe] = useState(false)
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 })
  const [isMicrosoftLoading, setIsMicrosoftLoading] = useState(false)
  const [isPending, startTransition] = useTransition()
  const { trackLogin } = useUserActivityTracking()
  const { login: contextLogin, getRedirectPath, user } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

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
    console.log('🎯 handleSubmit called!', { 
      email: email ? 'provided' : 'missing', 
      passwordLength: password.length,
      emailValue: email,
      timestamp: new Date().toISOString()
    })
    e.preventDefault()
    e.stopPropagation()
    
    // Validate inputs
    setError('')

    if (!email || !password) {
      console.warn('⚠️ Validation failed: missing email or password')
      setError('Please enter both email and password')
      return
    }
    
    if (!validateEmail(email)) {
      console.warn('⚠️ Validation failed: invalid email format')
      setError('Please enter a valid email address')
      return
    }
    
    if (password.length < 6) {
      console.warn('⚠️ Validation failed: password too short')
      setError('Password must be at least 6 characters')
      return
    }
    
    console.log('✅ Validation passed, starting login...')
    
    startTransition(() => {
      const performLogin = async () => {
      console.log('🚀 Login attempt started:', { 
        email: email ? 'provided' : 'missing', 
        hasPassword: !!password,
        timestamp: new Date().toISOString()
      })
      try {
        // Attempt login via AuthContext to stay in sync with RouteGuard
        console.log('📞 Calling contextLogin...', { email, passwordLength: password.length })
        let result
        try {
          result = await contextLogin(email, password)
        } catch (loginError: any) {
          console.error('❌ contextLogin threw an error:', loginError)
          console.error('❌ Error details:', {
            message: loginError?.message,
            stack: loginError?.stack,
            response: loginError?.response?.data
          })
          setError(loginError?.message || 'Login failed. Please check your credentials.')
          return
        }
        console.log('📞 contextLogin result:', { success: result.success, hasUser: !!result.user, error: result.error })
        if (!result.success) {
          setError(result.error || 'Login failed. Please try again.')
          return // Exit early on failure
        }
        
        if (!result.user) {
          setError('Login succeeded but user data is missing. Please try again.')
          return
        }
        
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

        const nextUser = result.user ?? user
        
        // Check for redirect parameter in URL (e.g., /login?redirect=/inbox)
        const redirectParam = searchParams.get('redirect')
        const safeRedirect = redirectParam && redirectParam.startsWith('/') && !redirectParam.startsWith('//')
          ? redirectParam
          : null

        // Wait a moment for auth state to fully update in context and localStorage to be written
        await new Promise(resolve => setTimeout(resolve, 300))
        
        // Re-check user from auth context (may have been updated)
        const currentUser = result.user ?? user
        
        // Double-check localStorage is set (critical for page reload)
        const verifyUser = localStorage.getItem('fikiri-user')
        const verifyUserId = localStorage.getItem('fikiri-user-id')
        if (!verifyUser || !verifyUserId) {
          console.error('❌ localStorage not set after login, retrying...')
          // Retry saving to localStorage
          if (result.user) {
            localStorage.setItem('fikiri-user', JSON.stringify(result.user))
            localStorage.setItem('fikiri-user-id', result.user.id.toString())
          }
        }
        
        // Determine final destination
        let finalDestination = '/dashboard'
        if (currentUser?.onboarding_completed) {
          // User has completed onboarding - use redirect param if available
          if (safeRedirect && safeRedirect !== '/login' && safeRedirect !== '/signup') {
            finalDestination = safeRedirect
          }
        } else {
          // User hasn't completed onboarding - go to onboarding
          if (safeRedirect) {
            finalDestination = `/onboarding?redirect=${encodeURIComponent(safeRedirect)}`
          } else {
            finalDestination = '/onboarding'
          }
        }
        
        // Verify localStorage one more time before redirect (reuse variables from earlier check)
        console.log('🔍 Final localStorage check before redirect:', {
          hasUser: !!verifyUser,
          hasUserId: !!verifyUserId,
          userLength: verifyUser?.length || 0
        })
        
        if (!verifyUser || !verifyUserId) {
          console.error('❌ CRITICAL: localStorage is empty before redirect! Login will fail.')
          setError('Login succeeded but failed to save session. Please try again.')
          return
        }
        
        // Ensure auth context is updated before redirect
        // Force a re-check of auth status to update context state
        await new Promise(resolve => setTimeout(resolve, 100))
        
        // Use React Router navigate instead of window.location to avoid race conditions
        // This allows RouteGuard to properly check auth state from context
        console.log('✅ Login successful, redirecting to:', finalDestination)
        console.log('User data:', currentUser)
        console.log('✅ localStorage verified - proceeding with redirect')
        
        // Clear any redirect params from URL before navigating
        navigate(finalDestination, { replace: true })
        
      } catch (error: any) {
        if (error.message?.includes('429') || error.message?.includes('rate limit') || error.message?.includes('Too many login attempts')) {
          // Error message already includes retry time from AuthContext
          setError(error.message || 'Too many login attempts. Please wait 15 minutes and try again.')
        } else if (error.message?.includes('Unauthorized')) {
          setError('Invalid email or password. Please try again.')
        } else {
          setError(error.message || 'Login failed. Please try again.')
        }
      }
    }
    
    performLogin()
    })
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
      
      const data = await apiClient.request<{ success: boolean; auth_url?: string; error?: string }>(
        'POST',
        '/auth/microsoft/connect',
        { data: { user_id: userId } }
      )

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
    <RadiantLayout>
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
              <Link 
                to={user ? "/dashboard" : "/"}
                className="cursor-pointer hover:opacity-80 transition-opacity"
                aria-label={user ? "Fikiri Solutions - Go to dashboard" : "Fikiri Solutions - Return to homepage"}
              >
                <FikiriLogo size="xl" variant="full" className="mx-auto" />
              </Link>
            </div>
            <motion.h1 
              className="text-5xl font-bold text-gray-900 mb-2 font-serif tracking-tight drop-shadow-sm"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
            >
              Fikiri Solutions
            </motion.h1>
            <motion.p 
              className="text-xl text-gray-800 mb-1 font-medium"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
            >
              AI-Powered Business Automation
            </motion.p>
            <motion.p 
              className="text-sm text-gray-600 font-light"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
            >
              Transform your business with intelligent automation
            </motion.p>
          </motion.div>

          {/* Login Form - solid card for contrast on gradient */}
          <motion.div 
            className="bg-white rounded-3xl p-8 shadow-2xl border border-gray-200/80"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.5 }}
          >
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-900 text-center mb-2 font-serif">
                Welcome Back
              </h2>
              <p className="text-gray-600 text-center text-sm font-light">
                Sign in to continue your automation journey
              </p>
            </div>
            
            <form className="space-y-6" onSubmit={handleSubmit}>
              {error && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}
              
              <div className="space-y-4">
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
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
                      className={`w-full pl-12 pr-4 py-3 bg-gray-50 border border-gray-300 rounded-xl text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition-all duration-200 ${emailError ? 'border-red-500 focus:ring-red-500' : ''}`}
                      placeholder="Enter your email"
                      value={email}
                      onChange={handleEmailChange}
                    />
                  </div>
                  {emailError && (
                    <p className="mt-2 text-sm text-red-600">{emailError}</p>
                  )}
                </div>
                
                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
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
                      className={`w-full pl-12 pr-12 py-3 bg-gray-50 border border-gray-300 rounded-xl text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition-all duration-200 ${passwordError ? 'border-red-500 focus:ring-red-500' : ''}`}
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
                    <p className="mt-2 text-sm text-red-600">{passwordError}</p>
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
                    className="h-4 w-4 text-brand-primary focus:ring-brand-primary border-gray-300 rounded"
                  />
                  <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-700">
                    Remember me
                  </label>
                </div>

                <div className="text-sm">
                  <button
                    type="button"
                    onClick={() => navigate('/forgot-password')}
                    className="font-medium text-brand-primary hover:text-fikiri-400 transition-colors"
                  >
                    Forgot password?
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={isPending}
                className="w-full flex justify-center items-center py-3 px-4 border border-transparent rounded-xl shadow-sm text-sm font-medium text-white bg-brand-primary hover:bg-fikiri-400 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-primary disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
              >
                {isPending ? (
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
                  <div className="w-full border-t border-gray-200" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-white text-gray-500">Or continue with</span>
                </div>
              </div>

              <div className="mt-6 grid grid-cols-3 gap-3">
                <button
                  type="button"
                  className="w-full inline-flex justify-center py-3 px-4 border border-gray-300 rounded-xl shadow-sm bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-primary transition-all duration-200"
                >
                  <Chrome className="h-5 w-5 mr-2" />
                  Gmail
                </button>

                <button
                  type="button"
                  onClick={handleMicrosoftLogin}
                  disabled={isMicrosoftLoading}
                  className="w-full inline-flex justify-center py-3 px-4 border border-gray-300 rounded-xl shadow-sm bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-primary transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Building2 className="h-5 w-5 mr-2" />
                  {isMicrosoftLoading ? 'Connecting...' : 'Microsoft'}
                </button>

                <button
                  type="button"
                  className="w-full inline-flex justify-center py-3 px-4 border border-gray-300 rounded-xl shadow-sm bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-primary transition-all duration-200"
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
                className="w-full inline-flex justify-center items-center py-3 px-4 border border-gray-300 rounded-xl shadow-sm bg-gray-50 text-sm font-medium text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-primary transition-all duration-200"
              >
                <UserPlus className="h-5 w-5 mr-2" />
                Create New Account
              </button>
            </div>

            {/* Features Preview */}
            <div className="mt-8 pt-6 border-t border-gray-200">
              <p className="text-xs text-gray-500 text-center mb-4">Powered by AI</p>
              <div className="flex justify-center space-x-6">
                <div className="flex items-center space-x-2 text-gray-600">
                  <Shield className="h-4 w-4 text-brand-primary" />
                  <span className="text-xs">Secure</span>
                </div>
                <div className="flex items-center space-x-2 text-gray-600">
                  <Rocket className="h-4 w-4 text-brand-primary" />
                  <span className="text-xs">Fast</span>
                </div>
                <div className="flex items-center space-x-2 text-gray-600">
                  <Zap className="h-4 w-4 text-brand-primary" />
                  <span className="text-xs">Smart</span>
                </div>
              </div>
            </div>
          </motion.div>

        </div>
      </div>
    </div>
    </RadiantLayout>
  )
}
