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

export const TableSkeleton: React.FC<{ rows?: number; columns?: number }> = ({ rows = 5, columns = 6 }) => {
  return (
    <div className="animate-pulse">
      <div className="space-y-3">
        {[...Array(rows)].map((_, rowIndex) => (
          <div key={rowIndex} className="flex items-center space-x-4 px-6 py-4 border-b border-brand-text/10 dark:border-gray-700">
            {[...Array(columns)].map((_, colIndex) => (
              <div key={colIndex} className="flex-1">
                <Skeleton className="h-4 w-full" />
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

export const LeadTableSkeleton: React.FC = () => {
  return (
    <div className="bg-brand-background dark:bg-gray-800 rounded-lg shadow-md border border-brand-text/10">
      <div className="px-6 py-4 border-b border-brand-text/10">
        <Skeleton className="h-6 w-32" />
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-brand-text/10 dark:divide-gray-700">
          <thead className="bg-brand-background/50 dark:bg-gray-800">
            <tr>
              {['Lead', 'Company', 'Stage', 'Score', 'Last Contact', 'Source'].map((header) => (
                <th key={header} className="px-6 py-3 text-left">
                  <Skeleton className="h-4 w-20" />
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-900 divide-y divide-brand-text/10 dark:divide-gray-700">
            {[...Array(5)].map((_, i) => (
              <tr key={i}>
                <td className="px-6 py-4">
                  <div className="flex items-center space-x-3">
                    <Skeleton className="h-10 w-10 rounded-full" />
                    <div className="flex-1">
                      <Skeleton className="h-4 w-24 mb-2" />
                      <Skeleton className="h-3 w-32" />
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <Skeleton className="h-4 w-20" />
                </td>
                <td className="px-6 py-4">
                  <Skeleton className="h-6 w-16 rounded-full" />
                </td>
                <td className="px-6 py-4">
                  <Skeleton className="h-4 w-12" />
                </td>
                <td className="px-6 py-4">
                  <Skeleton className="h-4 w-24" />
                </td>
                <td className="px-6 py-4">
                  <Skeleton className="h-4 w-16" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export const ServiceCardSkeletonList: React.FC<{ count?: number }> = ({ count = 4 }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {[...Array(count)].map((_, i) => (
        <ServiceCardSkeleton key={i} />
      ))}
    </div>
  )
}
