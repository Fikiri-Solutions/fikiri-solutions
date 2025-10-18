import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useInView } from 'react-intersection-observer';
import { useRef } from 'react';
import { FikiriLogo } from '../components/FikiriLogo';
import SimpleAnimatedBackground from '../components/SimpleAnimatedBackground';
import { 
  Check, 
  ArrowRight, 
  Star,
  Building2,
  TrendingUp,
  Settings,
  Zap,
  Shield,
  Users,
  Crown,
  Sparkles
} from 'lucide-react';

interface PricingTier {
  name: string;
  price: number;
  period: string;
  description: string;
  features: string[];
  highlighted?: boolean;
  cta: string;
  responses_limit: number | string;
  buttonStyle: string;
  popular?: boolean;
}

const PricingPage: React.FC = () => {
  const navigate = useNavigate();
  const [billingPeriod, setBillingPeriod] = useState<'monthly' | 'yearly'>('monthly');
  
  // Animation refs
  const heroRef = useRef(null);
  const pricingRef = useRef(null);
  const featuresRef = useRef(null);
  const industriesRef = useRef(null);
  
  // Animation states
  const heroInView = useInView(heroRef, { once: true, margin: "-100px" });
  const pricingInView = useInView(pricingRef, { once: true, margin: "-100px" });
  const featuresInView = useInView(featuresRef, { once: true, margin: "-100px" });
  const industriesInView = useInView(industriesRef, { once: true, margin: "-100px" });

  const pricingTiers: PricingTier[] = [
    {
      name: 'Starter',
      price: billingPeriod === 'monthly' ? 39 : 390,
      period: billingPeriod === 'monthly' ? '/month' : '/year',
      description: 'Perfect for small businesses getting started with AI automation',
      responses_limit: 200,
      features: [
        '200 AI responses per month',
        'Basic email automation',
        'Simple CRM integration',
        '500 emails/month',
        'Community support',
        'Basic analytics'
      ],
      cta: 'Start Free Trial',
      buttonStyle: 'bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 text-white'
    },
    {
      name: 'Growth',
      price: billingPeriod === 'monthly' ? 79 : 790,
      period: billingPeriod === 'monthly' ? '/month' : '/year',
      description: 'For growing businesses that need advanced automation',
      responses_limit: 800,
      features: [
        '800 AI responses per month',
        'Advanced AI responses',
        'Advanced CRM features',
        '2,000 emails/month',
        'Priority email support',
        'Advanced analytics',
        'Basic integrations',
        'Workflow automation'
      ],
      highlighted: true,
      popular: true,
      cta: 'Start Free Trial',
      buttonStyle: 'bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-700 hover:to-red-700 text-white'
    },
    {
      name: 'Business',
      price: billingPeriod === 'monthly' ? 199 : 1990,
      period: billingPeriod === 'monthly' ? '/month' : '/year',
      description: 'For established businesses needing comprehensive solutions',
      responses_limit: 4000,
      features: [
        '4,000 AI responses per month',
        'White-label options',
        'Custom integrations',
        '10,000 emails/month',
        'Phone support',
        'Advanced analytics',
        'Multi-user access',
        'API access',
        'Custom workflows'
      ],
      cta: 'Start Free Trial',
      buttonStyle: 'bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 text-white'
    },
    {
      name: 'Enterprise',
      price: billingPeriod === 'monthly' ? 399 : 3990,
      period: billingPeriod === 'monthly' ? '/month' : '/year',
      description: 'For large organizations with custom requirements',
      responses_limit: 'unlimited',
      features: [
        'Unlimited AI responses',
        'Custom AI training',
        'Dedicated support team',
        'SLA guarantee',
        'Unlimited emails',
        'White-label platform',
        'Custom integrations',
        'On-premise deployment',
        'Advanced security'
      ],
      cta: 'Contact Sales',
      buttonStyle: 'bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 text-white'
    }
  ];

  const industries = [
    {
      name: 'Landscaping',
      icon: '🌱',
      tier: 'Starter',
      price: billingPeriod === 'monthly' ? 39 : 390,
      features: ['Appointment scheduling', 'Service quotes', 'Seasonal planning']
    },
    {
      name: 'Restaurant',
      icon: '🍽️',
      tier: 'Growth',
      price: billingPeriod === 'monthly' ? 79 : 790,
      features: ['Reservation management', 'Menu recommendations', 'Special promotions']
    },
    {
      name: 'Medical Practice',
      icon: '🏥',
      tier: 'Business',
      price: billingPeriod === 'monthly' ? 199 : 1990,
      features: ['Appointment scheduling', 'Patient reminders', 'HIPAA compliance']
    },
    {
      name: 'Real Estate',
      icon: '🏠',
      tier: 'Business',
      price: billingPeriod === 'monthly' ? 199 : 1990,
      features: ['Property listings', 'Client consultations', 'Market analysis']
    },
    {
      name: 'E-commerce',
      icon: '🛍️',
      tier: 'Growth',
      price: billingPeriod === 'monthly' ? 79 : 790,
      features: ['Order management', 'Customer support', 'Inventory sync']
    },
    {
      name: 'Enterprise Solutions',
      icon: '🏢',
      tier: 'Enterprise',
      price: billingPeriod === 'monthly' ? 399 : 3990,
      features: ['Custom workflows', 'Multi-industry support', 'Advanced analytics']
    }
  ];

  const comparisonFeatures = [
    {
      category: 'Core Features',
      features: [
        { name: 'AI Responses per month', starter: '200', growth: '800', business: '4,000', enterprise: 'Unlimited' },
        { name: 'Email automation', starter: true, growth: true, business: true, enterprise: true },
        { name: 'Email limit per month', starter: '500', growth: '2,000', business: '10,000', enterprise: 'Unlimited' },
        { name: 'CRM integration', starter: 'Basic', growth: 'Advanced', business: 'Advanced', enterprise: 'Custom' },
        { name: 'Analytics', starter: 'Basic', growth: 'Advanced', business: 'Advanced', enterprise: 'Custom' },
        { name: 'Integrations', starter: 'Basic', growth: 'Basic', business: 'Custom', enterprise: 'Custom' }
      ]
    },
    {
      category: 'Support & Training',
      features: [
        { name: 'Support', starter: 'Community', growth: 'Priority Email', business: 'Phone', enterprise: 'Dedicated team' },
        { name: 'Onboarding', starter: 'Self-service', growth: 'Guided', business: 'White-glove', enterprise: 'Custom' },
        { name: 'Training', starter: false, growth: false, business: true, enterprise: 'Custom' },
        { name: 'SLA', starter: false, growth: false, business: false, enterprise: true },
        { name: 'Multi-user access', starter: false, growth: false, business: true, enterprise: true },
        { name: 'API access', starter: false, growth: false, business: true, enterprise: true }
      ]
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-orange-900/30 to-red-900/30 text-white overflow-hidden relative" style={{
      background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 20%, #FF6B35 40%, #D2691E 60%, #8B0000 80%, #991b1b 100%)'
    }}>
      {/* Header Navigation */}
      <header className="relative z-20 w-full px-4 sm:px-6 lg:px-8 py-6">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <button 
            onClick={() => navigate('/')}
            className="flex items-center space-x-3 hover:opacity-80 transition-opacity duration-200"
            aria-label="Fikiri Solutions - Return to homepage"
          >
            <FikiriLogo 
              size="xl" 
              variant="full" 
              animated={true}
              className="hover:scale-105 transition-transform duration-200"
            />
          </button>
          
          <nav className="hidden md:flex items-center space-x-8">
            <button onClick={() => navigate('/')} className="text-white hover:text-orange-200 transition-colors">Home</button>
            <button onClick={() => navigate('/services')} className="text-white hover:text-orange-200 transition-colors">Features</button>
            <button onClick={() => navigate('/industry')} className="text-white hover:text-orange-200 transition-colors">Industries</button>
            <span className="text-orange-200 font-medium">Pricing</span>
          </nav>

          <div className="flex items-center space-x-4">
            <button
              onClick={() => navigate('/login')}
              className="px-4 py-2 text-white hover:text-orange-200 transition-colors"
            >
              Sign in
            </button>
            <button
              onClick={() => navigate('/signup')}
              className="px-6 py-2 bg-gradient-to-r from-orange-600 to-red-600 text-white font-semibold rounded-lg hover:from-orange-700 hover:to-red-700 transition-all duration-300" style={{
                background: 'linear-gradient(to right, #FF6B35, #8B0000)'
              }}
            >
              Get started
            </button>
          </div>
        </div>
      </header>

      {/* Simple Animated Background - CSS-based mesh effect */}
      <SimpleAnimatedBackground />

      {/* Hero Section */}
      <section ref={heroRef} className="relative z-10 py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={heroInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
            transition={{ duration: 0.8 }}
          >
            <h1 className="text-4xl sm:text-6xl font-bold mb-6 bg-gradient-to-r from-orange-400 via-orange-500 to-red-600 bg-clip-text text-transparent" style={{
              background: 'linear-gradient(to right, #FF6B35, #D2691E, #8B0000)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent'
            }}>
              Plans for businesses of any size
            </h1>
            <p className="text-xl text-gray-200 mb-8">
              Get all the Fikiri Solutions features — pay for what you use
            </p>
          </motion.div>

          {/* Billing Toggle */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={heroInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="flex items-center justify-center mb-12"
          >
            <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-1 border border-gray-700">
              <button
                onClick={() => setBillingPeriod('monthly')}
                className={`px-6 py-2 rounded-md font-medium transition-all duration-300 ${
                  billingPeriod === 'monthly'
                    ? 'bg-gradient-to-r from-orange-500 to-red-500 text-white'
                    : 'text-white hover:text-orange-200'
                }`}
              >
                Monthly
              </button>
              <button
                onClick={() => setBillingPeriod('yearly')}
                className={`px-6 py-2 rounded-md font-medium transition-all duration-300 ${
                  billingPeriod === 'yearly'
                    ? 'bg-gradient-to-r from-orange-500 to-red-500 text-white'
                    : 'text-white hover:text-orange-200'
                }`}
              >
                <span>Yearly</span>
                <span className="ml-2 text-xs bg-green-500 text-white px-2 py-1 rounded-full">Save 17%</span>
              </button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Pricing Cards */}
      <section ref={pricingRef} className="relative z-10 py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {pricingTiers.map((tier, index) => (
              <motion.div
                key={tier.name}
                initial={{ opacity: 0, y: 30 }}
                animate={pricingInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                className={`relative bg-gray-800/50 backdrop-blur-sm rounded-2xl p-8 border transition-all duration-300 hover:scale-105 ${
                  tier.highlighted
                    ? 'border-orange-500 shadow-2xl shadow-orange-500/20'
                    : 'border-gray-700 hover:border-orange-500/50'
                }`}
              >
                {tier.popular && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                    <div className="bg-gradient-to-r from-orange-500 to-red-500 text-white px-4 py-2 rounded-full text-sm font-medium flex items-center gap-2">
                      <Star className="w-4 h-4" />
                      Most Popular
                    </div>
                  </div>
                )}

                <div className="text-center mb-8">
                  <h3 className="text-2xl font-bold text-white mb-2">{tier.name}</h3>
                  <div className="flex items-center justify-center mb-4">
                    <span className="text-4xl font-bold text-white">${tier.price}</span>
                    <span className="text-gray-300 ml-2">{tier.period}</span>
                  </div>
                  <p className="text-white text-sm">{tier.description}</p>
                </div>

                <ul className="space-y-3 mb-8">
                  {tier.features.map((feature, featureIndex) => (
                    <li key={featureIndex} className="flex items-center text-white">
                      <Check className="w-5 h-5 text-green-400 mr-3 flex-shrink-0" />
                      <span className="text-sm">{feature}</span>
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => {
                    if (tier.name === 'Enterprise') {
                      // Navigate to contact or demo page
                      navigate('/onboarding-flow');
                    } else {
                      navigate('/signup');
                    }
                  }}
                  className={`w-full py-3 px-6 rounded-lg font-semibold transition-all duration-300 transform hover:scale-105 ${tier.buttonStyle}`}
                >
                  {tier.cta}
                </button>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Industry-Specific Pricing */}
      <section ref={industriesRef} className="relative z-10 py-20 px-4 sm:px-6 lg:px-8 bg-gray-800/30">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={industriesInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl sm:text-4xl font-bold mb-4 bg-gradient-to-r from-orange-400 via-orange-500 to-red-600 bg-clip-text text-transparent" style={{
              background: 'linear-gradient(to right, #FF6B35, #D2691E, #8B0000)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent'
            }}>
              Industry-Specific Solutions
            </h2>
            <p className="text-xl text-gray-200 max-w-2xl mx-auto">
              Tailored automation for your specific industry needs
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {industries.map((industry, index) => (
              <motion.div
                key={industry.name}
                initial={{ opacity: 0, y: 30 }}
                animate={industriesInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6 border border-gray-700 hover:border-orange-500/50 transition-all duration-300"
              >
                <div className="text-center mb-4">
                  <div className="text-4xl mb-2">{industry.icon}</div>
                  <h3 className="text-xl font-semibold text-white">{industry.name}</h3>
                  <div className="flex items-center justify-center gap-2 mt-2">
                    <span className="text-orange-400 font-medium">{industry.tier}</span>
                    <span className="text-white font-bold">${industry.price}{billingPeriod === 'monthly' ? '/mo' : '/yr'}</span>
                  </div>
                </div>

                <ul className="space-y-2">
                  {industry.features.map((feature, featureIndex) => (
                    <li key={featureIndex} className="flex items-center text-white text-sm">
                      <Check className="w-4 h-4 text-green-400 mr-2 flex-shrink-0" />
                      {feature}
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => navigate('/industry')}
                  className="w-full mt-4 py-2 px-4 bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 text-white font-medium rounded-lg transition-all duration-300"
                >
                  Try {industry.name} AI
                </button>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Feature Comparison */}
      <section ref={featuresRef} className="relative z-10 py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={featuresInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl sm:text-4xl font-bold mb-4 bg-gradient-to-r from-orange-400 via-orange-500 to-red-600 bg-clip-text text-transparent" style={{
              background: 'linear-gradient(to right, #FF6B35, #D2691E, #8B0000)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent'
            }}>
              Compare Plans
            </h2>
          </motion.div>

          <div className="bg-gray-800/50 backdrop-blur-sm rounded-2xl border border-gray-700 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="text-left p-6 text-white font-semibold">Features</th>
                    <th className="text-center p-6 text-white font-semibold">Starter</th>
                    <th className="text-center p-6 text-white font-semibold">Growth</th>
                    <th className="text-center p-6 text-white font-semibold">Business</th>
                    <th className="text-center p-6 text-white font-semibold">Enterprise</th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonFeatures.map((category, categoryIndex) => (
                    <React.Fragment key={category.category}>
                      <tr className="border-b border-gray-700">
                        <td colSpan={5} className="p-4 text-orange-400 font-semibold text-sm uppercase tracking-wider">
                          {category.category}
                        </td>
                      </tr>
                      {category.features.map((feature, featureIndex) => (
                        <tr key={featureIndex} className="border-b border-gray-700/50">
                          <td className="p-4 text-white">{feature.name}</td>
                          <td className="p-4 text-center text-white">
                            {typeof feature.starter === 'boolean' 
                              ? (feature.starter ? <Check className="w-5 h-5 text-green-400 mx-auto" /> : '—')
                              : feature.starter
                            }
                          </td>
                          <td className="p-4 text-center text-white">
                            {typeof feature.growth === 'boolean' 
                              ? (feature.growth ? <Check className="w-5 h-5 text-green-400 mx-auto" /> : '—')
                              : feature.growth
                            }
                          </td>
                          <td className="p-4 text-center text-white">
                            {typeof feature.business === 'boolean' 
                              ? (feature.business ? <Check className="w-5 h-5 text-green-400 mx-auto" /> : '—')
                              : feature.business
                            }
                          </td>
                          <td className="p-4 text-center text-white">
                            {typeof feature.enterprise === 'boolean' 
                              ? (feature.enterprise ? <Check className="w-5 h-5 text-green-400 mx-auto" /> : '—')
                              : feature.enterprise
                            }
                          </td>
                        </tr>
                      ))}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="relative z-10 py-20 px-4 sm:px-6 lg:px-8 bg-gray-800/30">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4 bg-gradient-to-r from-orange-400 via-orange-500 to-red-600 bg-clip-text text-transparent" style={{
              background: 'linear-gradient(to right, #FF6B35, #D2691E, #8B0000)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent'
            }}>
              Frequently Asked Questions
            </h2>
          </div>

          <div className="space-y-6">
            {[
              {
                question: "Which plan is right for me?",
                answer: "Our Starter plan is great for small businesses just getting started. The Growth plan is perfect for businesses that need advanced features and higher usage limits. Business plan is ideal for established companies, and Enterprise is for large organizations with custom needs."
              },
              {
                question: "Can I change plans anytime?",
                answer: "Yes! You can upgrade or downgrade your plan at any time. Changes take effect immediately, and we'll prorate any billing differences."
              },
              {
                question: "Do you offer a free trial?",
                answer: "Yes, all plans come with a 14-day free trial. No credit card required to get started."
              },
              {
                question: "What happens if I exceed my response limit?",
                answer: "We'll notify you when you're approaching your limit. You can upgrade your plan or purchase additional responses as needed."
              }
            ].map((faq, index) => (
              <div key={index} className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6 border border-gray-700">
                <h3 className="text-lg font-semibold text-white mb-3">{faq.question}</h3>
                <p className="text-white">{faq.answer}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative z-10 py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl sm:text-4xl font-bold mb-6 bg-gradient-to-r from-orange-400 via-orange-500 to-red-600 bg-clip-text text-transparent" style={{
            background: 'linear-gradient(to right, #FF6B35, #D2691E, #8B0000)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent'
          }}>
            Ready to start automating?
          </h2>
          <p className="text-xl text-gray-200 mb-8">
            Get started with a free trial. No credit card required.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button
              onClick={() => navigate('/signup')}
              className="px-8 py-4 bg-gradient-to-r from-orange-600 to-red-600 text-white font-semibold rounded-lg hover:from-orange-700 hover:to-red-700 transition-all duration-300 transform hover:scale-105 flex items-center justify-center gap-2" style={{
                background: 'linear-gradient(to right, #FF6B35, #8B0000)'
              }}
            >
              Start Free Trial
              <ArrowRight className="w-5 h-5" />
            </button>
            <button
              onClick={() => navigate('/onboarding-flow')}
              className="px-8 py-4 border border-orange-400 text-white font-semibold rounded-lg hover:bg-orange-500/20 hover:border-orange-300 transition-all duration-300"
            >
              Schedule Demo
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 py-12 px-4 sm:px-6 lg:px-8 border-t border-gray-800">
        <div className="max-w-7xl mx-auto text-center">
          <p className="text-gray-300">&copy; 2024 Fikiri Solutions. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
};

export default PricingPage;
