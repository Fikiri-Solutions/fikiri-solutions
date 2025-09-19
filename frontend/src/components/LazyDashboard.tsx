import React, { Suspense, lazy } from 'react'
import { ChartSkeleton } from './Skeleton'

// Lazy load the enhanced dashboard
const EnhancedDashboard = lazy(() => import('../pages/EnhancedDashboard').then(module => ({ default: module.EnhancedDashboard })))
const CompactDashboard = lazy(() => import('../pages/CompactDashboard').then(module => ({ default: module.CompactDashboard })))

interface LazyDashboardProps {
  view: 'enhanced' | 'compact'
}

export const LazyDashboard: React.FC<LazyDashboardProps> = ({ view }) => {
  const DashboardComponent = view === 'enhanced' ? EnhancedDashboard : CompactDashboard
  
  return (
    <Suspense fallback={<ChartSkeleton />}>
      <DashboardComponent />
    </Suspense>
  )
}

export default LazyDashboard
