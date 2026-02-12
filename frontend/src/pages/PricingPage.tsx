import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useInView } from 'react-intersection-observer';
import { RadiantLayout, Gradient, Container } from '../components/radiant';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '../services/apiClient';
import { useToast } from '../components/Toast';
import { 
  Check, 
  ArrowRight, 
  Star,
  Loader2,
  CreditCard
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
  const { isAuthenticated } = useAuth();
  const [searchParams] = useSearchParams();
  const { addToast } = useToast();
  const [billingPeriod, setBillingPeriod] = useState<'monthly' | 'yearly'>('monthly');
  const [purchaseType, setPurchaseType] = useState<'trial' | 'immediate'>('trial');
  const [loadingTier, setLoadingTier] = useState<string | null>(null);
  const [hasAutoCheckedOut, setHasAutoCheckedOut] = useState(false);
  
  // Extract checkout logic to reusable function
  const handleCheckout = React.useCallback(async (tierName: string, showToast: boolean = true) => {
    if (loadingTier) return;
    
    try {
      setLoadingTier(tierName);
      const billingPeriodParam = billingPeriod === 'monthly' ? 'monthly' : 'annual';
      const useTrial = purchaseType === 'trial';
      
      if (showToast) {
        addToast({
          type: 'info',
          title: useTrial ? 'Starting Free Trial' : 'Starting Subscription',
          message: useTrial 
            ? 'Card required for verification. You won\'t be charged during your 14-day trial.'
            : 'You\'ll be charged immediately and can start using all features right away.'
        });
      }

      const { checkout_url } = await apiClient.createCheckoutSession(tierName, billingPeriodParam, useTrial);
      window.location.href = checkout_url;
    } catch (error: any) {
      const errorMessage = error?.response?.data?.error || error?.message || 'Failed to start checkout. Please try again.';
      addToast({
        type: 'error',
        title: 'Checkout Failed',
        message: errorMessage
      });
      setLoadingTier(null);
    }
  }, [loadingTier, billingPeriod, purchaseType, addToast]);
  
  // Check for canceled parameter and pre-selected plan
  React.useEffect(() => {
    if (searchParams.get('canceled') === 'true') {
      addToast({
        type: 'info',
        title: 'Checkout Canceled',
        message: 'You can return anytime to select a plan.'
      });
      navigate('/pricing', { replace: true });
      return;
    }
    
    // Check if plan is pre-selected from signup
    const planParam = searchParams.get('plan');
    const billingParam = searchParams.get('billing');
    const autoCheckout = searchParams.get('autoCheckout') === 'true';
    
    if (planParam && isAuthenticated && !hasAutoCheckedOut && autoCheckout) {
      // Set billing period if provided
      if (billingParam === 'annual' || billingParam === 'yearly') {
        setBillingPeriod('yearly');
      }
      
      // Auto-trigger checkout
      setHasAutoCheckedOut(true);
      addToast({
        type: 'success',
        title: 'Account Created!',
        message: 'Starting checkout process...'
      });
      
      // Skip Enterprise tier, trigger checkout for others
      const tierName = planParam.toLowerCase();
      if (tierName !== 'enterprise') {
        handleCheckout(tierName, false);
      }
    } else if (planParam && isAuthenticated && !hasAutoCheckedOut) {
      // Plan selected but no auto-checkout - just show message
      if (billingParam === 'annual' || billingParam === 'yearly') {
        setBillingPeriod('yearly');
      }
      addToast({
        type: 'success',
        title: 'Account Created!',
        message: 'Click "Start Free Trial" to begin your subscription.'
      });
    }
  }, [searchParams, addToast, navigate, isAuthenticated, hasAutoCheckedOut, handleCheckout]);
  
  // Animation states
  const { ref: heroRef, inView: heroInView } = useInView({ triggerOnce: true });
  const { ref: pricingRef, inView: pricingInView } = useInView({ triggerOnce: true });
  const { ref: featuresRef, inView: featuresInView } = useInView({ triggerOnce: true });
  const { ref: industriesRef, inView: industriesInView } = useInView({ triggerOnce: true });

  const pricingTiers: PricingTier[] = [
    {
      name: 'Starter',
      price: billingPeriod === 'monthly' ? 39 : (39 * 12) - Math.round(39 * 12 * 0.10), // Exactly 10% discount
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
      buttonStyle: 'bg-brand-primary hover:bg-fikiri-400 text-white'
    },
    {
      name: 'Growth',
      price: billingPeriod === 'monthly' ? 79 : (79 * 12) - Math.round(79 * 12 * 0.10), // Exactly 10% discount
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
      buttonStyle: 'bg-brand-primary hover:bg-fikiri-400 text-white'
    },
    {
      name: 'Business',
      price: billingPeriod === 'monthly' ? 199 : (199 * 12) - Math.round(199 * 12 * 0.10), // Exactly 10% discount
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
      buttonStyle: 'bg-brand-primary hover:bg-fikiri-400 text-white'
    },
    {
      name: 'Enterprise',
      price: billingPeriod === 'monthly' ? 399 : (399 * 12) - Math.round(399 * 12 * 0.10), // Exactly 10% discount
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
      buttonStyle: 'bg-brand-primary hover:bg-fikiri-400 text-white'
    }
  ];

  const industries = [
    {
      name: 'Real Estate',
      icon: '🏠',
      tier: 'Business',
      price: billingPeriod === 'monthly' ? 199 : (199 * 12) - Math.round(199 * 12 * 0.10), // Exactly 10% discount
      features: ['Property listings', 'Client consultations', 'Market analysis', 'Showings scheduling']
    },
    {
      name: 'Property Management',
      icon: '🏘️',
      tier: 'Growth',
      price: billingPeriod === 'monthly' ? 79 : (79 * 12) - Math.round(79 * 12 * 0.10), // Exactly 10% discount
      features: ['Tenant communication', 'Maintenance requests', 'Lease renewals', 'Rent collection']
    },
    {
      name: 'Construction',
      icon: '🔨',
      tier: 'Growth',
      price: billingPeriod === 'monthly' ? 79 : (79 * 12) - Math.round(79 * 12 * 0.10), // Exactly 10% discount
      features: ['Project quotes', 'Client communication', 'Scheduling', 'Material orders']
    },
    {
      name: 'Legal Services',
      icon: '⚖️',
      tier: 'Business',
      price: billingPeriod === 'monthly' ? 199 : (199 * 12) - Math.round(199 * 12 * 0.10), // Exactly 10% discount
      features: ['Client intake', 'Appointment scheduling', 'Document management', 'Case updates']
    },
    {
      name: 'Cleaning Services',
      icon: '🧹',
      tier: 'Starter',
      price: billingPeriod === 'monthly' ? 39 : (39 * 12) - Math.round(39 * 12 * 0.10), // Exactly 10% discount
      features: ['Service scheduling', 'Quote requests', 'Recurring appointments', 'Customer follow-up']
    },
    {
      name: 'Auto Services',
      icon: '🚗',
      tier: 'Starter',
      price: billingPeriod === 'monthly' ? 39 : (39 * 12) - Math.round(39 * 12 * 0.10), // Exactly 10% discount
      features: ['Appointment booking', 'Service reminders', 'Estimate requests', 'Customer follow-up']
    },
    {
      name: 'Event Planning',
      icon: '🎉',
      tier: 'Growth',
      price: billingPeriod === 'monthly' ? 79 : (79 * 12) - Math.round(79 * 12 * 0.10), // Exactly 10% discount
      features: ['Client consultations', 'Vendor coordination', 'Timeline management', 'Follow-up']
    },
    {
      name: 'Fitness & Wellness',
      icon: '💪',
      tier: 'Starter',
      price: billingPeriod === 'monthly' ? 39 : (39 * 12) - Math.round(39 * 12 * 0.10), // Exactly 10% discount
      features: ['Class scheduling', 'Membership inquiries', 'Appointment booking', 'Wellness tips']
    },
    {
      name: 'Beauty & Spa',
      icon: '💅',
      tier: 'Starter',
      price: billingPeriod === 'monthly' ? 39 : (39 * 12) - Math.round(39 * 12 * 0.10), // Exactly 10% discount
      features: ['Appointment booking', 'Service inquiries', 'Reminders', 'Promotions']
    },
    {
      name: 'Accounting & Consulting',
      icon: '📊',
      tier: 'Business',
      price: billingPeriod === 'monthly' ? 199 : (199 * 12) - Math.round(199 * 12 * 0.10), // Exactly 10% discount
      features: ['Client onboarding', 'Appointment scheduling', 'Document requests', 'Tax reminders']
    },
    {
      name: 'Restaurant',
      icon: '🍽️',
      tier: 'Growth',
      price: billingPeriod === 'monthly' ? 79 : (79 * 12) - Math.round(79 * 12 * 0.10), // Exactly 10% discount
      features: ['Reservation management', 'Menu recommendations', 'Special promotions', 'Catering inquiries']
    },
    {
      name: 'Medical Practice',
      icon: '🏥',
      tier: 'Business',
      price: billingPeriod === 'monthly' ? 199 : (199 * 12) - Math.round(199 * 12 * 0.10), // Exactly 10% discount
      features: ['Appointment scheduling', 'Patient reminders', 'HIPAA compliance', 'Follow-up care']
    },
    {
      name: 'Enterprise Solutions',
      icon: '🏢',
      tier: 'Enterprise',
      price: billingPeriod === 'monthly' ? 399 : (399 * 12) - Math.round(399 * 12 * 0.10), // Exactly 10% discount
      features: ['Custom workflows', 'Multi-industry support', 'Advanced analytics', 'White-label options']
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
    <RadiantLayout>
    <div className="min-h-screen bg-background text-foreground overflow-hidden">
      {/* Hero Section */}
      <section ref={heroRef} className="relative py-16 sm:py-20">
        <Container>
          <div className="max-w-4xl mx-auto text-center">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={heroInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
              transition={{ duration: 0.8 }}
            >
              <h1 className="text-4xl sm:text-6xl font-bold mb-6 text-foreground">
                Plans for businesses of any size
              </h1>
              <p className="text-xl text-muted-foreground mb-4">
                Get all the Fikiri Solutions features — pay for what you use
              </p>
              <p className="text-sm text-muted-foreground mb-8">
                {purchaseType === 'trial' ? (
                  <span className="inline-flex items-center gap-2">
                    <CreditCard className="w-4 h-4" />
                    Card required for free trial verification. No charge during trial period.
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-2">
                    <CreditCard className="w-4 h-4" />
                    Start using all features immediately. Charged today.
                  </span>
                )}
              </p>
            </motion.div>

            {/* Billing Toggle */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={heroInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
              transition={{ duration: 0.8, delay: 0.2 }}
              className="flex flex-col items-center justify-center mb-8 gap-4"
            >
              <div className="bg-card rounded-lg p-1 border border-border shadow-sm">
                <button
                  onClick={() => setBillingPeriod('monthly')}
                  className={`px-6 py-2 rounded-md font-medium transition-all duration-300 ${
                    billingPeriod === 'monthly'
                      ? 'bg-brand-primary text-white'
                      : 'text-foreground hover:bg-muted'
                  }`}
                >
                  Monthly
                </button>
                <button
                  onClick={() => setBillingPeriod('yearly')}
                  className={`px-6 py-2 rounded-md font-medium transition-all duration-300 ${
                    billingPeriod === 'yearly'
                      ? 'bg-brand-primary text-white'
                      : 'text-foreground hover:bg-muted'
                  }`}
                >
                  <span>Yearly</span>
                  <span className="ml-2 text-xs bg-green-600 text-white px-2 py-1 rounded-full">Save 10%</span>
                </button>
              </div>

              <div className="bg-card rounded-lg p-1 border border-border shadow-sm">
                <button
                  onClick={() => setPurchaseType('trial')}
                  className={`px-6 py-2 rounded-md font-medium transition-all duration-300 ${
                    purchaseType === 'trial'
                      ? 'bg-brand-primary text-white'
                      : 'text-foreground hover:bg-muted'
                  }`}
                >
                  <span>Free Trial</span>
                  <span className="ml-2 text-xs bg-brand-primary/90 text-white px-2 py-1 rounded-full">14 days</span>
                </button>
                <button
                  onClick={() => setPurchaseType('immediate')}
                  className={`px-6 py-2 rounded-md font-medium transition-all duration-300 ${
                    purchaseType === 'immediate'
                      ? 'bg-brand-primary text-white'
                      : 'text-foreground hover:bg-muted'
                  }`}
                >
                  Start Now
                </button>
              </div>
            </motion.div>
          </div>
        </Container>
      </section>

      {/* Pricing Cards - Radiant-style gradient behind */}
      <section ref={pricingRef} className="relative py-20">
        <Gradient className="absolute inset-x-2 top-24 bottom-0 rounded-3xl ring-1 ring-black/5 ring-inset opacity-30" />
        <Container className="relative">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {pricingTiers.map((tier, index) => (
              <motion.div
                key={tier.name}
                initial={{ opacity: 0, y: 30 }}
                animate={pricingInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                className={`relative bg-card rounded-2xl p-8 border border-border shadow-lg ring-1 ring-black/5 transition-all duration-300 hover:shadow-xl ${
                  tier.highlighted
                    ? 'ring-2 ring-brand-primary/30'
                    : 'hover:border-brand-primary/30'
                }`}
              >
                {tier.popular && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                    <div className="bg-brand-primary text-white px-4 py-2 rounded-full text-sm font-medium flex items-center gap-2 shadow-md">
                      <Star className="w-4 h-4" />
                      Most Popular
                    </div>
                  </div>
                )}

                <div className="text-center mb-8">
                  <h3 className="text-2xl font-bold text-foreground mb-2">{tier.name}</h3>
                  <div className="flex items-center justify-center mb-4">
                    <span className="text-4xl font-bold text-foreground">${tier.price}</span>
                    <span className="text-muted-foreground ml-2">{tier.period}</span>
                  </div>
                  <p className="text-muted-foreground text-sm">{tier.description}</p>
                </div>

                <ul className="space-y-3 mb-8">
                  {tier.features.map((feature, featureIndex) => (
                    <li key={featureIndex} className="flex items-center text-foreground">
                      <Check className="w-5 h-5 text-green-600 mr-3 flex-shrink-0" />
                      <span className="text-sm text-foreground">{feature}</span>
                    </li>
                  ))}
                </ul>

                <button
                  onClick={async () => {
                    if (tier.name === 'Enterprise') {
                      // Navigate to contact or demo page
                      navigate('/onboarding-flow');
                      return;
                    }

                    if (!isAuthenticated) {
                      // User not logged in - save plan selection and go to signup
                      localStorage.setItem('fikiri-selected-plan', JSON.stringify({
                        tier: tier.name.toLowerCase(),
                        billingPeriod: billingPeriod === 'monthly' ? 'monthly' : 'annual',
                        price: tier.price,
                        period: tier.period
                      }));
                      addToast({
                        type: 'info',
                        title: 'Sign up to continue',
                        message: `We'll set up your ${tier.name} plan after you create your account.`
                      });
                      navigate('/signup?plan=' + tier.name.toLowerCase());
                      return;
                    }

                    // User is authenticated - proceed to checkout
                    await handleCheckout(tier.name.toLowerCase());
                  }}
                  disabled={loadingTier === tier.name}
                  className={`w-full py-3 px-6 rounded-lg font-semibold transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 ${tier.buttonStyle}`}
                >
                  {loadingTier === tier.name ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Processing...</span>
                    </>
                  ) : (
                    <>
                      <CreditCard className="w-4 h-4" />
                      <span>{tier.cta}</span>
                    </>
                  )}
                </button>
              </motion.div>
            ))}
          </div>
        </Container>
      </section>

      {/* Industry-Specific Pricing */}
      <section ref={industriesRef} className="relative py-20 bg-muted/50">
        <Container>
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={industriesInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl sm:text-4xl font-bold mb-4 text-foreground">
              Industry-Specific Solutions
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
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
                className="bg-card rounded-xl p-6 border border-border shadow-sm hover:border-brand-primary/30 transition-all duration-300"
              >
                <div className="text-center mb-4">
                  <div className="text-4xl mb-2">{industry.icon}</div>
                  <h3 className="text-xl font-semibold text-foreground">{industry.name}</h3>
                  <div className="flex items-center justify-center gap-2 mt-2">
                    <span className="text-brand-primary font-medium">{industry.tier}</span>
                    <span className="text-foreground font-bold">${industry.price}{billingPeriod === 'monthly' ? '/mo' : '/yr'}</span>
                  </div>
                </div>

                <ul className="space-y-2">
                  {industry.features.map((feature, featureIndex) => (
                    <li key={featureIndex} className="flex items-center text-foreground text-sm">
                      <Check className="w-4 h-4 text-green-600 mr-2 flex-shrink-0" />
                      {feature}
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => navigate('/industry')}
                  className="w-full mt-4 py-2 px-4 bg-brand-primary hover:bg-fikiri-400 text-white font-medium rounded-lg transition-all duration-300"
                >
                  Try {industry.name} AI
                </button>
              </motion.div>
            ))}
          </div>
        </Container>
      </section>

      {/* Feature Comparison */}
      <section ref={featuresRef} className="relative py-20">
        <Container>
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={featuresInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl sm:text-4xl font-bold mb-4 text-foreground">
              Compare Plans
            </h2>
          </motion.div>

          <div className="bg-card rounded-2xl border border-border shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left p-6 text-foreground font-semibold">Features</th>
                    <th className="text-center p-6 text-foreground font-semibold">Starter</th>
                    <th className="text-center p-6 text-foreground font-semibold">Growth</th>
                    <th className="text-center p-6 text-foreground font-semibold">Business</th>
                    <th className="text-center p-6 text-foreground font-semibold">Enterprise</th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonFeatures.map((category) => (
                    <React.Fragment key={category.category}>
                      <tr className="border-b border-border">
                        <td colSpan={5} className="p-4 text-brand-primary font-semibold text-sm uppercase tracking-wider">
                          {category.category}
                        </td>
                      </tr>
                      {category.features.map((feature, featureIndex) => (
                        <tr key={featureIndex} className="border-b border-border/50">
                          <td className="p-4 text-foreground">{feature.name}</td>
                          <td className="p-4 text-center text-foreground">
                            {typeof feature.starter === 'boolean' 
                              ? (feature.starter ? <Check className="w-5 h-5 text-green-600 mx-auto" /> : '—')
                              : feature.starter
                            }
                          </td>
                          <td className="p-4 text-center text-foreground">
                            {typeof feature.growth === 'boolean' 
                              ? (feature.growth ? <Check className="w-5 h-5 text-green-600 mx-auto" /> : '—')
                              : feature.growth
                            }
                          </td>
                          <td className="p-4 text-center text-foreground">
                            {typeof feature.business === 'boolean' 
                              ? (feature.business ? <Check className="w-5 h-5 text-green-600 mx-auto" /> : '—')
                              : feature.business
                            }
                          </td>
                          <td className="p-4 text-center text-foreground">
                            {typeof feature.enterprise === 'boolean' 
                              ? (feature.enterprise ? <Check className="w-5 h-5 text-green-600 mx-auto" /> : '—')
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
        </Container>
      </section>

      {/* FAQ Section */}
      <section className="relative py-20 bg-muted/50">
        <Container>
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-16">
              <h2 className="text-3xl sm:text-4xl font-bold mb-4 text-foreground">
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
                <div key={index} className="bg-card rounded-xl p-6 border border-border shadow-sm">
                  <h3 className="text-lg font-semibold text-foreground mb-3">{faq.question}</h3>
                  <p className="text-muted-foreground">{faq.answer}</p>
                </div>
              ))}
            </div>
          </div>
        </Container>
      </section>

      {/* CTA Section - Radiant-style gradient strip */}
      <section className="relative py-20">
        <Gradient className="absolute inset-0 opacity-20" />
        <Container className="relative">
          <div className="max-w-4xl mx-auto text-center">
            <h2 className="text-3xl sm:text-4xl font-bold mb-6 text-foreground">
              Ready to start automating?
            </h2>
            <p className="text-xl text-muted-foreground mb-8">
              Get started with a free trial. No credit card required.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button
                onClick={() => navigate('/signup')}
                className="px-8 py-4 bg-brand-primary hover:bg-fikiri-400 text-white font-semibold rounded-full transition-all duration-300 flex items-center justify-center gap-2 shadow-md"
              >
                Start Free Trial
                <ArrowRight className="w-5 h-5" />
              </button>
              <button
                onClick={() => navigate('/onboarding-flow')}
                className="px-8 py-4 border border-border text-foreground font-semibold rounded-full hover:bg-muted transition-all duration-300"
              >
                Schedule Demo
              </button>
            </div>
          </div>
        </Container>
      </section>
    </div>
    </RadiantLayout>
  );
};

export default PricingPage;
