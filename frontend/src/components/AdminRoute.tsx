import { Navigate } from 'react-router-dom'
import { PageLoader } from './PageLoader'
import { usePlatformAdmin } from '../hooks/usePlatformAdmin'

interface AdminRouteProps {
  children: React.ReactNode
}

export function AdminRoute({ children }: AdminRouteProps) {
  const { context, loading } = usePlatformAdmin()

  if (loading) {
    return <PageLoader />
  }

  if (!context?.is_platform_admin) {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}
