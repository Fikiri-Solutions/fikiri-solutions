import React, { Suspense, lazy } from 'react'
import { ChartSkeleton } from './Skeleton'

// Lazy load the heavy charts component
const DashboardCharts = lazy(() => import('./DashboardCharts').then(module => ({ default: module.DashboardCharts })))

interface LazyDashboardChartsProps {
  data: any[]
}

export const LazyDashboardCharts: React.FC<LazyDashboardChartsProps> = ({ data }) => {
  return (
    <Suspense fallback={<ChartSkeleton />}>
      <DashboardCharts data={data} />
    </Suspense>
  )
}

export default LazyDashboardCharts
