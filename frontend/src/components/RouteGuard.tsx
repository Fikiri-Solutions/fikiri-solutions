import React, { useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

interface RouteGuardProps {
  children: React.ReactNode
  requireAuth?: boolean
  requireOnboarding?: boolean
  redirectTo?: string
}

export const RouteGuard: React.FC<RouteGuardProps> = ({ 
  children, 
  requireAuth = false, 
  requireOnboarding = false,
  redirectTo 
}) => {
  const { isAuthenticated, user, isLoading, getRedirectPath } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const hasRedirected = useRef(false) // Prevent redirect loops
  const lastPathname = useRef(location.pathname) // Track pathname changes

  useEffect(() => {
    // Reset redirect flag when pathname actually changes (user navigated)
    if (lastPathname.current !== location.pathname) {
      hasRedirected.current = false
      lastPathname.current = location.pathname
    }
    
    const currentPath = location.pathname
    
    // If loading, wait for auth state to initialize
    if (isLoading) {
      return // Wait for auth state to load
    }
    
    // Special case: If we're on a protected route and not authenticated, but localStorage has auth data,
    // give AuthContext a moment to initialize (race condition after page reload or login redirect)
    if (requireAuth && !isAuthenticated && typeof window !== 'undefined') {
      const hasLocalStorageAuth = localStorage.getItem('fikiri-user') && localStorage.getItem('fikiri-user-id')
      if (hasLocalStorageAuth && currentPath !== '/login' && currentPath !== '/signup') {
        // Auth data exists in localStorage but context hasn't initialized yet
        // Don't redirect immediately - let AuthContext catch up (it will re-render when state updates)
        if (process.env.NODE_ENV === 'development') {
          console.log('[RouteGuard] Auth data in localStorage but context not initialized yet, waiting for AuthContext...')
        }
        return // Return early to allow AuthContext to initialize and re-render
      }
    }
    
    // Debug logging for login/dashboard routes
    if (process.env.NODE_ENV === 'development' && (currentPath === '/login' || currentPath === '/dashboard')) {
      const urlParams = new URLSearchParams(location.search)
      const redirectParam = urlParams.get('redirect')
      console.log('[RouteGuard]', { 
        currentPath, 
        isAuthenticated, 
        isLoading, 
        hasRedirected: hasRedirected.current,
        userEmail: user?.email,
        onboarding_completed: user?.onboarding_completed,
        requireAuth,
        requireOnboarding,
        redirectParam,
        hasLocalStorage: typeof window !== 'undefined' ? {
          user: !!localStorage.getItem('fikiri-user'),
          userId: !!localStorage.getItem('fikiri-user-id')
        } : null
      })
    }

    // Handle authentication requirements
    // Don't redirect /inbox to login - it handles its own auth state
    if (requireAuth && !isAuthenticated && !hasRedirected.current && currentPath !== '/inbox') {
      // User needs to be authenticated but isn't
      // Only redirect if not already on an auth page or /inbox
      if (currentPath !== '/login' && currentPath !== '/signup') {
        hasRedirected.current = true
        // Preserve current path as redirect param so user returns here after login
        // Only add redirect param if we're not already coming from a redirect
        const urlParams = new URLSearchParams(location.search)
        const existingRedirect = urlParams.get('redirect')
        const redirectParam = existingRedirect || encodeURIComponent(currentPath)
        navigate(`/login?redirect=${redirectParam}`, { replace: true })
      }
      return
    }

    // Handle onboarding requirements (only for authenticated users)
    if (requireOnboarding && isAuthenticated && !user?.onboarding_completed && !hasRedirected.current) {
      // User is authenticated but hasn't completed onboarding
      if (!currentPath.startsWith('/onboarding')) {
        // Preserve redirect parameter if present
        const urlParams = new URLSearchParams(location.search)
        const redirectParam = urlParams.get('redirect')
        const safeRedirect = redirectParam && redirectParam.startsWith('/') && !redirectParam.startsWith('//')
          ? redirectParam
          : currentPath // Use current path as redirect if no explicit redirect param
        hasRedirected.current = true
        navigate(`/onboarding?redirect=${encodeURIComponent(safeRedirect)}`, { replace: true })
      }
      return
    }

    // Handle authenticated users trying to access auth pages
    // Only redirect if they're actually authenticated (not just loading)
    // BUT: Allow access to login/signup if localStorage was cleared (user wants to log in as different account)
    if (isAuthenticated && !isLoading && user && !hasRedirected.current && (currentPath === '/login' || currentPath === '/signup')) {
      // Check if localStorage has auth data - if not, user cleared it intentionally, allow access
      const hasLocalStorageAuth = typeof window !== 'undefined' && (
        localStorage.getItem('fikiri-user') || 
        localStorage.getItem('fikiri-user-id') ||
        localStorage.getItem('fikiri-auth')
      )
      
      // If localStorage was cleared, allow access to login/signup (user wants to switch accounts)
      if (!hasLocalStorageAuth) {
        return // Allow access to login/signup
      }
      
      const urlParams = new URLSearchParams(location.search)
      const redirectParam = urlParams.get('redirect')
      
      // If there's a redirect param, honor it (user was trying to access a protected route)
      if (redirectParam && currentPath === '/login') {
        const safeRedirect = redirectParam.startsWith('/') && !redirectParam.startsWith('//') && 
                            redirectParam !== '/login' && redirectParam !== '/signup'
          ? redirectParam
          : null
        
        if (safeRedirect) {
          // User has completed onboarding - redirect to their intended destination
          if (user?.onboarding_completed) {
            hasRedirected.current = true
            navigate(safeRedirect, { replace: true })
            return
          } else {
            // User hasn't completed onboarding - redirect to onboarding with preserved redirect
            hasRedirected.current = true
            navigate(`/onboarding?redirect=${encodeURIComponent(safeRedirect)}`, { replace: true })
            return
          }
        }
        // Fall through to standard redirect if redirect param is invalid
      }
      
      // No redirect param or invalid redirect - standard redirect logic
      // If user hasn't completed onboarding, redirect to onboarding
      if (!user?.onboarding_completed) {
        hasRedirected.current = true
        navigate('/onboarding', { replace: true })
        return
      }
      
      // User has completed onboarding - redirect to dashboard
      hasRedirected.current = true
      navigate('/dashboard', { replace: true })
      return
    }

    // Handle users who haven't completed onboarding trying to access protected routes
    // Only apply this if the route actually requires onboarding
    if (requireOnboarding && isAuthenticated && !user?.onboarding_completed && 
        !currentPath.startsWith('/onboarding') && 
        currentPath !== '/home' &&
        currentPath !== '/login' &&
        currentPath !== '/signup') {
      navigate('/onboarding', { replace: true })
      return
    }

    // Handle users who have completed onboarding trying to access onboarding pages
    if (isAuthenticated && user?.onboarding_completed && currentPath.startsWith('/onboarding')) {
      navigate('/dashboard', { replace: true })
      return
    }

    // For AuthRoute (requireAuth=false), don't redirect unauthenticated users
    // They should be able to stay on login/signup pages
    if (!requireAuth && !isAuthenticated) {
      // Allow unauthenticated users to stay on auth pages
      return
    }

    // Custom redirect logic - only apply if redirectTo is explicitly set
    if (redirectTo && redirectTo !== currentPath && 
        !currentPath.startsWith('/login') && 
        !currentPath.startsWith('/signup') && 
        !currentPath.startsWith('/onboarding')) {
      navigate(redirectTo, { replace: true })
      return
    }
  }, [isAuthenticated, user?.onboarding_completed, isLoading, location.pathname, navigate, requireAuth, requireOnboarding, redirectTo])

  // Show loading state while determining redirect
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-orange-500"></div>
      </div>
    )
  }

  return <>{children}</>
}

// Convenience components for common route protection patterns
export const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <RouteGuard requireAuth={true} requireOnboarding={true}>
    {children}
  </RouteGuard>
)

export const AuthRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <RouteGuard requireAuth={false}>
    {children}
  </RouteGuard>
)

export const OnboardingRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <RouteGuard requireAuth={true} requireOnboarding={false}>
    {children}
  </RouteGuard>
)
