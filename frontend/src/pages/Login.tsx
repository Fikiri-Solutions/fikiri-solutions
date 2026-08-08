import React, { useState, useEffect, useTransition } from 'react'
import { Mail, Lock, ArrowRight, Zap, Shield, Rocket, Github, Chrome, UserPlus, Eye, EyeOff, Building2 } from 'lucide-react'
import { useUserActivityTracking } from '../contexts/ActivityContext'
import { useAuth } from '../contexts/AuthContext'
import { RadiantLayout } from '../components/radiant'
import { motion, useReducedMotion } from 'framer-motion'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { apiClient } from '../services/apiClient'
import { loadGmailLookbackId } from '../utils/gmailLookbackStorage'
import { AUTOCOMPLETE } from '../constants/autocomplete'

export const Login: React.FC = () => {
  const [rememberMe, setRememberMe] = useState(() => {
    if (typeof window === 'undefined') return false
    try {
      return localStorage.getItem('fikiri-remember-me') === 'true'
    } catch {
      return false
    }
  })
  const [email, setEmail] = useState(() => {
    if (typeof window === 'undefined') return ''
    try {
      if (localStorage.getItem('fikiri-remember-me') === 'true') {
        return localStorage.getItem('fikiri-remember-email') || ''
      }
    } catch { /* ignore */ }
    return ''
  })
  const [password, setPassword] = useState(() => {
    if (typeof window === 'undefined') return ''
    try {
      if (localStorage.getItem('fikiri-remember-me') === 'true') {
        return localStorage.getItem('fikiri-remember-password') || ''
      }
    } catch { /* ignore */ }
    return ''
  })
  const [error, setError] = useState('')
  const [emailError, setEmailError] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isMicrosoftLoading, setIsMicrosoftLoading] = useState(false)
  const [isPending, startTransition] = useTransition()
  const { trackLogin } = useUserActivityTracking()
  const { login: contextLogin, getRedirectPath, user } = useAuth()
  const navigate = useNavigate()
  const reduceMotion = useReducedMotion()
  const [searchParams] = useSearchParams()

  // When "Remember me" is checked and we have saved credentials, keep form in sync (e.g. after navigation)
  useEffect(() => {
    if (typeof window === 'undefined' || !rememberMe) return
    try {
      const savedEmail = localStorage.getItem('fikiri-remember-email')
      const savedPassword = localStorage.getItem('fikiri-remember-password')
      if (savedEmail && savedPassword) {
        setEmail((prev) => (prev !== savedEmail ? savedEmail : prev))
        setPassword((prev) => (prev !== savedPassword ? savedPassword : prev))
      }
    } catch (err) {
      console.error('Error loading saved credentials:', err)
    }
  }, [rememberMe])

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
      trackLogin('microsoft', 'oauth')
      const redirectUri = `${window.location.origin}/integrations/outlook`
      const result = await apiClient.startOutlookOAuth(redirectUri)
      if (result?.url) {
        window.location.href = result.url
        return
      }
      throw new Error(result?.error || 'Outlook OAuth not configured')
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Microsoft login failed. Please try again.')
    } finally {
      setIsMicrosoftLoading(false)
    }
  }

  const handleGmailLogin = async () => {
    setError('')
    try {
      trackLogin('gmail', 'oauth')
      const redirectUri = `${window.location.origin}/integrations/gmail`
      const result = await apiClient.startGmailOAuth(redirectUri, loadGmailLookbackId())
      if (result?.url) {
        window.location.href = result.url
        return
      }
      throw new Error(result?.error || 'Gmail OAuth not configured')
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Gmail login failed. Please try again.')
    }
  }

  return (
    <RadiantLayout showFooterCta={false} backdropIntensity="subtle">
    <div id="main-content" className="relative overflow-x-clip">
      {/* Static ambient wash — calm for auth focus */}
      <div className="absolute inset-0 pointer-events-none" aria-hidden>
        <div className="absolute -left-16 top-10 h-56 w-56 rounded-full bg-brand-accent/12 blur-3xl sm:h-72 sm:w-72" />
        <div className="absolute -right-20 top-40 h-64 w-64 rounded-full bg-brand-secondary/12 blur-3xl sm:h-96 sm:w-96" />
        <div className="absolute bottom-20 left-1/3 h-48 w-48 rounded-full bg-brand-primary/12 blur-3xl sm:h-64 sm:w-64" />
      </div>

      {/* Main Content */}
      <div className="relative z-10 flex items-start justify-center px-4 pb-10 pt-4 sm:items-center sm:px-6 sm:pb-16 sm:pt-8 lg:px-8">
        <motion.div
          className="max-w-md w-full min-w-0"
          initial={reduceMotion ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: reduceMotion ? 0 : 0.45, ease: 'easeOut' }}
        >
          {/* Branding — nav already has logo; keep compact page title */}
          <div className="mb-5 text-center sm:mb-6">
            <h1 className="mb-1 text-3xl font-bold font-serif tracking-tight text-white drop-shadow-sm sm:text-4xl">
              Welcome back
            </h1>
            <p className="text-base text-white/85 sm:text-lg">
              Sign in to continue
            </p>
          </div>

          {/* Login Form - solid card for contrast on gradient */}
          <div className="bg-white rounded-3xl p-5 shadow-2xl border border-white/40 ring-1 ring-black/5 sm:p-8">
            <div className="mb-6">
              <h2 className="text-xl font-bold text-stone-900 text-center mb-2 font-serif sm:text-2xl">
                Sign in
              </h2>
              <p className="text-stone-600 text-center text-sm">
                Use your Fikiri account email and password
              </p>
            </div>
            
            <form
              id="login-form"
              name="login"
              method="post"
              action="#"
              className="space-y-6"
              onSubmit={handleSubmit}
              autoComplete="on"
            >
              {error && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}
              
              <div className="space-y-4">
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-stone-800 mb-2">
                    Email Address
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                      <Mail className="h-5 w-5 text-stone-500" />
                    </div>
                    <input
                      id="email"
                      name="email"
                      type="email"
                      autoComplete={AUTOCOMPLETE.login.identifier}
                      required
                      className={`w-full pl-12 pr-4 py-3 bg-stone-50 border border-stone-300 rounded-xl text-stone-900 placeholder:text-stone-500 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition-all duration-200 ${emailError ? 'border-red-500 focus:ring-red-500' : ''}`}
                      placeholder="Enter your email"
                      value={email}
                      onChange={handleEmailChange}
                    />
                  </div>
                  {emailError && (
                    <p className="mt-2 text-sm font-medium text-red-700">{emailError}</p>
                  )}
                </div>
                
                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-stone-800 mb-2">
                    Password
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                      <Lock className="h-5 w-5 text-stone-500" />
                    </div>
                    <input
                      id="password"
                      name="password"
                      type={showPassword ? "text" : "password"}
                      autoComplete={AUTOCOMPLETE.login.password}
                      required
                      className={`w-full pl-12 pr-12 py-3 bg-stone-50 border border-stone-300 rounded-xl text-stone-900 placeholder:text-stone-500 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition-all duration-200 ${passwordError ? 'border-red-500 focus:ring-red-500' : ''}`}
                      placeholder="Enter your password"
                      value={password}
                      onChange={handlePasswordChange}
                    />
                    <button
                      type="button"
                      className="absolute inset-y-0 right-0 min-w-[44px] flex items-center justify-center pr-2 touch-manipulation"
                      onClick={() => setShowPassword(!showPassword)}
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? (
                        <EyeOff className="h-5 w-5 text-stone-500 hover:text-stone-800" />
                      ) : (
                        <Eye className="h-5 w-5 text-stone-500 hover:text-stone-800" />
                      )}
                    </button>
                  </div>
                  {passwordError && (
                    <p className="mt-2 text-sm font-medium text-red-700">{passwordError}</p>
                  )}
                </div>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center">
                  <input
                    id="remember-me"
                    name="remember-me"
                    type="checkbox"
                    autoComplete={AUTOCOMPLETE.off}
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="h-4 w-4 text-brand-primary focus:ring-brand-primary border-stone-300 rounded"
                    aria-describedby="remember-me-label"
                  />
                  <label id="remember-me-label" htmlFor="remember-me" className="ml-2 block text-sm text-stone-800">
                    Remember me
                  </label>
                </div>

                <div className="text-sm">
                  <button
                    type="button"
                    onClick={() => navigate('/forgot-password')}
                    className="font-semibold text-orange-800 hover:text-orange-700 transition-colors"
                  >
                    Forgot password?
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={isPending}
                className="w-full min-h-[44px] touch-manipulation flex justify-center items-center gap-2 py-3 px-4 border border-transparent rounded-xl shadow-sm text-sm font-medium text-white bg-brand-primary hover:bg-fikiri-400 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-primary disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
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
                  <span className="px-2 bg-white text-stone-600">Or continue with</span>
                </div>
              </div>

              <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
                <button
                  type="button"
                  onClick={handleGmailLogin}
                  className="w-full min-h-[44px] touch-manipulation inline-flex items-center justify-center gap-2 py-3 px-3 sm:px-4 border border-stone-300 rounded-xl shadow-sm bg-white text-sm font-medium text-stone-800 hover:bg-stone-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-primary transition-colors duration-200"
                >
                  <Chrome className="h-5 w-5 shrink-0" aria-hidden />
                  <span className="truncate">Gmail</span>
                </button>

                <button
                  type="button"
                  onClick={handleMicrosoftLogin}
                  disabled={isMicrosoftLoading}
                  className="w-full min-h-[44px] touch-manipulation inline-flex items-center justify-center gap-2 py-3 px-3 sm:px-4 border border-stone-300 rounded-xl shadow-sm bg-white text-sm font-medium text-stone-800 hover:bg-stone-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-primary transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Building2 className="h-5 w-5 shrink-0" aria-hidden />
                  <span className="truncate">{isMicrosoftLoading ? 'Connecting...' : 'Microsoft'}</span>
                </button>

                <button
                  type="button"
                  disabled
                  title="Coming soon"
                  className="w-full min-h-[44px] touch-manipulation inline-flex items-center justify-center gap-2 py-3 px-3 sm:px-4 border border-stone-200 rounded-xl shadow-sm bg-stone-100 text-sm font-medium text-stone-500 cursor-not-allowed"
                >
                  <Github className="h-5 w-5 shrink-0" aria-hidden />
                  <span className="truncate">GitHub (soon)</span>
                </button>
              </div>
            </div>

            {/* Sign Up Button */}
            <div className="mt-6 text-center">
              <button
                type="button"
                onClick={() => window.location.href = '/signup'}
                className="w-full min-h-[44px] touch-manipulation inline-flex justify-center items-center gap-2 py-3 px-4 border border-stone-300 rounded-xl shadow-sm bg-stone-50 text-sm font-medium text-stone-800 hover:bg-stone-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-primary transition-colors duration-200"
              >
                <UserPlus className="h-5 w-5 shrink-0" aria-hidden />
                <span>Create New Account</span>
              </button>
            </div>

            {/* Features Preview */}
            <div className="mt-8 pt-6 border-t border-gray-200">
              <p className="text-xs text-stone-600 text-center mb-4">Powered by AI</p>
              <div className="flex justify-center space-x-6">
                <div className="flex items-center space-x-2 text-stone-700">
                  <Shield className="h-4 w-4 text-brand-primary" />
                  <span className="text-xs font-medium">Secure</span>
                </div>
                <div className="flex items-center space-x-2 text-stone-700">
                  <Rocket className="h-4 w-4 text-brand-primary" />
                  <span className="text-xs font-medium">Fast</span>
                </div>
                <div className="flex items-center space-x-2 text-stone-700">
                  <Zap className="h-4 w-4 text-brand-primary" />
                  <span className="text-xs font-medium">Smart</span>
                </div>
              </div>
            </div>
          </div>

        </motion.div>
      </div>
    </div>
    </RadiantLayout>
  )
}
