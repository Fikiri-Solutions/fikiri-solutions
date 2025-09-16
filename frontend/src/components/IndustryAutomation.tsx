import React, { useState, useEffect } from 'react';
import { MessageCircle, Building2, Users, TrendingUp, Settings, CheckCircle } from 'lucide-react';

interface IndustryPrompt {
  industry: string;
  tone: string;
  focus_areas: string[];
  tools: string[];
  pricing_tier: string;
}

interface PricingTier {
  name: string;
  price: number;
  responses_limit: number | string;
  features: string[];
}

interface UsageMetrics {
  tier: string;
  responses: number;
  tool_calls: number;
  tokens: number;
  monthly_cost: number;
}

export const IndustryAutomation: React.FC = () => {
  const [selectedIndustry, setSelectedIndustry] = useState<string>('landscaping');
  const [clientId, setClientId] = useState<string>('demo-client');
  const [message, setMessage] = useState<string>('');
  const [response, setResponse] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [prompts, setPrompts] = useState<Record<string, IndustryPrompt>>({});
  const [pricingTiers, setPricingTiers] = useState<Record<string, PricingTier>>({});
  const [usageMetrics, setUsageMetrics] = useState<UsageMetrics | null>(null);
  const [toolsUsed, setToolsUsed] = useState<any[]>([]);

  useEffect(() => {
    fetchIndustryPrompts();
    fetchPricingTiers();
    fetchClientAnalytics();
  }, [clientId]);

  const fetchIndustryPrompts = async () => {
    try {
      const response = await fetch('/api/industry/prompts');
      const data = await response.json();
      if (data.success) {
        setPrompts(data.prompts);
      }
    } catch (error) {
      console.error('Failed to fetch industry prompts:', error);
    }
  };

  const fetchPricingTiers = async () => {
    try {
      const response = await fetch('/api/industry/pricing-tiers');
      const data = await response.json();
      if (data.success) {
        setPricingTiers(data.tiers);
      }
    } catch (error) {
      console.error('Failed to fetch pricing tiers:', error);
    }
  };

  const fetchClientAnalytics = async () => {
    try {
      const response = await fetch(`/api/industry/analytics/${clientId}`);
      const data = await response.json();
      if (data.success && data.analytics.usage_metrics) {
        setUsageMetrics(data.analytics.usage_metrics);
      }
    } catch (error) {
      console.error('Failed to fetch client analytics:', error);
    }
  };

  const handleIndustryChat = async () => {
    if (!message.trim()) return;

    setIsLoading(true);
    try {
      const response = await fetch('/api/industry/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          industry: selectedIndustry,
          client_id: clientId,
          message: message,
        }),
      });

      const data = await response.json();
      if (data.success) {
        setResponse(data.response);
        setToolsUsed(data.tools_used || []);
        setUsageMetrics(data.usage_metrics);
        setMessage('');
      } else {
        setResponse(`Error: ${data.error}`);
      }
    } catch (error) {
      setResponse(`Network error: ${error}`);
    } finally {
      setIsLoading(false);
    }
  };

  const getIndustryIcon = (industry: string) => {
    switch (industry) {
      case 'landscaping':
        return '🌱';
      case 'restaurant':
        return '🍽️';
      case 'contractor':
        return '🔨';
      default:
        return '🏢';
    }
  };

  const getTierColor = (tier: string) => {
    switch (tier) {
      case 'starter':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
      case 'professional':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300';
      case 'premium':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300';
      case 'enterprise':
        return 'bg-gold-100 text-gold-800 dark:bg-gold-900 dark:text-gold-300';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            🚀 Industry-Specific AI Automation
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Powered by OpenAI Responses API with structured workflows and usage analytics
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Industry Selection & Chat */}
          <div className="lg:col-span-2 space-y-6">
            {/* Industry Selection */}
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
                Select Industry & Test AI
              </h2>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                {Object.entries(prompts).map(([industry, config]) => (
                  <button
                    key={industry}
                    onClick={() => setSelectedIndustry(industry)}
                    className={`p-4 rounded-lg border-2 transition-all ${
                      selectedIndustry === industry
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900'
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                    }`}
                  >
                    <div className="text-2xl mb-2">{getIndustryIcon(industry)}</div>
                    <div className="font-medium text-gray-900 dark:text-white capitalize">
                      {industry}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      {config.tone}
                    </div>
                    <div className={`inline-block px-2 py-1 rounded-full text-xs font-medium mt-2 ${getTierColor(config.pricing_tier)}`}>
                      {config.pricing_tier}
                    </div>
                  </button>
                ))}
              </div>

              {/* Chat Interface */}
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Client ID
                  </label>
                  <input
                    type="text"
                    value={clientId}
                    onChange={(e) => setClientId(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    placeholder="Enter client ID for analytics"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Test Message
                  </label>
                  <textarea
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    rows={3}
                    placeholder={`Test ${selectedIndustry} AI assistant...`}
                  />
                </div>

                <button
                  onClick={handleIndustryChat}
                  disabled={isLoading || !message.trim()}
                  className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium py-2 px-4 rounded-md transition-colors"
                >
                  {isLoading ? 'Processing...' : 'Send Message'}
                </button>
              </div>
            </div>

            {/* Response */}
            {response && (
              <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                  AI Response
                </h3>
                <div className="prose dark:prose-invert max-w-none">
                  <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                    {response}
                  </p>
                </div>
                
                {toolsUsed.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                      Tools Used:
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {toolsUsed.map((tool, index) => (
                        <span
                          key={index}
                          className="px-2 py-1 bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300 rounded-full text-xs"
                        >
                          {tool.tool}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right Column - Analytics & Pricing */}
          <div className="space-y-6">
            {/* Usage Metrics */}
            {usageMetrics && (
              <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  <TrendingUp className="inline-block w-5 h-5 mr-2" />
                  Usage Analytics
                </h3>
                
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Current Tier:</span>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getTierColor(usageMetrics.tier)}`}>
                      {usageMetrics.tier}
                    </span>
                  </div>
                  
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Responses:</span>
                    <span className="text-gray-900 dark:text-white font-medium">
                      {usageMetrics.responses}
                    </span>
                  </div>
                  
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Tool Calls:</span>
                    <span className="text-gray-900 dark:text-white font-medium">
                      {usageMetrics.tool_calls}
                    </span>
                  </div>
                  
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Tokens:</span>
                    <span className="text-gray-900 dark:text-white font-medium">
                      {usageMetrics.tokens.toLocaleString()}
                    </span>
                  </div>
                  
                  <div className="flex justify-between border-t pt-3">
                    <span className="text-gray-600 dark:text-gray-400">Monthly Cost:</span>
                    <span className="text-gray-900 dark:text-white font-bold">
                      ${usageMetrics.monthly_cost}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Pricing Tiers */}
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                <Building2 className="inline-block w-5 h-5 mr-2" />
                Pricing Tiers
              </h3>
              
              <div className="space-y-4">
                {Object.entries(pricingTiers).map(([tier, config]) => (
                  <div
                    key={tier}
                    className={`p-4 rounded-lg border ${
                      usageMetrics?.tier === tier
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900'
                        : 'border-gray-200 dark:border-gray-700'
                    }`}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <h4 className="font-medium text-gray-900 dark:text-white">
                        {config.name}
                      </h4>
                      <span className="text-lg font-bold text-gray-900 dark:text-white">
                        ${config.price}
                      </span>
                    </div>
                    
                    <div className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                      {typeof config.responses_limit === 'number' 
                        ? `${config.responses_limit} responses/month`
                        : 'Unlimited responses'
                      }
                    </div>
                    
                    <ul className="space-y-1">
                      {config.features.map((feature, index) => (
                        <li key={index} className="text-sm text-gray-600 dark:text-gray-400 flex items-center">
                          <CheckCircle className="w-3 h-3 mr-2 text-green-500" />
                          {feature}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </div>

            {/* Industry Focus Areas */}
            {prompts[selectedIndustry] && (
              <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  <Settings className="inline-block w-5 h-5 mr-2" />
                  {selectedIndustry.charAt(0).toUpperCase() + selectedIndustry.slice(1)} Focus
                </h3>
                
                <div className="space-y-3">
                  <div>
                    <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                      Focus Areas:
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {prompts[selectedIndustry].focus_areas.map((area, index) => (
                        <span
                          key={index}
                          className="px-2 py-1 bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300 rounded-full text-xs"
                        >
                          {area}
                        </span>
                      ))}
                    </div>
                  </div>
                  
                  <div>
                    <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                      Available Tools:
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {prompts[selectedIndustry].tools.map((tool, index) => (
                        <span
                          key={index}
                          className="px-2 py-1 bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300 rounded-full text-xs"
                        >
                          {tool}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
