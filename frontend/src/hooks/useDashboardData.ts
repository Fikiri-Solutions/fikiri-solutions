import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../services/apiClient';

// Dashboard metrics with real-time data
export function useDashboardMetrics() {
  return useQuery({
    queryKey: ['dashboard', 'metrics'],
    queryFn: () => apiClient.getDashboardMetrics(),
    staleTime: 30000, // 30 seconds
    refetchInterval: 60000, // Refetch every minute
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
}

// Dashboard timeseries with advanced caching
export function useDashboardTimeseries(period: 'week' | 'month' | 'quarter' = 'week') {
  return useQuery({
    queryKey: ['dashboard', 'timeseries', period],
    queryFn: () => apiClient.getDashboardTimeseries(1, period),
    staleTime: 60000, // 1 minute
    refetchInterval: 300000, // Refetch every 5 minutes
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
}

// Real-time activity feed
export function useActivityFeed(limit: number = 10) {
  return useQuery({
    queryKey: ['dashboard', 'activity', limit],
    queryFn: () => apiClient.getActivity(limit),
    staleTime: 15000, // 15 seconds
    refetchInterval: 30000, // Refetch every 30 seconds
    retry: 2,
  });
}

// Lead analytics with filtering
export function useLeadAnalytics(filters?: {
  dateRange?: { start: string; end: string };
  status?: string;
  source?: string;
}) {
  return useQuery({
    queryKey: ['dashboard', 'leads', filters],
    queryFn: () => apiClient.getLeads(filters),
    staleTime: 60000,
    retry: 3,
  });
}

// Email performance metrics
export function useEmailMetrics(period: 'day' | 'week' | 'month' = 'week') {
  return useQuery({
    queryKey: ['dashboard', 'emails', period],
    queryFn: () => apiClient.getEmailMetrics(period),
    staleTime: 30000,
    refetchInterval: 120000, // 2 minutes
    retry: 3,
  });
}

// AI performance metrics
export function useAIMetrics() {
  return useQuery({
    queryKey: ['dashboard', 'ai'],
    queryFn: () => apiClient.getAIMetrics(),
    staleTime: 60000,
    refetchInterval: 300000, // 5 minutes
    retry: 3,
  });
}

// Revenue analytics
export function useRevenueAnalytics(period: 'week' | 'month' | 'quarter' = 'month') {
  return useQuery({
    queryKey: ['dashboard', 'revenue', period],
    queryFn: () => apiClient.getRevenueAnalytics(period),
    staleTime: 300000, // 5 minutes
    refetchInterval: 900000, // 15 minutes
    retry: 3,
  });
}

// Mutation for updating dashboard preferences
export function useUpdateDashboardPreferences() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (preferences: {
      defaultView?: string;
      refreshInterval?: number;
      notifications?: boolean;
    }) => apiClient.updateDashboardPreferences(preferences),
    onSuccess: () => {
      // Invalidate dashboard queries to refetch with new preferences
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

// Prefetch dashboard data for better UX
export function usePrefetchDashboardData() {
  const queryClient = useQueryClient();
  
  const prefetchAll = () => {
    queryClient.prefetchQuery({
      queryKey: ['dashboard', 'metrics'],
      queryFn: () => apiClient.getDashboardMetrics(),
      staleTime: 30000,
    });
    
    queryClient.prefetchQuery({
      queryKey: ['dashboard', 'timeseries', 'week'],
      queryFn: () => apiClient.getDashboardTimeseries(1, 'week'),
      staleTime: 60000,
    });
    
    queryClient.prefetchQuery({
      queryKey: ['dashboard', 'activity', 10],
      queryFn: () => apiClient.getActivity(10),
      staleTime: 15000,
    });
  };
  
  return { prefetchAll };
}

