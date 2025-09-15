import React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 2 * 60 * 1000, // 2 minutes (reduced for faster updates)
      gcTime: 5 * 60 * 1000, // 5 minutes (reduced memory usage)
      retry: 1, // Reduced retries for faster failure
      refetchOnWindowFocus: false,
      refetchOnReconnect: false, // Disabled for faster initial load
      refetchOnMount: false, // Disabled for faster navigation
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
