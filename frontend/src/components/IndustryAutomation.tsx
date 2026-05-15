import React, { useState, useEffect, useRef } from 'react';
import { Building2, TrendingUp, Settings, CheckCircle, Loader2 } from 'lucide-react';
import { useToast } from './Toast';
import { useAuth } from '../contexts/AuthContext';
import { apiClient, type IndustryPromptConfig, type IndustryUsageMetrics } from '../services/apiClient';

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
  const [selectedIndustry, setSelectedIndustry] = useState<string>('real_estate');
  const [clientId, setClientId] = useState<string>('demo-client');
  const [message, setMessage] = useState<string>('');
  const [response, setResponse] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isLoadingPrompts, setIsLoadingPrompts] = useState<boolean>(true);
  const [isLoadingTiers, setIsLoadingTiers] = useState<boolean>(true);
  const [isLoadingAnalytics, setIsLoadingAnalytics] = useState<boolean>(true);
  const [prompts, setPrompts] = useState<Record<string, IndustryPromptConfig>>({});
  const [pricingTiers, setPricingTiers] = useState<Record<string, PricingTier>>({});
  const [usageMetrics, setUsageMetrics] = useState<UsageMetrics | null>(null);
  const [toolsUsed, setToolsUsed] = useState<any[]>([]);
  const { addToast } = useToast();
  const { user } = useAuth();
  const loadGeneration = useRef(0);

  const getUserId = (): number => {
    if (user?.id) {
      return user.id;
    }
    const stored = localStorage.getItem('fikiri-user-id');
    return stored ? Number(stored) : 1;
  };

  const FALLBACK_PROMPTS: Record<string, IndustryPromptConfig> = {
    real_estate: {
      industry: 'real_estate',
      tone: 'professional',
      focus_areas: ['property listings', 'client consultations', 'market analysis', 'showings scheduling'],
      tools: ['calendar', 'crm', 'property_api', 'market_data'],
      pricing_tier: 'business',
    },
    enterprise_solutions: {
      industry: 'enterprise_solutions',
      tone: 'professional',
      focus_areas: ['custom workflows', 'multi-industry support', 'advanced analytics', 'white-label options'],
      tools: ['custom_api', 'white_label', 'dedicated_support', 'advanced_analytics'],
      pricing_tier: 'enterprise',
    },
  };

  const FALLBACK_PRICING: Record<string, PricingTier> = {
    starter: {
      name: 'Starter',
      price: 49,
      responses_limit: 200,
      features: ['Basic AI responses', 'Email automation', 'Simple CRM', '500 emails/month'],
    },
  };

  const FALLBACK_USAGE: UsageMetrics = {
    tier: 'starter',
    responses: 0,
    tool_calls: 0,
    tokens: 0,
    monthly_cost: 29,
  };

  useEffect(() => {
    const gen = ++loadGeneration.current;
    let cancelled = false;

    setIsLoadingPrompts(true);
    setIsLoadingTiers(true);
    setIsLoadingAnalytics(true);

    (async () => {
      const userId = getUserId();
      const settled = await Promise.allSettled([
        apiClient.getIndustryPrompts(),
        apiClient.getIndustryPricingTiers(),
        apiClient.getIndustryUsage(userId),
      ]);

      if (cancelled || gen !== loadGeneration.current) {
        return;
      }

      const [promptsResult, pricingResult, usageResult] = settled;

      if (promptsResult.status === 'fulfilled') {
        setPrompts(promptsResult.value);
      } else {
        addToast({
          type: 'error',
          title: 'Load Failed',
          message: 'Failed to load industry prompts. Using fallback data.',
        });
        setPrompts(FALLBACK_PROMPTS);
      }

      if (pricingResult.status === 'fulfilled') {
        setPricingTiers(pricingResult.value);
      } else {
        addToast({
          type: 'error',
          title: 'Load Failed',
          message: 'Failed to load pricing tiers. Using fallback data.',
        });
        setPricingTiers(FALLBACK_PRICING);
      }

      if (usageResult.status === 'fulfilled') {
        setUsageMetrics(usageResult.value as IndustryUsageMetrics);
      } else {
        addToast({
          type: 'error',
          title: 'Load Failed',
          message: 'Failed to load analytics. Using fallback data.',
        });
        setUsageMetrics(FALLBACK_USAGE);
      }

      setIsLoadingPrompts(false);
      setIsLoadingTiers(false);
      setIsLoadingAnalytics(false);
    })();

    return () => {
      cancelled = true;
    };
  }, [user?.id, addToast]);

  const handleIndustryChat = async () => {
    if (!message.trim()) {
      addToast({ 
        type: 'warning', 
        title: 'Empty Message', 
        message: 'Please enter a message before sending.' 
      });
      return;
    }

    setIsLoading(true);
    try {
      const data = await apiClient.sendChatMessage(message, {
        industry: selectedIndustry,
        client_id: clientId
      });
      const responseText = (data as any)?.response ?? (data as any)?.data?.response;
      const tools = (data as any)?.service_queries ?? (data as any)?.data?.service_queries ?? [];
      if (responseText != null) {
        setResponse(responseText || 'No response received');
        setToolsUsed(tools);
        setMessage('');
        addToast({ 
          type: 'success', 
          title: 'Message Sent', 
          message: 'AI response received successfully.' 
        });
      } else {
        const errorMessage = (data as any)?.error || 'Failed to get response';
        setResponse(`Error: ${errorMessage}`);
        addToast({ 
          type: 'error', 
          title: 'Request Failed', 
          message: errorMessage 
        });
      }
    } catch (error: any) {
      const errorMessage = error?.message || 'Network error occurred';
      setResponse(`Network error: ${errorMessage}`);
      addToast({ 
        type: 'error', 
        title: 'Network Error', 
        message: 'Unable to connect to the server. Please try again.' 
      });
    } finally {
      setIsLoading(false);
    }
  };

  const getIndustryIcon = (industry: string) => {
    const icons: Record<string, string> = {
      // Real Estate
      'real_estate': '🏠',
      'property_management': '🏘️',
      
      // Construction & Services
      'construction': '🔨',
      'cleaning_services': '🧹',
      'auto_services': '🚗',
      
      // Events & Lifestyle
      'event_planning': '🎉',
      'fitness_wellness': '💪',
      'beauty_spa': '💅',
      
      // Professional Services
      'legal_services': '⚖️',
      'accounting_consulting': '📊',
      
      // Food & Beverage
      'restaurant': '🍽️',
      
      // Medical & Healthcare
      'medical_practice': '🏥',
      
      // Enterprise & Technology
      'enterprise_solutions': '🏢'
    };
    return icons[industry] || '🏢';
  };

  const getIndustryCategory = (industry: string) => {
    const categories: Record<string, string> = {
      // Real Estate
      'real_estate': 'Real Estate',
      'property_management': 'Real Estate',
      
      // Construction & Services
      'construction': 'General',
      'cleaning_services': 'General',
      'auto_services': 'General',
      
      // Events & Lifestyle
      'event_planning': 'General',
      'fitness_wellness': 'General',
      'beauty_spa': 'General',
      
      // Professional Services
      'legal_services': 'Professional Services',
      'accounting_consulting': 'Professional Services',
      
      // Food & Beverage
      'restaurant': 'Food & Beverage',
      
      // Medical & Healthcare
      'medical_practice': 'Medical & Healthcare',
      
      // Enterprise & Technology
      'enterprise_solutions': 'Enterprise & Technology'
    };
    return categories[industry] || 'General';
  };

  const getIndustryDescription = (industry: string) => {
    const descriptions: Record<string, string> = {
      'restaurant': 'Reservation management, menu recommendations, special promotions',
      'cafe': 'Loyalty programs, daily specials, event hosting, catering orders',
      'food_truck': 'Location updates, daily menus, event bookings, social media',
      'real_estate': 'Property listings, client consultations, market analysis',
      'property_management': 'Maintenance requests, tenant communication, rent collection',
      'medical_practice': 'Appointment scheduling, patient reminders, HIPAA compliance',
      'dental_clinic': 'Treatment plans, insurance claims, patient education',
      'veterinary': 'Vaccination reminders, emergency protocols, pet records',
      'landscaping': 'Appointment scheduling, service quotes, seasonal planning',
      'painting': 'Color consultations, project estimates, weather scheduling',
      'carpenter': 'Custom designs, project timelines, material sourcing',
      'drywall': 'Repair estimates, texture matching, project scheduling',
      'plumber': 'Emergency calls, repair estimates, preventive maintenance',
      'roofer': 'Weather scheduling, safety protocols, inspection reports',
      'car_rental': 'Reservation management, vehicle availability, fleet maintenance',
      'ride_share': 'Driver support, route optimization, earnings tracking',
      'content_creation': 'Content planning, social media strategy, brand consistency',
      'marketing_agency': 'Campaign management, client reporting, ROI tracking',
      'photography': 'Session booking, portfolio management, client galleries',
      'tax_services': 'Tax preparation, deadline management, IRS compliance',
      'accounting': 'Bookkeeping, financial reporting, audit preparation',
      'legal_services': 'Case management, client intake, document preparation',
      'retail_store': 'Inventory management, customer service, sales tracking',
      'ecommerce': 'Order management, customer support, inventory sync'
    };
    return descriptions[industry] || 'Industry-specific automation and workflows';
  };

  const getTierColor = (tier: string) => {
    switch (tier) {
      case 'starter':
        return 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300';
      case 'growth':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300';
      case 'business':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-300';
      case 'enterprise':
        return 'bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-300';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
    }
  };

  return (
    <div className="min-h-screen bg-brand-background dark:bg-gray-900 p-6 transition-colors duration-300">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-brand-text dark:text-white mb-2">
            🚀 Industry-Specific AI Automation
          </h1>
          <p className="text-brand-text/70 dark:text-gray-400">
            Powered by OpenAI Responses API with structured workflows and usage analytics
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Industry Selection & Chat */}
          <div className="lg:col-span-2 space-y-6">
            {/* Industry Selection */}
            <div className="bg-brand-background dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-brand-text/10">
              <h2 className="text-xl font-semibold text-brand-text dark:text-white mb-4">
                Select Industry & Test AI
              </h2>
              
              {/* Industry Categories */}
              {isLoadingPrompts ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-brand-primary mr-2" />
                  <span className="text-brand-text/70 dark:text-gray-400">Loading industries...</span>
                </div>
              ) : (
              <div className="space-y-6">
                {Object.entries(
                  Object.entries(prompts).reduce((acc, [industry, config]) => {
                    const category = getIndustryCategory(industry);
                    if (!acc[category]) {
                      acc[category] = [];
                    }
                    acc[category].push({ industry, config });
                    return acc;
                  }, {} as Record<string, Array<{industry: string, config: IndustryPromptConfig}>>)
                ).map(([category, industries]: [string, Array<{industry: string, config: IndustryPromptConfig}>]) => (
                  <div key={category} className="space-y-3">
                    <h3 className="text-lg font-medium text-brand-text dark:text-white border-b border-brand-text/10 dark:border-gray-700 pb-2">
                      {category}
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-2">
                      {industries.map(({ industry, config }: {industry: string, config: IndustryPromptConfig}) => (
                        <button
                          key={industry}
                          onClick={() => setSelectedIndustry(industry)}
                          className={`p-3 rounded-lg border-2 transition-all duration-200 text-left hover:scale-105 ${
                            selectedIndustry === industry
                              ? 'border-brand-primary bg-brand-accent/20 dark:bg-brand-accent/20 shadow-lg'
                              : 'border-brand-text/20 dark:border-gray-700 hover:border-brand-accent dark:hover:border-gray-600 hover:shadow-md'
                          }`}
                        >
                          <div className="flex flex-col items-center text-center space-y-2">
                            <div className="text-2xl">{getIndustryIcon(industry)}</div>
                            <div className="font-medium text-brand-text dark:text-white capitalize text-sm">
                              {industry.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
                            </div>
                            <div className={`inline-block px-2 py-1 rounded-full text-xs font-medium ${getTierColor(config.pricing_tier)}`}>
                              {config.pricing_tier}
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
              )}

              {/* Chat Interface */}
              <div className="space-y-4">
                <div>
                  <label htmlFor="industry-client-id" className="block text-sm font-medium text-brand-text dark:text-gray-300 mb-2">
                    Client ID
                  </label>
                  <input
                    id="industry-client-id"
                    type="text"
                    value={clientId}
                    onChange={(e) => setClientId(e.target.value)}
                    className="w-full px-3 py-2 border border-brand-text/20 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-brand-text dark:text-white focus:border-brand-accent dark:focus:border-brand-accent focus:ring-brand-accent dark:focus:ring-brand-accent transition-colors duration-200"
                    placeholder="Enter client ID for analytics"
                  />
                </div>

                <div>
                  <label htmlFor="industry-test-message" className="block text-sm font-medium text-brand-text dark:text-gray-300 mb-2">
                    Test Message
                  </label>
                  <textarea
                    id="industry-test-message"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    className="w-full px-3 py-2 border border-brand-text/20 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-brand-text dark:text-white focus:border-brand-accent dark:focus:border-brand-accent focus:ring-brand-accent dark:focus:ring-brand-accent transition-colors duration-200"
                    rows={3}
                    placeholder={`Test ${selectedIndustry.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')} AI assistant...`}
                  />
                </div>

                <button
                  onClick={handleIndustryChat}
                  disabled={isLoading || !message.trim()}
                  className="w-full bg-brand-primary hover:bg-brand-secondary disabled:bg-gray-400 text-white font-medium py-2 px-4 rounded-md transition-all duration-200 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-brand-accent focus:ring-offset-2 dark:focus:ring-offset-gray-900"
                >
                  {isLoading ? 'Processing...' : 'Send Message'}
                </button>
              </div>
            </div>

            {/* Response */}
            {response && (
              <div className="bg-brand-background dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-brand-text/10">
                <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-3">
                  AI Response
                </h3>
                <div className="prose dark:prose-invert max-w-none">
                  <p className="text-brand-text/80 dark:text-gray-300 whitespace-pre-wrap">
                    {response}
                  </p>
                </div>
                
                {toolsUsed.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-sm font-medium text-brand-text dark:text-white mb-2">
                      Tools Used:
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {toolsUsed.map((tool, index) => (
                        <span
                          key={index}
                          className="px-2 py-1 bg-brand-accent/20 text-brand-primary dark:bg-brand-accent/20 dark:text-brand-accent rounded-full text-xs"
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
            {isLoadingAnalytics ? (
              <div className="bg-brand-background dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-brand-text/10">
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-5 w-5 animate-spin text-brand-primary mr-2" />
                  <span className="text-brand-text/70 dark:text-gray-400">Loading analytics...</span>
                </div>
              </div>
            ) : usageMetrics ? (
              <div className="bg-brand-background dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-brand-text/10">
                <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-4">
                  <TrendingUp className="inline-block w-5 h-5 mr-2" />
                  Usage Analytics
                </h3>
                
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-brand-text/70 dark:text-gray-400">Current Tier:</span>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getTierColor(usageMetrics.tier)}`}>
                      {usageMetrics.tier}
                    </span>
                  </div>
                  
                  <div className="flex justify-between">
                    <span className="text-brand-text/70 dark:text-gray-400">Responses:</span>
                    <span className="text-brand-text dark:text-white font-medium">
                      {usageMetrics.responses}
                    </span>
                  </div>
                  
                  <div className="flex justify-between">
                    <span className="text-brand-text/70 dark:text-gray-400">Tool Calls:</span>
                    <span className="text-brand-text dark:text-white font-medium">
                      {usageMetrics.tool_calls}
                    </span>
                  </div>
                  
                  <div className="flex justify-between">
                    <span className="text-brand-text/70 dark:text-gray-400">Tokens:</span>
                    <span className="text-brand-text dark:text-white font-medium">
                      {usageMetrics.tokens.toLocaleString()}
                    </span>
                  </div>
                  
                  <div className="flex justify-between border-t border-brand-text/10 pt-3">
                    <span className="text-brand-text/70 dark:text-gray-400">Monthly Cost:</span>
                    <span className="text-brand-text dark:text-white font-bold">
                      ${usageMetrics.monthly_cost}
                    </span>
                  </div>
                </div>
              </div>
            ) : null}

            {/* Pricing Tiers */}
            <div className="bg-brand-background dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-brand-text/10">
              <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-4">
                <Building2 className="inline-block w-5 h-5 mr-2" />
                Pricing Tiers
              </h3>
              
              {isLoadingTiers ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-5 w-5 animate-spin text-brand-primary mr-2" />
                  <span className="text-brand-text/70 dark:text-gray-400">Loading tiers...</span>
                </div>
              ) : (
              <div className="space-y-4">
                {Object.entries(pricingTiers).map(([tier, config]) => {
                  // Check if this tier matches the selected industry's pricing tier
                  const isSelectedTier = selectedIndustry && prompts[selectedIndustry]?.pricing_tier === tier;
                  
                  return (
                    <div
                      key={tier}
                      className={`p-4 rounded-lg border transition-all duration-200 cursor-pointer hover:shadow-md ${
                        isSelectedTier
                          ? 'border-brand-primary bg-brand-accent/20 dark:bg-brand-accent/20 shadow-lg'
                          : 'border-brand-text/20 dark:border-gray-700 hover:border-brand-accent dark:hover:border-gray-600'
                      }`}
                      onClick={() => {
                        // Find an industry that uses this tier and select it
                        const industryForTier = Object.keys(prompts).find(
                          industry => prompts[industry]?.pricing_tier === tier
                        );
                        if (industryForTier) {
                          setSelectedIndustry(industryForTier);
                        }
                        
                        // Update usage metrics based on selected tier with consistent data
                        const tierConfig = pricingTiers[tier];
                        if (tierConfig) {
                          // Define tier-specific usage patterns
                          const tierUsagePatterns = {
                            starter: {
                              usagePercentage: 0.75, // 75% usage
                              toolCallRatio: 0.05,   // 5% of responses use tools
                              avgTokensPerResponse: 120
                            },
                            growth: {
                              usagePercentage: 0.65, // 65% usage
                              toolCallRatio: 0.08,   // 8% of responses use tools
                              avgTokensPerResponse: 150
                            },
                            business: {
                              usagePercentage: 0.55, // 55% usage
                              toolCallRatio: 0.12,   // 12% of responses use tools
                              avgTokensPerResponse: 180
                            },
                            enterprise: {
                              usagePercentage: 0.45, // 45% usage (enterprise users are more selective)
                              toolCallRatio: 0.15,   // 15% of responses use tools
                              avgTokensPerResponse: 200
                            }
                          };
                          
                          const pattern = tierUsagePatterns[tier as keyof typeof tierUsagePatterns] || tierUsagePatterns.starter;
                          const responsesLimit = typeof tierConfig.responses_limit === 'number' 
                            ? tierConfig.responses_limit 
                            : 100000; // Default for unlimited (enterprise)
                          
                          // Calculate usage based on tier-specific patterns
                          const responses = Math.floor(responsesLimit * pattern.usagePercentage);
                          const toolCalls = Math.floor(responses * pattern.toolCallRatio);
                          const tokens = responses * pattern.avgTokensPerResponse;
                          
                          const newMetrics = {
                            tier: tier,
                            responses: responses,
                            tool_calls: toolCalls,
                            tokens: tokens,
                            monthly_cost: tierConfig.price
                          };
                          
                          setUsageMetrics(newMetrics);
                        }
                      }}
                    >
                    <div className="flex justify-between items-start mb-2">
                      <h4 className="font-medium text-brand-text dark:text-white">
                        {config.name}
                      </h4>
                      <span className="text-lg font-bold text-brand-text dark:text-white">
                        ${config.price}
                      </span>
                    </div>
                    
                    <div className="text-sm text-brand-text/70 dark:text-gray-400 mb-3">
                      {typeof config.responses_limit === 'number' 
                        ? `${config.responses_limit} responses/month`
                        : 'Unlimited responses'
                      }
                    </div>
                    
                    <ul className="space-y-1">
                      {config.features.map((feature, index) => (
                        <li key={index} className="text-sm text-brand-text/70 dark:text-gray-400 flex items-center">
                          <CheckCircle className="w-3 h-3 mr-2 text-brand-accent" />
                          {feature}
                        </li>
                      ))}
                    </ul>
                  </div>
                  );
                })}
              </div>
              )}
            </div>

            {/* Industry Focus Areas */}
            {prompts[selectedIndustry] && (
              <div className="bg-brand-background dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-brand-text/10">
                <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-4">
                  <Settings className="inline-block w-5 h-5 mr-2" />
                  {selectedIndustry.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')} Focus
                </h3>
                
                <div className="space-y-3">
                  <div>
                    <h4 className="text-sm font-medium text-brand-text dark:text-white mb-2">
                      Focus Areas:
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {prompts[selectedIndustry].focus_areas.map((area, index) => (
                        <span
                          key={index}
                          className="px-2 py-1 bg-brand-accent/20 text-brand-primary dark:bg-brand-accent/20 dark:text-brand-accent rounded-full text-xs"
                        >
                          {area}
                        </span>
                      ))}
                    </div>
                  </div>
                  
                  <div>
                    <h4 className="text-sm font-medium text-brand-text dark:text-white mb-2">
                      Available Tools:
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {prompts[selectedIndustry].tools.map((tool, index) => (
                        <span
                          key={index}
                          className="px-2 py-1 bg-brand-secondary/20 text-brand-secondary dark:bg-brand-secondary/20 dark:text-brand-secondary rounded-full text-xs"
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
