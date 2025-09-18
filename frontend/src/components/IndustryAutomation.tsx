import React, { useState, useEffect } from 'react';
import { Building2, TrendingUp, Settings, CheckCircle } from 'lucide-react';

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
      // Mock data for now - replace with actual API call when backend endpoints are ready
      const mockPrompts = {
        landscaping: {
          industry: 'landscaping',
          tone: 'professional',
          focus_areas: ['appointment scheduling', 'service quotes', 'seasonal planning'],
          tools: ['calendar', 'quote_generator', 'weather_api'],
          pricing_tier: 'starter'
        },
        restaurant: {
          industry: 'restaurant',
          tone: 'friendly',
          focus_areas: ['reservation management', 'menu recommendations', 'special promotions'],
          tools: ['reservation_system', 'menu_api', 'promotion_tracker'],
          pricing_tier: 'professional'
        },
        medical_practice: {
          industry: 'medical_practice',
          tone: 'professional',
          focus_areas: ['appointment scheduling', 'patient reminders', 'HIPAA compliance'],
          tools: ['calendar', 'patient_portal', 'compliance_checker'],
          pricing_tier: 'premium'
        }
      };
      setPrompts(mockPrompts);
    } catch (error) {
      console.error('Failed to fetch industry prompts:', error)
      // Set fallback data
      setPrompts({
        landscaping: {
          industry: 'landscaping',
          tone: 'professional',
          focus_areas: ['appointment scheduling', 'service quotes', 'seasonal planning'],
          tools: ['calendar', 'quote_generator', 'weather_api'],
          pricing_tier: 'starter'
        }
      })
    }
  };

  const fetchPricingTiers = async () => {
    try {
      // Mock data for now - replace with actual API call when backend endpoints are ready
      const mockTiers = {
        starter: {
          name: 'Starter',
          price: 29,
          responses_limit: 1000,
          features: ['Basic AI responses', 'Email automation', 'CRM integration']
        },
        professional: {
          name: 'Professional',
          price: 79,
          responses_limit: 5000,
          features: ['Advanced AI responses', 'Multi-channel automation', 'Analytics dashboard']
        },
        premium: {
          name: 'Premium',
          price: 149,
          responses_limit: 15000,
          features: ['Custom AI training', 'API access', 'Priority support']
        },
        enterprise: {
          name: 'Enterprise',
          price: 299,
          responses_limit: 'unlimited',
          features: ['White-label solution', 'Custom integrations', 'Dedicated support']
        }
      };
      setPricingTiers(mockTiers);
    } catch (error) {
      console.error('Failed to fetch pricing tiers:', error)
      // Set fallback data
      setPricingTiers({
        starter: {
          name: 'Starter',
          price: 29,
          responses_limit: 1000,
          features: ['Basic AI responses', 'Email automation', 'CRM integration']
        }
      })
    }
  };

  const fetchClientAnalytics = async () => {
    try {
      // Mock data for now - replace with actual API call when backend endpoints are ready
      const mockAnalytics = {
        tier: 'professional',
        responses: 1250,
        tool_calls: 45,
        tokens: 125000,
        monthly_cost: 79
      };
      setUsageMetrics(mockAnalytics);
    } catch (error) {
      console.error('Failed to fetch client analytics:', error)
      // Set fallback data
      setUsageMetrics({
        tier: 'starter',
        responses: 0,
        tool_calls: 0,
        tokens: 0,
        monthly_cost: 29
      })
    }
  };

  const handleIndustryChat = async () => {
    if (!message.trim()) return;

    setIsLoading(true);
    try {
        // Use the main AI API endpoint
        const response = await fetch('https://fikirisolutions.onrender.com/api/ai/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message,
          user_id: 1, // Add user_id parameter
          context: {
            industry: selectedIndustry,
            client_id: clientId
          }
        }),
      });

      const data = await response.json();
      if (data.success) {
        setResponse(data.data?.response || 'No response received');
        setToolsUsed(data.data?.service_queries || []);
        setMessage('');
      } else {
        setResponse(`Error: ${data.error || 'Failed to get response'}`);
      }
    } catch (error) {
      setResponse(`Network error: ${error}`);
    } finally {
      setIsLoading(false);
    }
  };

  const getIndustryIcon = (industry: string) => {
    const icons: Record<string, string> = {
      // Food & Beverage
      'restaurant': '🍽️',
      'cafe': '☕',
      'food_truck': '🚚',
      
      // Real Estate
      'real_estate': '🏠',
      'property_management': '🏢',
      
      // Medical & Healthcare
      'medical_practice': '🏥',
      'dental_clinic': '🦷',
      'veterinary': '🐕',
      
      // Labor & Trades
      'landscaping': '🌱',
      'painting': '🎨',
      'carpenter': '🔨',
      'drywall': '🔧',
      'plumber': '🚰',
      'roofer': '🏠',
      
      // Transportation & Services
      'car_rental': '🚗',
      'ride_share': '🚕',
      
      // Creative & Marketing
      'content_creation': '📱',
      'marketing_agency': '📊',
      'photography': '📸',
      
      // Professional Services
      'tax_services': '📋',
      'accounting': '💰',
      'legal_services': '⚖️',
      
      // Retail & E-commerce
      'retail_store': '🛍️',
      'ecommerce': '💻'
    };
    return icons[industry] || '🏢';
  };

  const getIndustryCategory = (industry: string) => {
    const categories: Record<string, string> = {
      // Food & Beverage
      'restaurant': 'Food & Beverage',
      'cafe': 'Food & Beverage',
      'food_truck': 'Food & Beverage',
      
      // Real Estate
      'real_estate': 'Real Estate',
      'property_management': 'Real Estate',
      
      // Medical & Healthcare
      'medical_practice': 'Medical & Healthcare',
      'dental_clinic': 'Medical & Healthcare',
      'veterinary': 'Medical & Healthcare',
      
      // Labor & Trades
      'landscaping': 'Labor & Trades',
      'painting': 'Labor & Trades',
      'carpenter': 'Labor & Trades',
      'drywall': 'Labor & Trades',
      'plumber': 'Labor & Trades',
      'roofer': 'Labor & Trades',
      
      // Transportation & Services
      'car_rental': 'Transportation & Services',
      'ride_share': 'Transportation & Services',
      
      // Creative & Marketing
      'content_creation': 'Creative & Marketing',
      'marketing_agency': 'Creative & Marketing',
      'photography': 'Creative & Marketing',
      
      // Professional Services
      'tax_services': 'Professional Services',
      'accounting': 'Professional Services',
      'legal_services': 'Professional Services',
      
      // Retail & E-commerce
      'retail_store': 'Retail & E-commerce',
      'ecommerce': 'Retail & E-commerce'
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
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 transition-colors duration-300">
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
              
              {/* Industry Categories */}
              <div className="space-y-6">
                {Object.entries(
                  Object.entries(prompts).reduce((acc, [industry, config]) => {
                    const category = getIndustryCategory(industry);
                    if (!acc[category]) {
                      acc[category] = [];
                    }
                    acc[category].push({ industry, config });
                    return acc;
                  }, {} as Record<string, Array<{industry: string, config: IndustryPrompt}>>)
                ).map(([category, industries]: [string, Array<{industry: string, config: IndustryPrompt}>]) => (
                  <div key={category} className="space-y-3">
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-700 pb-2">
                      {category}
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                      {industries.map(({ industry, config }: {industry: string, config: IndustryPrompt}) => (
                        <button
                          key={industry}
                          onClick={() => setSelectedIndustry(industry)}
                          className={`p-4 rounded-lg border-2 transition-all duration-200 text-left hover:scale-105 ${
                            selectedIndustry === industry
                              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900 shadow-lg'
                              : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 hover:shadow-md'
                          }`}
                        >
                          <div className="flex items-start space-x-3">
                            <div className="text-2xl">{getIndustryIcon(industry)}</div>
                            <div className="flex-1 min-w-0">
                              <div className="font-medium text-gray-900 dark:text-white capitalize">
                                {industry.replace('_', ' ')}
                              </div>
                              <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                                {getIndustryDescription(industry)}
                              </div>
                              <div className={`inline-block px-2 py-1 rounded-full text-xs font-medium mt-2 ${getTierColor(config.pricing_tier)}`}>
                                {config.pricing_tier}
                              </div>
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
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
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:border-blue-500 dark:focus:border-blue-400 focus:ring-blue-500 dark:focus:ring-blue-400 transition-colors duration-200"
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
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:border-blue-500 dark:focus:border-blue-400 focus:ring-blue-500 dark:focus:ring-blue-400 transition-colors duration-200"
                    rows={3}
                    placeholder={`Test ${selectedIndustry} AI assistant...`}
                  />
                </div>

                <button
                  onClick={handleIndustryChat}
                  disabled={isLoading || !message.trim()}
                  className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium py-2 px-4 rounded-md transition-all duration-200 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900"
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
                {Object.entries(pricingTiers).map(([tier, config]) => {
                  // Check if this tier matches the selected industry's pricing tier
                  const isSelectedTier = selectedIndustry && prompts[selectedIndustry]?.pricing_tier === tier;
                  
                  return (
                    <div
                      key={tier}
                      className={`p-4 rounded-lg border transition-all duration-200 cursor-pointer hover:shadow-md ${
                        isSelectedTier
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900 shadow-lg'
                          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
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
                            professional: {
                              usagePercentage: 0.65, // 65% usage
                              toolCallRatio: 0.08,   // 8% of responses use tools
                              avgTokensPerResponse: 150
                            },
                            premium: {
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
                          
                          setUsageMetrics({
                            tier: tier,
                            responses: responses,
                            tool_calls: toolCalls,
                            tokens: tokens,
                            monthly_cost: tierConfig.price
                          });
                        }
                      }}
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
                  );
                })}
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
