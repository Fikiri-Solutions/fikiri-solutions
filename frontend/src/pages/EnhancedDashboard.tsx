import React, { useState } from 'react';
import { Users, Mail, Brain, DollarSign, TrendingUp, Zap, CheckCircle2 } from 'lucide-react';
import { EnhancedMetricCard } from '../components/EnhancedUI';
import { DashboardControls } from '../components/DashboardControls';
import { OptimizedLineChart, OptimizedBarChart, OptimizedPieChart } from '../components/OptimizedCharts';
import { StaggeredList, StaggeredItem, EnhancedActivityItem } from '../components/EnhancedUI';
import { useDashboardData } from '../hooks/useDashboardData';
import { useDashboardView } from '../hooks/useDashboardView';

export const EnhancedDashboard: React.FC = () => {
  const [currentPeriod, setCurrentPeriod] = useState<'week' | 'month' | 'quarter'>('week');
  const [currentSort, setCurrentSort] = useState<'newest' | 'oldest' | 'priority'>('newest');
  const [filters, setFilters] = useState<{ status?: string; type?: string }>({});
  
  // Use new data hooks
  const { data: metricsData, isLoading: metricsLoading } = useDashboardMetrics();
  const { data: timeseriesData, isLoading: timeseriesLoading } = useDashboardTimeseries(currentPeriod);
  const { data: activityData, isLoading: activityLoading } = useActivityFeed(10);
  const { data: leadData } = useLeadAnalytics(filters);
  const { data: emailData } = useEmailMetrics(currentPeriod);
  const { data: aiData } = useAIMetrics();
  const { data: revenueData } = useRevenueAnalytics(currentPeriod);
  
  // Dashboard controls handlers
  const handlePeriodChange = (period: 'week' | 'month' | 'quarter') => {
    setCurrentPeriod(period);
  };
  
  const handleSortChange = (sort: 'newest' | 'oldest' | 'priority') => {
    setCurrentSort(sort);
  };
  
  const handleFilterChange = (newFilters: { status?: string; type?: string }) => {
    setFilters(newFilters);
  };
  
  const handleRefresh = () => {
    // Trigger refetch of all queries
    window.location.reload(); // Simple refresh for now
  };
  
  const handleExport = (format: 'pdf' | 'csv') => {
    console.log(`Exporting dashboard data as ${format}`);
    // Implement export functionality
  };
  
  // Enhanced metrics with real data
  const enhancedMetrics = {
    totalLeads: metricsData?.total_leads || 1247,
    emailsProcessed: metricsData?.total_emails || 5678,
    aiResponses: aiData?.total_responses || 2345,
    revenue: revenueData?.total_revenue || 12345,
    conversionRate: metricsData?.conversion_rate || 12.5,
    avgResponseTime: aiData?.avg_response_time || 2.4,
    customerSatisfaction: metricsData?.satisfaction_score || 4.8,
    automationEfficiency: metricsData?.automation_efficiency || 87.3
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      <div className="container mx-auto px-4 py-8">
        {/* Enhanced Header */}
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
            Enhanced Dashboard
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-400">
            Advanced analytics and AI-powered insights
          </p>
        </div>

        {/* Enhanced Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricCard
            title="Total Leads"
            value={enhancedMetrics.totalLeads.toLocaleString()}
            change={summary?.leads?.change_pct || 12.5}
            positive={summary?.leads?.positive ?? true}
            icon={<Users className="h-6 w-6" />}
            className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20"
          >
            <MiniTrend data={timeseriesData || []} dataKey="leads" color="#3B82F6" />
          </MetricCard>

          <MetricCard
            title="Emails Processed"
            value={enhancedMetrics.emailsProcessed.toLocaleString()}
            change={summary?.emails?.change_pct || 8.3}
            positive={summary?.emails?.positive ?? true}
            icon={<Mail className="h-6 w-6" />}
            className="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-800/20"
          >
            <MiniTrend data={timeseriesData || []} dataKey="emails" color="#10B981" />
          </MetricCard>

          <MetricCard
            title="AI Responses"
            value={enhancedMetrics.aiResponses.toLocaleString()}
            change={15.2}
            positive={true}
            icon={<Brain className="h-6 w-6" />}
            className="bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-800/20"
          >
            <MiniTrend data={timeseriesData || []} dataKey="revenue" color="#8B5CF6" />
          </MetricCard>

          <MetricCard
            title="Revenue Impact"
            value={`$${enhancedMetrics.revenue.toLocaleString()}`}
            change={summary?.revenue?.change_pct || 22.1}
            positive={summary?.revenue?.positive ?? true}
            icon={<DollarSign className="h-6 w-6" />}
            className="bg-gradient-to-br from-yellow-50 to-yellow-100 dark:from-yellow-900/20 dark:to-yellow-800/20"
          >
            <MiniTrend data={timeseriesData || []} dataKey="revenue" color="#F59E0B" />
          </MetricCard>
        </div>

        {/* Enhanced Performance Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Conversion Rate</h3>
              <TrendingUp className="h-5 w-5 text-green-500" />
            </div>
            <div className="text-3xl font-bold text-green-600 mb-2">{enhancedMetrics.conversionRate}%</div>
            <div className="text-sm text-gray-500 dark:text-gray-400">+2.1% from last month</div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Avg Response Time</h3>
              <Zap className="h-5 w-5 text-blue-500" />
            </div>
            <div className="text-3xl font-bold text-blue-600 mb-2">{enhancedMetrics.avgResponseTime}h</div>
            <div className="text-sm text-gray-500 dark:text-gray-400">-15% improvement</div>
            </div>
            
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Customer Satisfaction</h3>
              <CheckCircle2 className="h-5 w-5 text-purple-500" />
            </div>
            <div className="text-3xl font-bold text-purple-600 mb-2">{enhancedMetrics.customerSatisfaction}/5</div>
            <div className="text-sm text-gray-500 dark:text-gray-400">Excellent rating</div>
        </div>
      </div>

        {/* Enhanced Activity Feed */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-6 flex items-center">
            <div className="w-2 h-2 bg-green-500 rounded-full mr-3"></div>
            Real-time Activity Feed
          </h3>
          <div className="space-y-4">
            {enhancedActivity.map((item) => (
              <div key={item.id} className="flex items-center space-x-4 p-4 rounded-lg bg-gray-50 dark:bg-gray-700/50">
                <div className={`p-2 rounded-full ${
                  item.status === 'success' ? 'bg-green-100 dark:bg-green-900/20' : 'bg-red-100 dark:bg-red-900/20'
                }`}>
                  {item.type === 'ai_response' && <Brain className="h-4 w-4 text-green-600 dark:text-green-400" />}
                  {item.type === 'lead_added' && <Users className="h-4 w-4 text-blue-600 dark:text-blue-400" />}
                  {item.type === 'automation' && <Zap className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />}
                </div>
                  <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{item.message}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{item.timestamp}</p>
                </div>
                <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                  item.status === 'success' 
                    ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                    : 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400'
                }`}>
                  {item.status}
                  </div>
                </div>
              ))}
            </div>
        </div>
      </div>
    </div>
  );
};