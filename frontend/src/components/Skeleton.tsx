import React from 'react'

interface SkeletonProps {
  className?: string
}

export const Skeleton: React.FC<SkeletonProps> = ({ className = '' }) => {
  return (
    <div className={`animate-pulse bg-gray-200 rounded ${className}`} />
  )
}

export const MetricCardSkeleton: React.FC = () => {
  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <Skeleton className="h-4 w-20 mb-2" />
          <Skeleton className="h-8 w-16 mb-1" />
          <Skeleton className="h-3 w-12" />
        </div>
        <Skeleton className="h-8 w-8 rounded-full" />
      </div>
    </div>
  )
}

export const ServiceCardSkeleton: React.FC = () => {
  return (
    <div className="card">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <Skeleton className="h-4 w-24 mb-2" />
          <Skeleton className="h-3 w-32 mb-4" />
        </div>
        <Skeleton className="h-5 w-5 rounded-full" />
      </div>
      <div className="mt-4">
        <Skeleton className="h-6 w-16 rounded-full" />
      </div>
    </div>
  )
}

export const ChartSkeleton: React.FC<SkeletonProps> = ({ className = '' }) => {
  return (
    <div className="card">
      <Skeleton className="h-6 w-32 mb-4" />
      <Skeleton className={`h-64 w-full ${className}`} />
    </div>
  )
}

export const ActivitySkeleton: React.FC = () => {
  return (
    <div className="card">
      <Skeleton className="h-6 w-32 mb-4" />
      <div className="space-y-3">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="flex items-center space-x-3">
            <Skeleton className="h-5 w-5 rounded-full" />
            <div className="flex-1">
              <Skeleton className="h-4 w-full mb-1" />
              <Skeleton className="h-3 w-20" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
