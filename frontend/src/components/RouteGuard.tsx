import React, { useEffect } from 'react'
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

  useEffect(() => {
    if (isLoading) return // Wait for auth state to load

    const currentPath = location.pathname
    const shouldRedirect = redirectTo || getRedirectPath()

    console.log('RouteGuard effect:', {
      currentPath,
      shouldRedirect,
      requireAuth,
      requireOnboarding,
      isAuthenticated,
      onboardingCompleted: user?.onboarding_completed,
      isLoading
    })

    // Handle authentication requirements
    if (requireAuth && !isAuthenticated) {
      // User needs to be authenticated but isn't
      if (currentPath !== '/login' && currentPath !== '/signup') {
        console.log('RouteGuard: Redirecting to login (auth required)')
        navigate('/login')
      }
      return
    }

    // Handle onboarding requirements
    if (requireOnboarding && isAuthenticated && !user?.onboarding_completed) {
      // User is authenticated but hasn't completed onboarding
      if (!currentPath.startsWith('/onboarding')) {
        console.log('RouteGuard: Redirecting to onboarding (onboarding required)')
        navigate('/onboarding')
      }
      return
    }

    // Handle authenticated users trying to access auth pages
    if (isAuthenticated && (currentPath === '/login' || currentPath === '/signup')) {
      // Use getRedirectPath to determine where to send authenticated users
      const redirectPath = getRedirectPath()
      if (redirectPath !== currentPath) {
        console.log('RouteGuard: Redirecting authenticated user from auth page to:', redirectPath)
        navigate(redirectPath)
      }
      return
    }

    // Handle users who haven't completed onboarding trying to access protected routes
    if (isAuthenticated && !user?.onboarding_completed && !currentPath.startsWith('/onboarding') && currentPath !== '/home') {
      console.log('RouteGuard: Redirecting to onboarding (incomplete onboarding)')
      navigate('/onboarding')
      return
    }

    // Handle users who have completed onboarding trying to access onboarding pages
    if (isAuthenticated && user?.onboarding_completed && currentPath.startsWith('/onboarding')) {
      console.log('RouteGuard: Redirecting to home (onboarding completed)')
      navigate('/home')
      return
    }

    // Custom redirect logic - only apply if we're not on auth pages
    if (shouldRedirect && shouldRedirect !== currentPath && 
        !currentPath.startsWith('/login') && 
        !currentPath.startsWith('/signup') && 
        !currentPath.startsWith('/onboarding-flow')) {
      console.log('RouteGuard: Custom redirect to:', shouldRedirect)
      navigate(shouldRedirect)
      return
    }
  }, [isAuthenticated, user, isLoading, location.pathname, navigate, requireAuth, requireOnboarding, redirectTo, getRedirectPath])

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
