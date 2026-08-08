import React, { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { RadiantLayout, Gradient, Container, Reveal } from '../components/radiant';
import { MarketingChatWidget } from '../components/MarketingChatWidget';
import { TableScroll } from '../components/TableScroll';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '../services/apiClient';
import { useToast } from '../components/Toast';
import { 
  Check, 
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
      <div className="relative min-h-dvh overflow-hidden pb-[env(safe-area-inset-bottom)]">
        <div className="relative z-10">
      {/* Hero Section */}
      <section className="relative z-10 py-8 sm:py-12">
        <Container>
          <div className="max-w-4xl mx-auto text-center">
            <Reveal direction="up">
              <h1 className="text-3xl font-bold mb-4 text-white sm:text-4xl md:text-5xl lg:text-6xl">
                Plans for businesses of any size
              </h1>
              <p className="text-base sm:text-xl text-white/85 mb-3">
                Get all the Fikiri Solutions features — pay for what you use
              </p>
              <p className="text-sm text-white/75 mb-4 leading-relaxed">
                Verified now: core CRM, lead capture, and core automation actions. Optional integrations: Gmail, Outlook, Twilio, Slack, Stripe.
                Some advanced automation actions are marked partial or coming soon.
              </p>
              <p className="text-sm text-white/75 mb-8 px-1 sm:px-0">
                {purchaseType === 'trial' ? (
                  <span className="inline-flex max-w-full flex-wrap items-center justify-center gap-2 text-center">
                    <CreditCard className="h-4 w-4 shrink-0" aria-hidden />
                    <span>Card required for free trial verification. No charge during your 7-day trial.</span>
                  </span>
                ) : (
                  <span className="inline-flex max-w-full flex-wrap items-center justify-center gap-2 text-center">
                    <CreditCard className="h-4 w-4 shrink-0" aria-hidden />
                    <span>Start using all features immediately. Charged today.</span>
                  </span>
                )}
              </p>
            </Reveal>

            {/* Billing Toggle */}
            <Reveal direction="up" delay={0.12} className="flex flex-col items-center justify-center mb-8 gap-4">
              <div className="bg-white/90 backdrop-blur-sm rounded-lg p-1 border border-white/20 shadow-sm flex flex-col sm:flex-row w-full sm:w-auto">
                <button
                  onClick={() => setBillingPeriod('monthly')}
                  className={`min-h-[44px] px-4 sm:px-6 py-2.5 rounded-md font-medium touch-manipulation transition-all duration-300 ${
                    billingPeriod === 'monthly'
                      ? 'bg-brand-primary text-white'
                      : 'text-stone-800 hover:bg-stone-100'
                  }`}
                >
                  Monthly
                </button>
                <button
                  onClick={() => setBillingPeriod('yearly')}
                  className={`min-h-[44px] px-4 sm:px-6 py-2.5 rounded-md font-medium touch-manipulation transition-all duration-300 ${
                    billingPeriod === 'yearly'
                      ? 'bg-brand-primary text-white'
                      : 'text-stone-800 hover:bg-stone-100'
                  }`}
                >
                  <span>Yearly</span>
                  <span className="ml-2 text-xs bg-green-600 text-white px-2 py-1 rounded-full">Save 10%</span>
                </button>
              </div>

              <div className="bg-white/90 backdrop-blur-sm rounded-lg p-1 border border-white/20 shadow-sm flex flex-col sm:flex-row w-full sm:w-auto">
                <button
                  onClick={() => setPurchaseType('trial')}
                  className={`min-h-[44px] px-4 sm:px-6 py-2.5 rounded-md font-medium touch-manipulation transition-all duration-300 ${
                    purchaseType === 'trial'
                      ? 'bg-brand-primary text-white'
                      : 'text-stone-800 hover:bg-stone-100'
                  }`}
                >
                  <span>Free Trial</span>
                  <span className="ml-2 text-xs bg-brand-primary/90 text-white px-2 py-1 rounded-full">7 days</span>
                </button>
                <button
                  onClick={() => setPurchaseType('immediate')}
                  className={`min-h-[44px] px-4 sm:px-6 py-2.5 rounded-md font-medium touch-manipulation transition-all duration-300 ${
                    purchaseType === 'immediate'
                      ? 'bg-brand-primary text-white'
                      : 'text-stone-800 hover:bg-stone-100'
                  }`}
                >
                  Start Now
                </button>
              </div>
            </Reveal>
          </div>
        </Container>
      </section>

      {/* Pricing Cards - Radiant-style gradient behind */}
      <section className="relative py-14 sm:py-20 z-10 overflow-x-hidden">
        <Gradient className="absolute inset-x-2 top-24 bottom-0 rounded-3xl ring-1 ring-black/5 ring-inset opacity-30" />
        <Container className="relative">
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4 md:gap-8">
            {pricingTiers.map((tier, index) => (
              <Reveal
                key={tier.name}
                direction="up"
                delay={index * 0.1}
                className={`relative min-w-0 bg-white/[0.95] backdrop-blur-sm rounded-2xl p-6 sm:p-8 border border-white/30 shadow-lg shadow-orange-950/25 ring-1 ring-white/15 transition-all duration-300 hover:shadow-xl ${
                  tier.highlighted
                    ? 'ring-2 ring-brand-primary/50'
                    : 'hover:border-brand-primary/40'
                }`}
              >
                {tier.popular && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                    <div className="bg-brand-primary text-white px-4 py-2 rounded-full text-sm font-semibold flex items-center gap-2 shadow-md">
                      <Star className="w-4 h-4" />
                      Most Popular
                    </div>
                  </div>
                )}

                <div className="text-center mb-8">
                  <h3 className="text-2xl font-bold text-stone-900 mb-2">{tier.name}</h3>
                  <div className="flex items-center justify-center mb-4">
                    <span className="text-4xl font-bold text-stone-900">${tier.price}</span>
                    <span className="text-stone-600 ml-2 font-medium">{tier.period}</span>
                  </div>
                  <p className="text-stone-700 text-sm leading-relaxed">{tier.description}</p>
                </div>

                <ul className="space-y-3 mb-8 min-w-0">
                  {tier.features.map((feature, featureIndex) => (
                    <li key={featureIndex} className="flex items-center text-stone-800 min-w-0">
                      <Check className="w-5 h-5 text-green-700 mr-3 flex-shrink-0" aria-hidden />
                      <span className="text-sm text-stone-800 break-words">{feature}</span>
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
                  className={`w-full min-h-[44px] touch-manipulation py-3 px-6 rounded-lg font-semibold transition-all duration-300 sm:transform sm:hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 ${tier.buttonStyle}`}
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
              </Reveal>
            ))}
          </div>
        </Container>
      </section>

      {/* Consultation & Implementation Services */}
      <section className="relative py-14 sm:py-20 z-10 overflow-x-hidden">
        <Container>
          <Reveal direction="up" className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4 text-white">
              Consultation & Implementation
            </h2>
            <p className="text-lg text-white/80 max-w-3xl mx-auto">
              Subscription gives you platform access. Consultation covers hands-on setup so your CRM, inbox, and
              automation work reliably for your team.
            </p>
          </Reveal>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <Reveal direction="left" delay={0.08} className="bg-white/[0.95] backdrop-blur-sm rounded-2xl p-6 border border-white/30 shadow-sm shadow-orange-950/15">
              <h3 className="text-xl font-semibold text-stone-900 mb-3">Workflow Diagnostic</h3>
              <p className="text-stone-700 text-sm mb-4">
                We review one part of your business from start to finish and show where time is being lost.
              </p>
              <ul className="space-y-2 text-sm text-stone-800">
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-green-700" aria-hidden />
                  Simple map of how work happens now vs. how it should work
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-green-700" aria-hidden />
                  Clear checklist of what can be automated now (and what should wait)
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-green-700" aria-hidden />
                  Realistic estimate of time and cost savings
                </li>
              </ul>
            </Reveal>

            <Reveal direction="up" delay={0.16} className="bg-white/[0.95] backdrop-blur-sm rounded-2xl p-6 border border-white/30 shadow-sm shadow-orange-950/15">
              <h3 className="text-xl font-semibold text-stone-900 mb-3">Foundations Sprint</h3>
              <p className="text-stone-700 text-sm mb-4">
                We clean up your CRM and inbox so automation works reliably.
              </p>
              <ul className="space-y-2 text-sm text-stone-800">
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-green-700" aria-hidden />
                  Clear rules for who owns each lead and next step
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-green-700" aria-hidden />
                  Better email routing and response templates
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-green-700" aria-hidden />
                  3-5 simple numbers to track progress
                </li>
              </ul>
            </Reveal>

            <Reveal direction="right" delay={0.24} className="bg-white/[0.95] backdrop-blur-sm rounded-2xl p-6 border border-white/30 shadow-sm shadow-orange-950/15">
              <h3 className="text-xl font-semibold text-stone-900 mb-3">Automation Build Sprint</h3>
              <p className="text-stone-700 text-sm mb-4">
                We build one automation from start to finish, train your team, and support rollout.
              </p>
              <ul className="space-y-2 text-sm text-stone-800">
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-green-700" aria-hidden />
                  End-to-end automation delivery
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-green-700" aria-hidden />
                  Live testing with your real scenarios
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-green-700" aria-hidden />
                  30 days of in-scope fixes after launch
                </li>
              </ul>
            </Reveal>
          </div>

          <Reveal direction="up" delay={0.1} className="mt-8 bg-orange-50 border border-orange-200 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-orange-950">Not sure where to start?</p>
              <p className="text-sm text-orange-900">
                Book a consultation and we will tell you if a diagnostic is the right next step.
              </p>
            </div>
            <button
              onClick={() => navigate('/contact')}
              className="px-4 py-2 bg-brand-primary hover:bg-fikiri-400 text-white font-medium rounded-lg transition-all duration-300"
            >
              Book Consultation
            </button>
          </Reveal>
        </Container>
      </section>

      {/* Feature Comparison */}
      <section className="relative py-14 sm:py-20 z-10">
        <Container>
          <Reveal direction="up" className="text-center mb-8 sm:mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4 text-white">
              Compare Plans
            </h2>
            <p className="text-sm text-white/75 sm:hidden">
              Swipe horizontally to compare all plans
            </p>
          </Reveal>

          <Reveal direction="up" delay={0.1} className="bg-white/[0.95] backdrop-blur-sm rounded-2xl border border-white/30 shadow-sm shadow-orange-950/15 overflow-hidden">
            <TableScroll size="wide" label="Compare plans table">
              <table className="w-full table-fixed sm:table-auto">
                <thead>
                  <tr className="border-b border-stone-200">
                    <th className="text-left p-4 sm:p-6 text-stone-900 font-semibold whitespace-nowrap w-[38%] sm:w-auto">Features</th>
                    <th className="text-center p-4 sm:p-6 text-stone-900 font-semibold whitespace-nowrap">Starter</th>
                    <th className="text-center p-4 sm:p-6 text-stone-900 font-semibold whitespace-nowrap">Growth</th>
                    <th className="text-center p-4 sm:p-6 text-stone-900 font-semibold whitespace-nowrap">Business</th>
                    <th className="text-center p-4 sm:p-6 text-stone-900 font-semibold whitespace-nowrap">Enterprise</th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonFeatures.map((category) => (
                    <React.Fragment key={category.category}>
                      <tr className="border-b border-stone-200">
                        <td colSpan={5} className="p-4 text-orange-800 font-semibold text-sm uppercase tracking-wider">
                          {category.category}
                        </td>
                      </tr>
                      {category.features.map((feature, featureIndex) => (
                        <tr key={featureIndex} className="border-b border-stone-100">
                          <td className="table-scroll-cell-wrap p-4 text-stone-800 min-w-[8rem]">{feature.name}</td>
                          <td className="p-4 text-center text-stone-700">
                            {typeof feature.starter === 'boolean' 
                              ? (feature.starter ? <Check className="w-5 h-5 text-green-700 mx-auto" aria-label="Included" /> : <span className="text-stone-400" aria-label="Not included">—</span>)
                              : feature.starter
                            }
                          </td>
                          <td className="p-4 text-center text-stone-700">
                            {typeof feature.growth === 'boolean' 
                              ? (feature.growth ? <Check className="w-5 h-5 text-green-700 mx-auto" aria-label="Included" /> : <span className="text-stone-400" aria-label="Not included">—</span>)
                              : feature.growth
                            }
                          </td>
                          <td className="p-4 text-center text-stone-700">
                            {typeof feature.business === 'boolean' 
                              ? (feature.business ? <Check className="w-5 h-5 text-green-700 mx-auto" aria-label="Included" /> : <span className="text-stone-400" aria-label="Not included">—</span>)
                              : feature.business
                            }
                          </td>
                          <td className="p-4 text-center text-stone-700">
                            {typeof feature.enterprise === 'boolean' 
                              ? (feature.enterprise ? <Check className="w-5 h-5 text-green-700 mx-auto" aria-label="Included" /> : <span className="text-stone-400" aria-label="Not included">—</span>)
                              : feature.enterprise
                            }
                          </td>
                        </tr>
                      ))}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </TableScroll>
          </Reveal>
        </Container>
      </section>

      <section className="relative py-10 z-10 border-t border-white/10">
        <Container>
          <Reveal direction="up">
          <p className="text-center text-white/80 text-sm sm:text-base">
            Questions about plans or trials?{' '}
            <Link to="/faq" className="font-medium text-orange-300 hover:text-orange-200 underline-offset-4 hover:underline">
              Read the FAQ
            </Link>
            .
          </p>
          </Reveal>
        </Container>
      </section>
        </div>
      </div>
      <MarketingChatWidget />
    </RadiantLayout>
  );
};

export default PricingPage;
