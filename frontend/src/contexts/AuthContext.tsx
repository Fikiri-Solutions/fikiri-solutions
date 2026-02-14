import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '../services/apiClient'

export interface User {
  id: number
  email: string
  name: string
  role?: string
  business_name?: string
  business_email?: string
  industry?: string
  team_size?: string
  timezone?: string
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
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string; user?: User }>
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
  // Initialize auth state synchronously from localStorage if available
  // This prevents race conditions where RouteGuard checks before useEffect runs
  const getInitialAuthState = (): AuthState => {
    if (typeof window === 'undefined') {
      return {
        user: null,
        isAuthenticated: false,
        isLoading: true,
        onboardingData: null
      }
    }

    try {
      console.log('🔍 getInitialAuthState - Checking localStorage...')
      let userData = localStorage.getItem('fikiri-user')
      let userId = localStorage.getItem('fikiri-user-id')
      
      // Fallback: Check Zustand store if AuthContext keys don't exist
      if (!userData || !userId) {
        console.log('🔍 Checking Zustand store (fikiri-auth) as fallback...')
        const zustandAuth = localStorage.getItem('fikiri-auth')
        if (zustandAuth) {
          try {
            const zustandData = JSON.parse(zustandAuth)
            const zustandUser = zustandData?.state?.user
            if (zustandUser && zustandUser.id && zustandUser.email) {
              console.log('✅ Found user in Zustand store, migrating to AuthContext format')
              // Migrate from Zustand to AuthContext format
              userData = JSON.stringify(zustandUser)
              userId = zustandUser.id.toString()
              // Save in AuthContext format for future use
              localStorage.setItem('fikiri-user', userData)
              if (userId) localStorage.setItem('fikiri-user-id', userId)
            }
          } catch (error) {
            console.error('❌ Error parsing Zustand auth data:', error)
          }
        }
      }
      
      console.log('🔍 getInitialAuthState - localStorage check:', {
        hasUserData: !!userData,
        hasUserId: !!userId,
        userDataLength: userData?.length || 0,
        userDataPreview: userData ? userData.substring(0, 100) : null
      })
      
      if (userData && userId) {
        try {
          const user = JSON.parse(userData)
          if (user && user.id && user.email) {
            console.log('✅ Initial auth state loaded from localStorage:', {
              userId: user.id,
              email: user.email,
              onboarding_completed: user.onboarding_completed
            })
            return {
              user,
              isAuthenticated: true,
              isLoading: false, // Already loaded, no need to wait
              onboardingData: null
            }
          } else {
            console.warn('⚠️ User data missing required fields:', {
              hasId: !!user?.id,
              hasEmail: !!user?.email,
              user: user
            })
          }
        } catch (error) {
          console.error('❌ Error parsing initial user data:', error)
        }
      } else {
        console.log('⚠️ No auth data in localStorage during initial state check')
      }
    } catch (error) {
      console.error('❌ Error reading initial auth state:', error)
    }

    // Default: no auth data found, will check async
    console.log('⚠️ Returning default (unauthenticated) initial state')
    return {
      user: null,
      isAuthenticated: false,
      isLoading: true,
      onboardingData: null
    }
  }

  const [authState, setAuthState] = useState<AuthState>(getInitialAuthState())
  
  const navigate = useNavigate()
  
  // Monitor localStorage for unexpected clears (development only)
  if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
    const originalSetItem = Storage.prototype.setItem
    const originalRemoveItem = Storage.prototype.removeItem
    const originalClear = Storage.prototype.clear
    
    Storage.prototype.setItem = function(key: string, value: string) {
      if (key.startsWith('fikiri-')) {
        console.log(`[localStorage] SET ${key}:`, value.substring(0, 50) + (value.length > 50 ? '...' : ''))
      }
      return originalSetItem.call(this, key, value)
    }
    
    Storage.prototype.removeItem = function(key: string) {
      if (key.startsWith('fikiri-')) {
        console.log(`[localStorage] REMOVE ${key}`, new Error().stack)
      }
      return originalRemoveItem.call(this, key)
    }
    
    Storage.prototype.clear = function() {
      console.log(`[localStorage] CLEAR ALL`, new Error().stack)
      return originalClear.call(this)
    }
  }

  // Define clearAuthData first (used by checkAuthStatus)
  const clearAuthData = () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('fikiri-user')
      localStorage.removeItem('fikiri-user-id')
      localStorage.removeItem('fikiri-onboarding-data')
      localStorage.removeItem('fikiri-onboarding-completed')
      localStorage.removeItem('fikiri-remember-email')
      localStorage.removeItem('fikiri-remember-password')
      localStorage.removeItem('fikiri-remember-me')
    }
    setAuthState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      onboardingData: null
    })
  }

  // Define checkAuthStatus before useEffect uses it
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

      // Read from localStorage synchronously (this is fast)
      let userData = localStorage.getItem('fikiri-user')
      let userId = localStorage.getItem('fikiri-user-id')
      const onboardingData = localStorage.getItem('fikiri-onboarding-data')
      
      // Fallback: Check Zustand store if AuthContext keys don't exist
      if (!userData || !userId) {
        console.log('🔍 checkAuthStatus - Checking Zustand store (fikiri-auth) as fallback...')
        const zustandAuth = localStorage.getItem('fikiri-auth')
        if (zustandAuth) {
          try {
            const zustandData = JSON.parse(zustandAuth)
            const zustandUser = zustandData?.state?.user
            if (zustandUser && zustandUser.id && zustandUser.email) {
              console.log('✅ Found user in Zustand store, migrating to AuthContext format')
              // Migrate from Zustand to AuthContext format
              userData = JSON.stringify(zustandUser)
              userId = zustandUser.id.toString()
              // Save in AuthContext format for future use
              localStorage.setItem('fikiri-user', userData)
              if (userId) localStorage.setItem('fikiri-user-id', userId)
            }
          } catch (error) {
            console.error('❌ Error parsing Zustand auth data:', error)
          }
        }
      }
      
      console.log('🔍 checkAuthStatus - localStorage check:', {
        hasUserData: !!userData,
        hasUserId: !!userId,
        userDataLength: userData?.length || 0
      })

      if (userData && userId) {
        try {
          const user = JSON.parse(userData)
          // Validate user object has required fields
          if (user && user.id && user.email) {
            // Set auth state immediately (synchronous)
            setAuthState(prev => ({
              ...prev,
              user,
              isAuthenticated: true,
              isLoading: false
            }))
            console.log('✅ Auth state restored from localStorage:', user.email)
          } else {
            console.warn('Invalid user data in localStorage, clearing auth')
            clearAuthData()
          }
        } catch (error) {
          console.error('Error parsing user data:', error)
          clearAuthData()
        }
      } else {
        // No user data found
        console.log('No auth data in localStorage')
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

  // Load auth state from localStorage on mount (for onboarding data and validation)
  useEffect(() => {
    // Only run async check if we didn't already load from localStorage
    if (authState.isLoading) {
      checkAuthStatus()
    } else {
      // Still check for onboarding data
      const onboardingData = localStorage.getItem('fikiri-onboarding-data')
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
    }
  }, []) // Only run once on mount

  const login = async (email: string, password: string): Promise<{ success: boolean; error?: string; user?: User }> => {
    console.log('🔐 [AuthContext] login() called', { email, hasPassword: !!password })
    try {
      console.log('🔐 [AuthContext] Calling apiClient.login...')
      const data = await apiClient.login(email, password)
      console.log('🔐 [AuthContext] apiClient.login returned:', data)

      // Handle rate limiting (if backend returns 429, axios throws; handle in catch if needed)
      if ((data as any)?.retry_after != null) {
        const minutes = Math.ceil((data as any).retry_after / 60)
        return {
          success: false,
          error: `Too many login attempts. Please wait ${minutes} minute${minutes !== 1 ? 's' : ''} and try again.`
        }
      }
      
      console.log('🔍 Login response:', JSON.stringify(data, null, 2))
      console.log('🔍 Login response structure:', {
        hasSuccess: 'success' in data,
        success: data.success,
        hasData: 'data' in data,
        dataKeys: data.data ? Object.keys(data.data) : null,
        hasUser: !!data.data?.user,
        hasAccessToken: !!data.data?.access_token,
        fullData: data.data,
        fullResponse: data
      })

      if (data.success) {
        // Backend returns: { success: true, data: { user: {...}, access_token: "..." } }
        // So we need to access data.data.user
        const user = data.data?.user
        const accessToken = data.data?.access_token
        
        console.log('🔍 Extracted user:', user)
        console.log('🔍 Extracted user details:', user ? {
          id: user.id,
          email: user.email,
          hasId: !!user.id,
          hasEmail: !!user.email
        } : 'NO USER')
        if (import.meta.env.DEV) {
          console.log('🔍 Extracted token:', accessToken ? 'present' : 'missing')
        }
        
        // Validate user object
        if (!user || !user.id) {
          console.error('❌ Invalid user data in login response. Full response:', data)
          console.error('❌ Tried to extract from:', {
            'data.data?.user': data.data?.user,
            'data.data': data.data
          })
          return { 
            success: false, 
            error: 'Invalid response from server' 
          }
        }
        
        // Store user data and tokens (only in browser)
        if (typeof window !== 'undefined') {
          try {
            console.log('💾 About to save to localStorage:', {
              userId: user.id,
              email: user.email,
              userObject: user
            })
            
            const userJson = JSON.stringify(user)
            console.log('💾 User JSON stringified, length:', userJson.length)
            
            localStorage.setItem('fikiri-user', userJson)
            localStorage.setItem('fikiri-user-id', user.id.toString())
            if (accessToken) {
              localStorage.setItem('fikiri-token', accessToken)
            }
            
            console.log('✅ Saved to localStorage:', {
              userId: user.id,
              email: user.email,
              hasToken: !!accessToken,
              userJsonLength: userJson.length
            })
            
            // Immediately verify it was saved
            const savedUser = localStorage.getItem('fikiri-user')
            const savedUserId = localStorage.getItem('fikiri-user-id')
            console.log('✅ Verified localStorage immediately after save:', {
              hasUser: !!savedUser,
              hasUserId: !!savedUserId,
              savedUserLength: savedUser?.length || 0,
              savedUserIdValue: savedUserId,
              savedUserPreview: savedUser ? savedUser.substring(0, 100) : null
            })
            
            // Double-check after a tiny delay
            setTimeout(() => {
              const checkUser = localStorage.getItem('fikiri-user')
              const checkUserId = localStorage.getItem('fikiri-user-id')
              console.log('✅ Verified localStorage after 10ms:', {
                hasUser: !!checkUser,
                hasUserId: !!checkUserId,
                stillSaved: checkUser ? 'YES' : 'NO - WAS CLEARED!'
              })
            }, 10)
          } catch (error) {
            console.error('❌ Error saving to localStorage:', error)
            console.error('❌ Error details:', {
              message: error instanceof Error ? error.message : String(error),
              stack: error instanceof Error ? error.stack : null
            })
          }
        } else {
          console.warn('⚠️ window is undefined, cannot save to localStorage')
        }
        
        setAuthState(prev => ({
          ...prev,
          user,
          isAuthenticated: true,
          isLoading: false
        }))
        
        console.log('✅ Auth state updated:', { 
          userId: user.id, 
          email: user.email,
          isAuthenticated: true, 
          isLoading: false 
        })

        return { success: true, user }
      } else {
        console.error('❌ Login failed - data.success is false:', data)
        return { 
          success: false, 
          error: data.error || 'Login failed' 
        }
      }
    } catch (error: any) {
      console.error('❌ [AuthContext] login() exception:', error)
      console.error('❌ [AuthContext] Error details:', {
        message: error?.message,
        response: error?.response?.data,
        status: error?.response?.status,
        stack: error?.stack
      })
      
      if (error?.response?.status === 429) {
        const retryAfter = error.response?.data?.retry_after
        const minutes = retryAfter ? Math.ceil(retryAfter / 60) : 15
        return { success: false, error: `Too many login attempts. Please wait ${minutes} minute${minutes !== 1 ? 's' : ''} and try again.` }
      }
      
      const errorMessage = error?.response?.data?.error || error?.message || 'Network error. Please try again.'
      return { success: false, error: errorMessage }
    }
  }

  const signup = async (email: string, password: string, name: string): Promise<{ success: boolean; error?: string }> => {
    try {
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

      const data = await apiClient.signup(signupData)

      if (data.success) {
        const user = data.data?.user
        const tokens = data.data?.tokens
        
        // Store user data and tokens (only in browser)
        if (typeof window !== 'undefined') {
          localStorage.setItem('fikiri-user', JSON.stringify(user))
          localStorage.setItem('fikiri-user-id', user.id.toString())
          if (tokens && tokens.access_token) {
            localStorage.setItem('fikiri-token', tokens.access_token)
          }
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

  const logout = async () => {
    try {
      await apiClient.logout()
    } catch (error) {
      // Continue with logout even if backend call fails (backend might be down)
      if (import.meta.env.DEV) {
        console.warn('Backend logout failed, continuing with local logout:', error)
      }
    } finally {
      // Always clear local auth data regardless of backend response
      clearAuthData()
      navigate('/')
    }
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

  // clearAuthData is now defined above, near checkAuthStatus

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

    return '/dashboard' // Fully onboarded user (changed from /home to /dashboard)
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
