import React from 'react';
import { Users, Mail, Brain, DollarSign, TrendingUp, Zap, CheckCircle2 } from 'lucide-react';

export const CompactDashboard: React.FC = () => {

  // Compact metrics
  const compactMetrics = {
    totalLeads: 1247,
    emailsProcessed: 5678,
    aiResponses: 2345,
    revenue: 12345
  };

  const compactActivity = [
    { id: 1, type: 'ai_response', message: 'AI processed customer inquiry', status: 'success', timestamp: '2m ago' },
    { id: 2, type: 'lead_added', message: 'New lead: TechCorp Solutions', status: 'success', timestamp: '5m ago' },
    { id: 3, type: 'automation', message: 'Email sequence triggered', status: 'success', timestamp: '8m ago' },
    { id: 4, type: 'ai_response', message: 'AI generated follow-up', status: 'success', timestamp: '12m ago' }
  ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="container mx-auto px-4 py-6">
        {/* Compact Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
            Compact Dashboard
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Essential metrics at a glance
          </p>
        </div>

        {/* Compact Metrics Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wide">Leads</p>
                <p className="text-xl font-bold text-gray-900 dark:text-white">{compactMetrics.totalLeads.toLocaleString()}</p>
              </div>
              <Users className="h-5 w-5 text-blue-500" />
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wide">Emails</p>
                <p className="text-xl font-bold text-gray-900 dark:text-white">{compactMetrics.emailsProcessed.toLocaleString()}</p>
              </div>
              <Mail className="h-5 w-5 text-green-500" />
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wide">AI Responses</p>
                <p className="text-xl font-bold text-gray-900 dark:text-white">{compactMetrics.aiResponses.toLocaleString()}</p>
              </div>
              <Brain className="h-5 w-5 text-purple-500" />
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wide">Revenue</p>
                <p className="text-xl font-bold text-gray-900 dark:text-white">${compactMetrics.revenue.toLocaleString()}</p>
              </div>
              <DollarSign className="h-5 w-5 text-yellow-500" />
            </div>
          </div>
        </div>

        {/* Compact Activity Feed */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4 border border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
            <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
            Recent Activity
          </h3>
          <div className="space-y-3">
            {compactActivity.map((item) => (
              <div key={item.id} className="flex items-center space-x-3 py-2">
                <div className={`p-1.5 rounded-full ${
                  item.status === 'success' ? 'bg-green-100 dark:bg-green-900/20' : 'bg-red-100 dark:bg-red-900/20'
                }`}>
                  {item.type === 'ai_response' && <Brain className="h-3 w-3 text-green-600 dark:text-green-400" />}
                  {item.type === 'lead_added' && <Users className="h-3 w-3 text-blue-600 dark:text-blue-400" />}
                  {item.type === 'automation' && <Zap className="h-3 w-3 text-yellow-600 dark:text-yellow-400" />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{item.message}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{item.timestamp}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Compact Performance Indicators */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Conversion Rate</span>
              <TrendingUp className="h-4 w-4 text-green-500" />
            </div>
            <div className="text-2xl font-bold text-green-600">12.5%</div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Response Time</span>
              <Zap className="h-4 w-4 text-blue-500" />
            </div>
            <div className="text-2xl font-bold text-blue-600">2.4h</div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Satisfaction</span>
              <CheckCircle2 className="h-4 w-4 text-purple-500" />
            </div>
            <div className="text-2xl font-bold text-purple-600">4.8/5</div>
          </div>
        </div>
      </div>
    </div>
  );
};