import React, { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useInView } from 'react-intersection-observer';
import { RadiantLayout, Gradient, Container, AnimatedBackground } from '../components/radiant';
import { PublicChatbotWidget } from '../components/PublicChatbotWidget';
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
            ? 'Card required for verification. You won\'t be charged during your 7-day trial.'
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

  const pricingTiers: PricingTier[] = [
    {
      name: 'Starter',
      price: billingPeriod === 'monthly' ? 49 : (49 * 12) - Math.round(49 * 12 * 0.10), // Exactly 10% discount
      period: billingPeriod === 'monthly' ? '/month' : '/year',
      description: 'For small businesses getting started with verified core automation',
      responses_limit: 200,
      features: [
        '200 AI responses per month',
        'Core email automation (verified actions)',
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
      price: billingPeriod === 'monthly' ? 99 : (99 * 12) - Math.round(99 * 12 * 0.10), // Exactly 10% discount
      period: billingPeriod === 'monthly' ? '/month' : '/year',
      description: 'For growing businesses that need higher limits and broader automation',
      responses_limit: 800,
      features: [
        '800 AI responses per month',
        'Advanced AI responses',
        'Advanced CRM features',
        '2,000 emails/month',
        'Priority email support',
        'Advanced analytics',
        'Basic integrations',
        'Workflow automation (includes partial actions)'
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
      description: 'For established businesses needing comprehensive workflows and support',
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
      price: billingPeriod === 'monthly' ? 499 : (499 * 12) - Math.round(499 * 12 * 0.10), // Exactly 10% discount
      period: billingPeriod === 'monthly' ? '/month' : '/year',
      description: 'For large organizations with custom requirements and governance',
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

  const comparisonFeatures = [
    {
      category: 'Core Features',
      features: [
        { name: 'AI Responses per month', starter: '200', growth: '800', business: '4,000', enterprise: 'Unlimited' },
        { name: 'Core email automation', starter: true, growth: true, business: true, enterprise: true },
        { name: 'Email limit per month', starter: '500', growth: '2,000', business: '10,000', enterprise: 'Unlimited' },
        { name: 'CRM integration', starter: 'Basic', growth: 'Advanced', business: 'Advanced', enterprise: 'Custom' },
        { name: 'Analytics', starter: 'Basic', growth: 'Advanced', business: 'Advanced', enterprise: 'Custom' },
        { name: 'Integrations', starter: 'Optional add-ons', growth: 'Optional add-ons', business: 'Custom', enterprise: 'Custom' }
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
      <div className="min-h-screen bg-background text-foreground overflow-hidden relative">
        <div className="absolute inset-0 fikiri-gradient-animated pointer-events-none">
          <AnimatedBackground />
        </div>
        <div className="relative z-10">
      {/* Hero Section */}
      <section ref={heroRef} className="relative py-16 sm:py-20 z-10">
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
              <p className="text-sm text-muted-foreground mb-4">
                Verified now: core CRM, lead capture, and core automation actions. Optional integrations: Gmail, Outlook, Twilio, Slack, Stripe.
                Some advanced automation actions are marked partial or coming soon.
              </p>
              <p className="text-sm text-muted-foreground mb-8">
                {purchaseType === 'trial' ? (
                  <span className="inline-flex items-center gap-2">
                    <CreditCard className="w-4 h-4" />
                    Card required for free trial verification. No charge during your 7-day trial.
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
              <div className="bg-card/90 backdrop-blur-sm rounded-lg p-1 border border-border shadow-sm">
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

              <div className="bg-card/90 backdrop-blur-sm rounded-lg p-1 border border-border shadow-sm">
                <button
                  onClick={() => setPurchaseType('trial')}
                  className={`px-6 py-2 rounded-md font-medium transition-all duration-300 ${
                    purchaseType === 'trial'
                      ? 'bg-brand-primary text-white'
                      : 'text-foreground hover:bg-muted'
                  }`}
                >
                  <span>Free Trial</span>
                  <span className="ml-2 text-xs bg-brand-primary/90 text-white px-2 py-1 rounded-full">7 days</span>
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
      <section ref={pricingRef} className="relative py-20 z-10">
        <Gradient className="absolute inset-x-2 top-24 bottom-0 rounded-3xl ring-1 ring-black/5 ring-inset opacity-30" />
        <Container className="relative">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {pricingTiers.map((tier, index) => (
              <motion.div
                key={tier.name}
                initial={{ opacity: 0, y: 30 }}
                animate={pricingInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                className={`relative bg-card/90 backdrop-blur-sm rounded-2xl p-8 border border-border shadow-lg ring-1 ring-black/5 transition-all duration-300 hover:shadow-xl ${
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
                      navigate('/signup');
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

      {/* Feature Comparison */}
      <section ref={featuresRef} className="relative py-20 z-10">
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

          <div className="bg-card/90 backdrop-blur-sm rounded-2xl border border-border shadow-sm overflow-hidden">
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

      <section className="relative py-10 z-10 border-t border-border/60">
        <Container>
          <p className="text-center text-muted-foreground text-sm sm:text-base">
            Questions about plans or trials?{' '}
            <Link to="/faq" className="font-medium text-brand-primary hover:text-brand-secondary underline-offset-4 hover:underline">
              Read the FAQ
            </Link>
            .
          </p>
        </Container>
      </section>

      {/* CTA Section - Radiant-style gradient strip */}
      <section className="relative py-20 z-10">
        <Gradient className="absolute inset-0 opacity-20" />
        <Container className="relative">
          <div className="max-w-4xl mx-auto text-center">
            <h2 className="text-3xl sm:text-4xl font-bold mb-6 text-foreground">
              Ready to start automating?
            </h2>
            <p className="text-xl text-muted-foreground mb-8">
              Get started with a 7-day free trial. No credit card required.
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
                onClick={() => navigate('/signup')}
                className="px-8 py-4 border border-border text-foreground font-semibold rounded-full hover:bg-muted transition-all duration-300"
              >
                Schedule Demo
              </button>
            </div>
          </div>
        </Container>
      </section>
        </div>
      </div>
      <PublicChatbotWidget />
    </RadiantLayout>
  );
};

export default PricingPage;
