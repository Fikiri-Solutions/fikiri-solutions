import React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 0, // No stale time - always fetch fresh data
      gcTime: 0, // No garbage collection time - clear immediately
      retry: 1, // Reduced retries for faster failure
      refetchOnWindowFocus: true, // Re-enable refetch on focus
      refetchOnReconnect: true, // Re-enable refetch on reconnect
      refetchOnMount: true, // Re-enable refetch on mount
      // Keep previous data while fetching new data
      placeholderData: (previousData) => previousData,
    },
    mutations: {
      retry: 1,
    },
  },
})

interface QueryProviderProps {
  children: React.ReactNode
}

export const QueryProvider: React.FC<QueryProviderProps> = ({ children }) => {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}
