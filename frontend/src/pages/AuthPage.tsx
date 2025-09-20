import React, { useState, useEffect } from 'react'
import { Eye, EyeOff, AlertCircle, CheckCircle, Loader2, Mail, Lock, User } from 'lucide-react'
import { FikiriLogo } from '../components/FikiriLogo'

interface SignupFormData {
  name: string
  email: string
  password: string
  confirmPassword: string
  businessName: string
  industry: string
  teamSize: string
}

interface LoginFormData {
  email: string
  password: string
}

export const AuthPage: React.FC = () => {
  const [isSignup, setIsSignup] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [success, setSuccess] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const [signupData, setSignupData] = useState<SignupFormData>({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    businessName: '',
    industry: '',
    teamSize: ''
  })

  const [loginData, setLoginData] = useState<LoginFormData>({
    email: '',
    password: ''
  })

  // Prevent double submits
  useEffect(() => {
    if (isSubmitting) {
      const timer = setTimeout(() => setIsSubmitting(false), 2000)
      return () => clearTimeout(timer)
    }
  }, [isSubmitting])

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return emailRegex.test(email)
  }

  const validatePassword = (password: string): { valid: boolean; message?: string } => {
    if (password.length < 8) {
      return { valid: false, message: 'Password must be at least 8 characters' }
    }
    if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(password)) {
      return { valid: false, message: 'Password must contain uppercase, lowercase, and number' }
    }
    return { valid: true }
  }

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (isSubmitting) return // Prevent double submit
    
    setIsSubmitting(true)
    setIsLoading(true)
    setErrors({})

    // Client-side validation
    const newErrors: Record<string, string> = {}

    if (!signupData.name.trim()) {
      newErrors.name = 'Name is required'
    }

    if (!validateEmail(signupData.email)) {
      newErrors.email = 'Please enter a valid email address'
    }

    const passwordValidation = validatePassword(signupData.password)
    if (!passwordValidation.valid) {
      newErrors.password = passwordValidation.message!
    }

    if (signupData.password !== signupData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match'
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors)
      setIsLoading(false)
      setIsSubmitting(false)
      return
    }

    try {
      const response = await fetch('https://fikirisolutions.onrender.com/api/auth/signup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: signupData.name,
          email: signupData.email,
          password: signupData.password,
          business_name: signupData.businessName,
          industry: signupData.industry,
          team_size: signupData.teamSize
        })
      })

      const data = await response.json()

      if (data.success) {
        setSuccess('Account created successfully! Redirecting to Gmail connection...')
        
        // Store user data
        localStorage.setItem('fikiri-user', JSON.stringify(data.data.user))
        localStorage.setItem('fikiri-user-id', data.data.user.id.toString())
        
        // Redirect to Gmail connection
        setTimeout(() => {
          window.location.href = '/onboarding'
        }, 1500)
      } else {
        if (data.error_code === 'EMAIL_EXISTS') {
          setErrors({ email: 'An account with this email already exists' })
        } else {
          setErrors({ general: data.error || 'Failed to create account' })
        }
      }
    } catch (error) {
      setErrors({ general: 'Network error. Please try again.' })
    } finally {
      setIsLoading(false)
      setIsSubmitting(false)
    }
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (isSubmitting) return // Prevent double submit
    
    setIsSubmitting(true)
    setIsLoading(true)
    setErrors({})

    try {
      const response = await fetch('https://fikirisolutions.onrender.com/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(loginData)
      })

      const data = await response.json()

      if (data.success) {
        setSuccess('Login successful! Redirecting to dashboard...')
        
        // Store user data
        localStorage.setItem('fikiri-user', JSON.stringify(data.data.user))
        localStorage.setItem('fikiri-user-id', data.data.user.id.toString())
        
        // Redirect to dashboard
        setTimeout(() => {
          window.location.href = '/'
        }, 1000)
      } else {
        if (data.error_code === 'INVALID_CREDENTIALS') {
          setErrors({ general: 'Invalid email or password' })
        } else {
          setErrors({ general: data.error || 'Login failed' })
        }
      }
    } catch (error) {
      setErrors({ general: 'Network error. Please try again.' })
    } finally {
      setIsLoading(false)
      setIsSubmitting(false)
    }
  }

  const handleGoogleAuth = () => {
    // Redirect to Google OAuth
    window.location.href = '/api/auth/google'
  }

  return (
    <div className="min-h-screen bg-brand-background flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        {/* Logo and Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center mb-4">
            <FikiriLogo size="lg" variant="full" className="mx-auto" />
          </div>
          <h1 className="text-3xl font-bold text-brand-text">Fikiri Solutions</h1>
          <p className="text-brand-text/70 mt-2">
            AI-powered email automation for your business
          </p>
        </div>

        {/* Auth Form */}
        <div className="bg-brand-background border border-brand-text/10 rounded-2xl shadow-xl p-8">
          {/* Success Message */}
          {success && (
            <div className="mb-6 bg-brand-accent/10 border border-brand-accent/20 rounded-lg p-4">
              <div className="flex items-center">
                <CheckCircle className="h-5 w-5 text-brand-accent mr-3" />
                <p className="text-sm text-brand-text">{success}</p>
              </div>
            </div>
          )}

          {/* General Error */}
          {errors.general && (
            <div className="mb-6 bg-brand-error/10 border border-brand-error/20 rounded-lg p-4">
              <div className="flex items-center">
                <AlertCircle className="h-5 w-5 text-brand-error mr-3" />
                <p className="text-sm text-brand-text">{errors.general}</p>
              </div>
            </div>
          )}

          {/* Tab Toggle */}
          <div className="flex mb-6 bg-brand-text/5 rounded-lg p-1">
            <button
              onClick={() => setIsSignup(false)}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                !isSignup
                  ? 'bg-brand-background text-brand-text shadow-sm'
                  : 'text-brand-text/60 hover:text-brand-text'
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => setIsSignup(true)}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                isSignup
                  ? 'bg-brand-background text-brand-text shadow-sm'
                  : 'text-brand-text/60 hover:text-brand-text'
              }`}
            >
              Create Account
            </button>
          </div>

          {/* Google Auth Button */}
          <button
            onClick={handleGoogleAuth}
            disabled={isLoading}
            className="w-full flex items-center justify-center px-4 py-3 border border-brand-text/20 rounded-lg shadow-sm bg-brand-background text-sm font-medium text-brand-text hover:bg-brand-text/5 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-accent disabled:opacity-50 disabled:cursor-not-allowed mb-4"
          >
            <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continue with Google
          </button>

          <div className="relative mb-4">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-brand-background text-brand-text/60">Or continue with email</span>
            </div>
          </div>

          {/* Signup Form */}
          {isSignup ? (
            <form onSubmit={handleSignup} className="space-y-4">
              {/* Name */}
              <div>
                <label className="block text-sm font-medium text-brand-text mb-1">
                  Full Name
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-brand-text/60" />
                  <input
                    type="text"
                    value={signupData.name}
                    onChange={(e) => setSignupData({ ...signupData, name: e.target.value })}
                    className={`w-full pl-10 pr-3 py-3 border rounded-lg focus:ring-2 focus:ring-brand-accent focus:border-brand-accent bg-white text-brand-text placeholder-brand-text/60 ${
                      errors.name ? 'border-brand-error' : 'border-brand-text/20'
                    }`}
                    placeholder="John Doe"
                    disabled={isLoading}
                  />
                </div>
                {errors.name && (
                  <p className="mt-1 text-sm text-brand-error">{errors.name}</p>
                )}
              </div>

              {/* Email */}
              <div>
                <label className="block text-sm font-medium text-brand-text mb-1">
                  Work Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-brand-text/60" />
                  <input
                    type="email"
                    value={signupData.email}
                    onChange={(e) => setSignupData({ ...signupData, email: e.target.value })}
                    className={`w-full pl-10 pr-3 py-3 border rounded-lg focus:ring-2 focus:ring-brand-accent focus:border-brand-accent bg-white text-brand-text placeholder-brand-text/60 ${
                      errors.email ? 'border-brand-error' : 'border-brand-text/20'
                    }`}
                    placeholder="john@company.com"
                    disabled={isLoading}
                  />
                </div>
                {errors.email && (
                  <p className="mt-1 text-sm text-brand-error">{errors.email}</p>
                )}
              </div>

              {/* Password */}
              <div>
                <label className="block text-sm font-medium text-brand-text mb-1">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-brand-text/60" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={signupData.password}
                    onChange={(e) => setSignupData({ ...signupData, password: e.target.value })}
                    className={`w-full pl-10 pr-10 py-3 border rounded-lg focus:ring-2 focus:ring-brand-accent focus:border-brand-accent bg-white text-brand-text placeholder-brand-text/60 ${
                      errors.password ? 'border-brand-error' : 'border-brand-text/20'
                    }`}
                    placeholder="Create a strong password"
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-brand-text/60 hover:text-brand-text"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {errors.password && (
                  <p className="mt-1 text-sm text-brand-error">{errors.password}</p>
                )}
              </div>

              {/* Confirm Password */}
              <div>
                <label className="block text-sm font-medium text-brand-text mb-1">
                  Confirm Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-brand-text/60" />
                  <input
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={signupData.confirmPassword}
                    onChange={(e) => setSignupData({ ...signupData, confirmPassword: e.target.value })}
                    className={`w-full pl-10 pr-10 py-3 border rounded-lg focus:ring-2 focus:ring-brand-accent focus:border-brand-accent bg-white text-brand-text placeholder-brand-text/60 ${
                      errors.confirmPassword ? 'border-brand-error' : 'border-brand-text/20'
                    }`}
                    placeholder="Confirm your password"
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-brand-text/60 hover:text-brand-text"
                  >
                    {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {errors.confirmPassword && (
                  <p className="mt-1 text-sm text-brand-error">{errors.confirmPassword}</p>
                )}
              </div>

              {/* Business Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-brand-text mb-1">
                    Company
                  </label>
                  <input
                    type="text"
                    value={signupData.businessName}
                    onChange={(e) => setSignupData({ ...signupData, businessName: e.target.value })}
                    className="w-full px-3 py-3 border border-brand-text/20 rounded-lg focus:ring-2 focus:ring-brand-accent focus:border-brand-accent bg-white text-brand-text placeholder-brand-text/60"
                    placeholder="Acme Corp"
                    disabled={isLoading}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-brand-text mb-1">
                    Team Size
                  </label>
                  <select
                    value={signupData.teamSize}
                    onChange={(e) => setSignupData({ ...signupData, teamSize: e.target.value })}
                    className="w-full px-3 py-3 border border-brand-text/20 rounded-lg focus:ring-2 focus:ring-brand-accent focus:border-brand-accent bg-white text-brand-text"
                    disabled={isLoading}
                  >
                    <option value="">Select size</option>
                    <option value="1-5">1-5 people</option>
                    <option value="6-20">6-20 people</option>
                    <option value="21-50">21-50 people</option>
                    <option value="50+">50+ people</option>
                  </select>
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading || isSubmitting}
                className="w-full bg-brand-primary text-white py-3 px-4 rounded-lg font-medium hover:bg-brand-secondary focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-accent disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="animate-spin h-4 w-4 mr-2" />
                    Creating Account...
                  </>
                ) : (
                  'Create Account'
                )}
              </button>
            </form>
          ) : (
            /* Login Form */
            <form onSubmit={handleLogin} className="space-y-4">
              {/* Email */}
              <div>
                <label className="block text-sm font-medium text-brand-text mb-1">
                  Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-brand-text/60" />
                  <input
                    type="email"
                    value={loginData.email}
                    onChange={(e) => setLoginData({ ...loginData, email: e.target.value })}
                    className="w-full pl-10 pr-3 py-3 border border-brand-text/20 rounded-lg focus:ring-2 focus:ring-brand-accent focus:border-brand-accent bg-white text-brand-text placeholder-brand-text/60"
                    placeholder="john@company.com"
                    disabled={isLoading}
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label className="block text-sm font-medium text-brand-text mb-1">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-brand-text/60" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={loginData.password}
                    onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                    className="w-full pl-10 pr-10 py-3 border border-brand-text/20 rounded-lg focus:ring-2 focus:ring-brand-accent focus:border-brand-accent bg-white text-brand-text placeholder-brand-text/60"
                    placeholder="Enter your password"
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-brand-text/60 hover:text-brand-text"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading || isSubmitting}
                className="w-full bg-brand-primary text-white py-3 px-4 rounded-lg font-medium hover:bg-brand-secondary focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-accent disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="animate-spin h-4 w-4 mr-2" />
                    Signing In...
                  </>
                ) : (
                  'Sign In'
                )}
              </button>
            </form>
          )}

          {/* Privacy Notice */}
          <div className="mt-6 text-center">
            <p className="text-xs text-brand-text/60">
              We store your password securely hashed. You can{' '}
              <button className="text-brand-primary hover:text-brand-secondary underline">
                remove all data anytime
              </button>{' '}
              in Settings.
            </p>
          </div>

          {/* Support Link */}
          <div className="mt-4 text-center">
            <a
              href="mailto:support@fikirisolutions.com"
              className="text-sm text-brand-primary hover:text-brand-secondary"
            >
              Need help? Contact Support
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
