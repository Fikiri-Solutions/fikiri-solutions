import React from 'react';
import { CheckCircle, Star, Users, Zap, Shield, Clock } from 'lucide-react';
import { FeatureStatus, getFeatureStatus } from '../components/FeatureStatus';

export const ServicesLanding: React.FC = () => {
  const features = [
    {
      icon: <Zap className="h-6 w-6 text-blue-500" />,
      title: "AI Email Assistant",
      description: "Automatically respond to customer inquiries with intelligent, context-aware replies",
      status: getFeatureStatus('ai-assistant')
    },
    {
      icon: <Users className="h-6 w-6 text-green-500" />,
      title: "Smart CRM",
      description: "Track leads, manage customer relationships, and score prospects automatically",
      status: getFeatureStatus('crm')
    },
    {
      icon: <Shield className="h-6 w-6 text-purple-500" />,
      title: "Enterprise Security",
      description: "Bank-level security with SOC2 compliance and data encryption",
      status: getFeatureStatus('auth')
    },
    {
      icon: <Clock className="h-6 w-6 text-orange-500" />,
      title: "24/7 Automation",
      description: "Never miss a lead with round-the-clock email processing and follow-ups",
      status: getFeatureStatus('automation')
    }
  ];

  const pricingTiers = [
    {
      name: "Starter",
      price: "$39",
      period: "/month",
      description: "Perfect for small businesses",
      features: [
        "Up to 500 emails/month",
        "Basic AI responses",
        "Simple CRM",
        "Email support",
        "Gmail integration"
      ],
      cta: "Start Free Trial",
      popular: false
    },
    {
      name: "Growth",
      price: "$79",
      period: "/month",
      description: "For growing businesses",
      features: [
        "Up to 2,000 emails/month",
        "Advanced AI responses",
        "Advanced CRM",
        "Priority support",
        "Gmail + Outlook integration",
        "Custom templates",
        "Analytics dashboard"
      ],
      cta: "Start Free Trial",
      popular: true
    },
    {
      name: "Business",
      price: "$199",
      period: "/month",
      description: "For established businesses",
      features: [
        "Up to 10,000 emails/month",
        "White-label options",
        "Custom integrations",
        "Phone support",
        "All integrations",
        "Custom workflows",
        "API access"
      ],
      cta: "Start Free Trial",
      popular: false
    },
    {
      name: "Enterprise",
      price: "$399",
      period: "/month",
      description: "For large organizations",
      features: [
        "Unlimited emails",
        "Custom AI training",
        "Unlimited contacts",
        "Dedicated support",
        "All integrations",
        "Custom workflows",
        "API access",
        "White-label options",
        "SLA guarantee"
      ],
      cta: "Contact Sales",
      popular: false
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Hero Section */}
      <div className="container mx-auto px-4 py-16">
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            Automate Your Customer Communication
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
            Fikiri Solutions uses AI to automatically respond to customer emails, 
            manage leads, and grow your business while you sleep.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button className="bg-blue-600 text-white px-8 py-3 rounded-lg text-lg font-semibold hover:bg-blue-700 transition-colors">
              Start Free Trial
            </button>
            <button className="border border-blue-600 text-blue-600 px-8 py-3 rounded-lg text-lg font-semibold hover:bg-blue-50 transition-colors">
              Book a Demo
            </button>
          </div>
        </div>

        {/* Demo Video Placeholder */}
        <div className="bg-white rounded-xl shadow-lg p-8 mb-16">
          <div className="aspect-video bg-gray-200 rounded-lg flex items-center justify-center">
            <div className="text-center">
              <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M8 5v10l8-5-8-5z"/>
                </svg>
              </div>
              <p className="text-gray-600">Watch Demo Video</p>
            </div>
          </div>
        </div>

        {/* Features Section */}
        <div className="mb-16">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
            Everything You Need to Scale Your Business
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <div key={index} className="bg-white p-6 rounded-xl shadow-lg">
                <div className="flex items-center justify-between mb-4">
                  {feature.icon}
                  <FeatureStatus status={feature.status} />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  {feature.title}
                </h3>
                <p className="text-gray-600">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Status Disclaimer */}
        <div className="mb-16">
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-blue-900 mb-3">
              🚀 Current Platform Status
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div className="flex items-center gap-2">
                <FeatureStatus status="live" />
                <span className="text-blue-800">Fully operational</span>
              </div>
              <div className="flex items-center gap-2">
                <FeatureStatus status="beta" />
                <span className="text-blue-800">In active development</span>
              </div>
              <div className="flex items-center gap-2">
                <FeatureStatus status="coming-soon" />
                <span className="text-blue-800">Coming soon</span>
              </div>
            </div>
            <p className="text-blue-700 mt-3 text-sm">
              We're continuously improving our platform. Beta features are fully functional but may have limited configurations.
            </p>
          </div>
        </div>
        <div className="mb-16">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
            Simple, Transparent Pricing
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {pricingTiers.map((tier, index) => (
              <div key={index} className={`bg-white p-8 rounded-xl shadow-lg relative ${tier.popular ? 'ring-2 ring-blue-500' : ''}`}>
                {tier.popular && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                    <span className="bg-blue-500 text-white px-4 py-1 rounded-full text-sm font-semibold">
                      Most Popular
                    </span>
                  </div>
                )}
                
                <div className="text-center mb-6">
                  <h3 className="text-2xl font-bold text-gray-900 mb-2">{tier.name}</h3>
                  <div className="flex items-baseline justify-center mb-2">
                    <span className="text-4xl font-bold text-gray-900">{tier.price}</span>
                    <span className="text-gray-600 ml-1">{tier.period}</span>
                  </div>
                  <p className="text-gray-600">{tier.description}</p>
                </div>

                <ul className="space-y-3 mb-8">
                  {tier.features.map((feature, featureIndex) => (
                    <li key={featureIndex} className="flex items-center">
                      <CheckCircle className="h-5 w-5 text-green-500 mr-3" />
                      <span className="text-gray-700">{feature}</span>
                    </li>
                  ))}
                </ul>

                <button className={`w-full py-3 rounded-lg font-semibold transition-colors ${
                  tier.popular 
                    ? 'bg-blue-600 text-white hover:bg-blue-700' 
                    : 'border border-gray-300 text-gray-700 hover:bg-gray-50'
                }`}>
                  {tier.cta}
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Social Proof */}
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-8">
            Trusted by Growing Businesses
          </h2>
          <div className="flex items-center justify-center space-x-8 opacity-60">
            <div className="text-2xl font-bold text-gray-400">500+</div>
            <div className="text-gray-400">Happy Customers</div>
            <div className="flex items-center">
              {[...Array(5)].map((_, i) => (
                <Star key={i} className="h-5 w-5 text-yellow-400 fill-current" />
              ))}
              <span className="ml-2 text-gray-400">4.9/5 Rating</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

