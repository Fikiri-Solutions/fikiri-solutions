import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'

export interface User {
  id: number
  email: string
  name: string
  role?: string
  business_name?: string
  business_email?: string
  industry?: string
  team_size?: string
  is_active: boolean
  email_verified: boolean
  created_at: string
  onboarding_completed: boolean
  onboarding_step: number
  metadata?: Record<string, any>
}

export interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  onboardingData: OnboardingData | null
}

export interface OnboardingData {
  businessName: string
  businessEmail: string
  industry: string
  teamSize: string
  services: string[]
  privacyConsent: boolean
  termsAccepted: boolean
  marketingConsent: boolean
}

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>
  signup: (email: string, password: string, name: string) => Promise<{ success: boolean; error?: string }>
  logout: () => void
  updateUser: (user: User) => void
  setOnboardingData: (data: OnboardingData) => void
  clearOnboardingData: () => void
  checkAuthStatus: () => Promise<void>
  getRedirectPath: () => string
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

interface AuthProviderProps {
  children: ReactNode
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
    onboardingData: null
  })
  
  const navigate = useNavigate()

  // Load auth state from localStorage on mount
  useEffect(() => {
    checkAuthStatus()
  }, [])

  const checkAuthStatus = async () => {
    try {
      // Check if we're in the browser environment
      if (typeof window === 'undefined') {
        setAuthState(prev => ({
          ...prev,
          isLoading: false
        }))
        return
      }

      const userData = localStorage.getItem('fikiri-user')
      const userId = localStorage.getItem('fikiri-user-id')
      const onboardingData = localStorage.getItem('fikiri-onboarding-data')

      if (userData && userId) {
        try {
          const user = JSON.parse(userData)
          setAuthState(prev => ({
            ...prev,
            user,
            isAuthenticated: true,
            isLoading: false
          }))
        } catch (error) {
          console.error('Error parsing user data:', error)
          clearAuthData()
        }
      } else {
        setAuthState(prev => ({
          ...prev,
          isLoading: false
        }))
      }

      // Load onboarding data if exists
      if (onboardingData) {
        try {
          const data = JSON.parse(onboardingData)
          setAuthState(prev => ({
            ...prev,
            onboardingData: data
          }))
        } catch (error) {
          console.error('Error parsing onboarding data:', error)
        }
      }
    } catch (error) {
      console.error('Error checking auth status:', error)
      setAuthState(prev => ({
        ...prev,
        isLoading: false
      }))
    }
  }

  const login = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const response = await fetch('https://fikirisolutions.onrender.com/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password })
      })

      const data = await response.json()

      if (data.success) {
        const user = data.data.user
        
        // Store user data (only in browser)
        if (typeof window !== 'undefined') {
          localStorage.setItem('fikiri-user', JSON.stringify(user))
          localStorage.setItem('fikiri-user-id', user.id.toString())
        }
        
        setAuthState(prev => ({
          ...prev,
          user,
          isAuthenticated: true
        }))

        return { success: true }
      } else {
        return { 
          success: false, 
          error: data.error || 'Login failed' 
        }
      }
    } catch (error) {
      return { 
        success: false, 
        error: 'Network error. Please try again.' 
      }
    }
  }

  const signup = async (email: string, password: string, name: string): Promise<{ success: boolean; error?: string }> => {
    try {
      // Get onboarding data if available
      const onboardingData = authState.onboardingData
      
      const signupData = {
        email,
        password,
        name,
        business_name: onboardingData?.businessName || '',
        business_email: onboardingData?.businessEmail || email,
        industry: onboardingData?.industry || '',
        team_size: onboardingData?.teamSize || '',
        privacy_consent: onboardingData?.privacyConsent || false,
        terms_accepted: onboardingData?.termsAccepted || false,
        marketing_consent: onboardingData?.marketingConsent || false
      }

      const response = await fetch('https://fikirisolutions.onrender.com/api/auth/signup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(signupData)
      })

      const data = await response.json()

      if (data.success) {
        const user = data.data.user
        
        // Store user data (only in browser)
        if (typeof window !== 'undefined') {
          localStorage.setItem('fikiri-user', JSON.stringify(user))
          localStorage.setItem('fikiri-user-id', user.id.toString())
        }
        
        // Clear onboarding data as it's now in the user account
        clearOnboardingData()
        
        setAuthState(prev => ({
          ...prev,
          user,
          isAuthenticated: true,
          onboardingData: null
        }))

        return { success: true }
      } else {
        return { 
          success: false, 
          error: data.error || 'Signup failed' 
        }
      }
    } catch (error) {
      return { 
        success: false, 
        error: 'Network error. Please try again.' 
      }
    }
  }

  const logout = () => {
    clearAuthData()
    navigate('/')
  }

  const updateUser = (user: User) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('fikiri-user', JSON.stringify(user))
    }
    setAuthState(prev => ({
      ...prev,
      user
    }))
  }

  const setOnboardingData = (data: OnboardingData) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('fikiri-onboarding-data', JSON.stringify(data))
    }
    setAuthState(prev => ({
      ...prev,
      onboardingData: data
    }))
  }

  const clearOnboardingData = () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('fikiri-onboarding-data')
    }
    setAuthState(prev => ({
      ...prev,
      onboardingData: null
    }))
  }

  const clearAuthData = () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('fikiri-user')
      localStorage.removeItem('fikiri-user-id')
      localStorage.removeItem('fikiri-onboarding-data')
      localStorage.removeItem('fikiri-onboarding-completed')
    }
    setAuthState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      onboardingData: null
    })
  }

  const getRedirectPath = (): string => {
    if (!authState.isAuthenticated) {
      // Not authenticated - check if we have onboarding data
      if (authState.onboardingData) {
        return '/signup' // User has started onboarding, needs to create account
      }
      return '/login' // No onboarding data, start with login
    }

    // Authenticated - check onboarding status
    if (!authState.user?.onboarding_completed) {
      return '/onboarding' // User needs to complete onboarding
    }

    return '/home' // Fully onboarded user
  }

  const value: AuthContextType = {
    ...authState,
    login,
    signup,
    logout,
    updateUser,
    setOnboardingData,
    clearOnboardingData,
    checkAuthStatus,
    getRedirectPath
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}
