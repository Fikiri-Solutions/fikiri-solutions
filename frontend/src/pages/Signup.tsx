import React, { useState, useEffect } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { Link, useNavigate } from 'react-router-dom';
import { 
  Mail, 
  Lock, 
  User, 
  Building, 
  Eye, 
  EyeOff, 
  ArrowRight, 
  Chrome, 
  Github,
  UserPlus,
  CheckCircle,
  AlertCircle
} from 'lucide-react';
import { RadiantLayout } from '../components/radiant';
import { useAuth } from '../contexts/AuthContext';
import { useUserActivityTracking } from '../contexts/ActivityContext';
import { SMS_CONSENT } from '../constants/smsConsent';
import { AUTOCOMPLETE } from '../constants/autocomplete';

const Signup: React.FC = () => {
  const reduceMotion = useReducedMotion();
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    company: '',
    password: '',
    confirmPassword: '',
    agreeToTerms: false,
    subscribeNewsletter: false,
    phone: '',
    smsConsent: false,
  });
  
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  
  const { signup } = useAuth();
  const { trackSignup } = useUserActivityTracking();
  const navigate = useNavigate();

  // Load onboarding data if available
  useEffect(() => {
    const onboardingData = localStorage.getItem('fikiri-onboarding-data');
    if (onboardingData) {
      try {
        const data = JSON.parse(onboardingData);
        setFormData(prev => ({
          ...prev,
          email: data.businessEmail || prev.email,
          company: data.businessName || prev.company
        }));
        // Clear the onboarding data after using it
        localStorage.removeItem('fikiri-onboarding-data');
      } catch (error) {
        console.error('Error parsing onboarding data:', error);
      }
    }
  }, []);

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.firstName.trim()) {
      newErrors.firstName = 'First name is required';
    }

    if (!formData.lastName.trim()) {
      newErrors.lastName = 'Last name is required';
    }

    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'Email is invalid';
    }

    if (!formData.company.trim()) {
      newErrors.company = 'Company name is required';
    }

    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters';
    }

    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your password';
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    if (!formData.agreeToTerms) {
      newErrors.agreeToTerms = 'You must agree to the terms and conditions';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
    
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsLoading(true);
    setErrors({});
    
    try {
      // Create account using auth context
      const result = await signup(
        formData.email,
        formData.password,
        `${formData.firstName} ${formData.lastName}`,
        {
          businessName: formData.company.trim(),
          businessEmail: formData.email.trim(),
          termsAccepted: formData.agreeToTerms,
          privacyConsent: formData.agreeToTerms,
          marketingConsent: formData.subscribeNewsletter,
          phone: formData.phone.trim(),
          smsConsent: formData.smsConsent === true,
        },
      );
      
      if (result.success) {
        // Track successful signup
        trackSignup(formData.email, 'email');
        
        // Check if user selected a plan before signing up
        const selectedPlan = localStorage.getItem('fikiri-selected-plan');
        if (selectedPlan) {
          try {
            const plan = JSON.parse(selectedPlan);
            localStorage.removeItem('fikiri-selected-plan');
            
            // Redirect to pricing page with plan pre-selected and auto-checkout enabled
            navigate(`/pricing?plan=${plan.tier}&billing=${plan.billingPeriod}&autoCheckout=true`);
            return;
          } catch (e) {
            console.error('Error parsing selected plan:', e);
          }
        }
        
        navigate(result.redirectPath ?? '/onboarding');
      } else {
        setErrors({ submit: result.error || 'Failed to create account. Please try again.' });
      }
    } catch (error) {
      setErrors({ submit: 'Failed to create account. Please try again.' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <RadiantLayout showFooterCta={false} backdropIntensity="subtle">
    <div 
      id="main-content"
      className="relative overflow-x-clip"
    >
      {/* Static ambient wash — calm for auth focus */}
      <div className="absolute inset-0 pointer-events-none" aria-hidden>
        <div className="absolute -left-16 top-10 h-56 w-56 rounded-full bg-brand-accent/12 blur-3xl sm:h-72 sm:w-72" />
        <div className="absolute -right-20 top-40 h-64 w-64 rounded-full bg-brand-secondary/12 blur-3xl sm:h-96 sm:w-96" />
        <div className="absolute bottom-20 left-1/3 h-48 w-48 rounded-full bg-brand-primary/12 blur-3xl sm:h-64 sm:w-64" />
      </div>

      {/* Main Content */}
      <div className="relative z-10 flex items-start justify-center px-4 pb-10 pt-4 sm:items-center sm:px-6 sm:pb-16 sm:pt-8 lg:px-8">
        <motion.div
          className="max-w-md w-full min-w-0"
          initial={reduceMotion ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.45, ease: 'easeOut' }}
        >
          {/* Branding — nav already has logo */}
          <div className="mb-5 text-center sm:mb-6">
            <h1 className="mb-1 text-3xl font-bold text-white font-serif tracking-tight sm:text-4xl">
              Join Fikiri
            </h1>
            <p className="text-base text-white/85 sm:text-lg">
              Create your account
            </p>
          </div>

          {/* Signup Form — dark panel for contrast on marketing wash */}
          <div className="rounded-3xl border border-white/20 bg-black/45 p-5 shadow-2xl backdrop-blur-sm sm:p-8 sm:backdrop-blur-md">
            <div className="mb-6">
              <h2 className="text-xl font-bold text-white text-center mb-2 font-serif sm:text-2xl">
                Create Your Account
              </h2>
              <p className="text-white/80 text-center text-sm">
                Get started with Fikiri Solutions today
              </p>
            </div>
            
            <form className="space-y-6" onSubmit={handleSubmit} autoComplete="on">
              {errors.submit && (
                <div className="bg-red-500/20 border border-red-500/50 rounded-xl p-4 backdrop-blur-sm">
                  <div className="flex items-center">
                    <AlertCircle className="h-5 w-5 text-red-300 mr-2" />
                    <p className="text-sm text-red-200">{errors.submit}</p>
                  </div>
                </div>
              )}
              
              {/* Name Fields */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="firstName" className="block text-sm font-medium text-white/90 mb-2">
                    First Name
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                      <User className="h-5 w-5 text-gray-500" />
                    </div>
                    <input
                      id="firstName"
                      name="firstName"
                      type="text"
                      autoComplete={AUTOCOMPLETE.signup.givenName}
                      required
                      className={`w-full pl-12 pr-4 py-3 bg-white border border-gray-300 rounded-xl text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-all duration-200 ${errors.firstName ? 'border-red-500 focus:ring-red-500' : ''}`}
                      placeholder="John"
                      value={formData.firstName}
                      onChange={handleInputChange}
                    />
                  </div>
                  {errors.firstName && (
                    <p className="mt-2 text-sm text-red-300">{errors.firstName}</p>
                  )}
                </div>
                
                <div>
                  <label htmlFor="lastName" className="block text-sm font-medium text-white/90 mb-2">
                    Last Name
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                      <User className="h-5 w-5 text-gray-500" />
                    </div>
                    <input
                      id="lastName"
                      name="lastName"
                      type="text"
                      autoComplete={AUTOCOMPLETE.signup.familyName}
                      required
                      className={`w-full pl-12 pr-4 py-3 bg-white border border-gray-300 rounded-xl text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-all duration-200 ${errors.lastName ? 'border-red-500 focus:ring-red-500' : ''}`}
                      placeholder="Doe"
                      value={formData.lastName}
                      onChange={handleInputChange}
                    />
                  </div>
                  {errors.lastName && (
                    <p className="mt-2 text-sm text-red-300">{errors.lastName}</p>
                  )}
                </div>
              </div>
              
              {/* Email Field */}
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-white/90 mb-2">
                  Email Address
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <Mail className="h-5 w-5 text-gray-500" />
                  </div>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete={AUTOCOMPLETE.signup.email}
                    required
                    className={`w-full pl-12 pr-4 py-3 bg-white border border-gray-300 rounded-xl text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-all duration-200 ${errors.email ? 'border-red-500 focus:ring-red-500' : ''}`}
                    placeholder="john@company.com"
                    value={formData.email}
                    onChange={handleInputChange}
                  />
                </div>
                {errors.email && (
                  <p className="mt-2 text-sm text-red-300">{errors.email}</p>
                )}
              </div>
              
              {/* Company Field */}
              <div>
                <label htmlFor="company" className="block text-sm font-medium text-white/90 mb-2">
                  Company Name
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <Building className="h-5 w-5 text-gray-500" />
                  </div>
                  <input
                    id="company"
                    name="company"
                    type="text"
                    autoComplete={AUTOCOMPLETE.signup.organization}
                    required
                    className={`w-full pl-12 pr-4 py-3 bg-white border border-gray-300 rounded-xl text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-all duration-200 ${errors.company ? 'border-red-500 focus:ring-red-500' : ''}`}
                    placeholder="Your Company"
                    value={formData.company}
                    onChange={handleInputChange}
                  />
                </div>
                {errors.company && (
                  <p className="mt-2 text-sm text-red-300">{errors.company}</p>
                )}
              </div>

              {/* Optional Phone + SMS Consent (CTIA/TCPA express consent — checkbox unchecked by default) */}
              <div className="rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-800/50 p-4">
                <p className="text-sm font-medium text-gray-800 dark:text-gray-200 mb-2">{SMS_CONSENT.sectionTitle}</p>
                <p className="text-xs text-gray-600 dark:text-gray-400 mb-3">
                  {SMS_CONSENT.upfrontDisclosure}
                </p>
                <label htmlFor="phone" className="block text-sm font-medium text-white/90 mb-2">
                  Mobile number <span className="text-white/55 font-normal">(optional)</span>
                </label>
                <div className="relative">
                  <input
                    id="phone"
                    name="phone"
                    type="tel"
                    autoComplete={AUTOCOMPLETE.signup.tel}
                    className="w-full pl-4 pr-4 py-3 bg-white border border-gray-300 rounded-xl text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-all duration-200"
                    placeholder="+1 (555) 123-4567"
                    value={formData.phone}
                    onChange={handleInputChange}
                  />
                </div>
                <div className="mt-3 flex items-start">
                  <div className="flex items-center h-5">
                    <input
                      id="smsConsent"
                      name="smsConsent"
                      type="checkbox"
                      autoComplete={AUTOCOMPLETE.off}
                      checked={formData.smsConsent}
                      onChange={handleInputChange}
                      className="w-4 h-4 text-brand-accent bg-white/10 border-white/20 rounded focus:ring-brand-accent focus:ring-2"
                    />
                  </div>
                  <label htmlFor="smsConsent" className="ml-3 text-sm text-gray-300">
                    {SMS_CONSENT.checkboxLabel}
                  </label>
                </div>
              </div>
              
              {/* Password Fields */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-white/90 mb-2">
                    Password
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                      <Lock className="h-5 w-5 text-gray-500" />
                    </div>
                    <input
                      id="password"
                      name="password"
                      type={showPassword ? "text" : "password"}
                      autoComplete={AUTOCOMPLETE.signup.newPassword}
                      required
                      className={`w-full pl-12 pr-12 py-3 bg-white border border-gray-300 rounded-xl text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-all duration-200 ${errors.password ? 'border-red-500 focus:ring-red-500' : ''}`}
                      placeholder="••••••••"
                      value={formData.password}
                      onChange={handleInputChange}
                    />
                    <button
                      type="button"
                      className="absolute inset-y-0 right-0 min-w-[44px] flex items-center justify-center pr-2 touch-manipulation"
                      onClick={() => setShowPassword(!showPassword)}
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? (
                        <EyeOff className="h-5 w-5 text-gray-500 hover:text-gray-700" />
                      ) : (
                        <Eye className="h-5 w-5 text-gray-500 hover:text-gray-700" />
                      )}
                    </button>
                  </div>
                  {errors.password && (
                    <p className="mt-2 text-sm text-red-300">{errors.password}</p>
                  )}
                </div>
                
                <div>
                  <label htmlFor="confirmPassword" className="block text-sm font-medium text-white/90 mb-2">
                    Confirm Password
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                      <Lock className="h-5 w-5 text-gray-500" />
                    </div>
                    <input
                      id="confirmPassword"
                      name="confirmPassword"
                      type={showConfirmPassword ? "text" : "password"}
                      autoComplete={AUTOCOMPLETE.signup.newPasswordConfirm}
                      required
                      className={`w-full pl-12 pr-12 py-3 bg-white border border-gray-300 rounded-xl text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-all duration-200 ${errors.confirmPassword ? 'border-red-500 focus:ring-red-500' : ''}`}
                      placeholder="••••••••"
                      value={formData.confirmPassword}
                      onChange={handleInputChange}
                    />
                    <button
                      type="button"
                      className="absolute inset-y-0 right-0 min-w-[44px] flex items-center justify-center pr-2 touch-manipulation"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                    >
                      {showConfirmPassword ? (
                        <EyeOff className="h-5 w-5 text-gray-500 hover:text-gray-700" />
                      ) : (
                        <Eye className="h-5 w-5 text-gray-500 hover:text-gray-700" />
                      )}
                    </button>
                  </div>
                  {errors.confirmPassword && (
                    <p className="mt-2 text-sm text-red-300">{errors.confirmPassword}</p>
                  )}
                </div>
              </div>
              
              {/* Checkboxes */}
              <div className="space-y-4">
                <div className="flex items-start">
                  <div className="flex items-center h-5">
                    <input
                      id="agreeToTerms"
                      name="agreeToTerms"
                      type="checkbox"
                      autoComplete={AUTOCOMPLETE.off}
                      className="w-4 h-4 text-brand-accent bg-white/10 border-white/20 rounded focus:ring-brand-accent focus:ring-2"
                      checked={formData.agreeToTerms}
                      onChange={handleInputChange}
                    />
                  </div>
                  <div className="ml-3 text-sm">
                    <label htmlFor="agreeToTerms" className="text-gray-300">
                      I agree to the{' '}
                      <Link to="/terms" className="text-brand-accent hover:text-brand-secondary underline">
                        Terms of Service
                      </Link>{' '}
                      and{' '}
                      <Link to="/privacy" className="text-brand-accent hover:text-brand-secondary underline">
                        Privacy Policy
                      </Link>
                    </label>
                    {errors.agreeToTerms && (
                      <p className="mt-1 text-sm text-red-300">{errors.agreeToTerms}</p>
                    )}
                  </div>
                </div>
                
                <div className="flex items-start">
                  <div className="flex items-center h-5">
                    <input
                      id="subscribeNewsletter"
                      name="subscribeNewsletter"
                      type="checkbox"
                      autoComplete={AUTOCOMPLETE.off}
                      className="w-4 h-4 text-brand-accent bg-white/10 border-white/20 rounded focus:ring-brand-accent focus:ring-2"
                      checked={formData.subscribeNewsletter}
                      onChange={handleInputChange}
                    />
                  </div>
                  <div className="ml-3 text-sm">
                    <label htmlFor="subscribeNewsletter" className="text-gray-300">
                      Subscribe to our newsletter for updates and tips
                    </label>
                  </div>
                </div>
              </div>
              
              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full min-h-[44px] touch-manipulation flex justify-center items-center gap-2 py-3 px-4 border border-transparent rounded-xl shadow-sm text-sm font-medium text-white bg-gradient-to-r from-brand-primary to-brand-secondary hover:from-brand-secondary hover:to-brand-primary focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-accent disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
              >
                {isLoading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Creating Account...
                  </>
                ) : (
                  <>
                    Create Account
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </button>
            </form>

            {/* Social Signup Options */}
            <div className="mt-6">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/20" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-transparent text-gray-300">Or sign up with</span>
                </div>
              </div>

              <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-3">
                <button
                  type="button"
                  disabled
                  title="Coming soon"
                  className="w-full min-h-[44px] touch-manipulation inline-flex items-center justify-center gap-2 py-3 px-3 sm:px-4 border border-white/10 rounded-xl bg-white/5 text-sm font-medium text-gray-400 cursor-not-allowed"
                >
                  <Chrome className="h-5 w-5 shrink-0" aria-hidden />
                  <span className="text-center leading-snug">Gmail (coming soon)</span>
                </button>

                <button
                  type="button"
                  disabled
                  title="Coming soon"
                  className="w-full min-h-[44px] touch-manipulation inline-flex items-center justify-center gap-2 py-3 px-3 sm:px-4 border border-white/10 rounded-xl bg-white/5 text-sm font-medium text-gray-400 cursor-not-allowed"
                >
                  <Github className="h-5 w-5 shrink-0" aria-hidden />
                  <span className="text-center leading-snug">GitHub (coming soon)</span>
                </button>
              </div>
            </div>

            {/* Sign In Link */}
            <div className="mt-6 text-center">
              <p className="text-sm text-gray-300">
                Already have an account?{' '}
                <Link 
                  to="/login" 
                  className="text-brand-accent hover:text-brand-secondary font-medium underline"
                >
                  Sign in here
                </Link>
              </p>
            </div>
          </div>

          {/* Features Preview */}
          <div className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="text-center">
              <div className="w-12 h-12 bg-brand-accent/20 rounded-xl flex items-center justify-center mx-auto mb-2">
                <CheckCircle className="h-6 w-6 text-brand-accent" />
              </div>
              <p className="text-xs text-gray-300">Free Trial</p>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 bg-brand-secondary/20 rounded-xl flex items-center justify-center mx-auto mb-2">
                <UserPlus className="h-6 w-6 text-brand-secondary" />
              </div>
              <p className="text-xs text-gray-300">Easy Setup</p>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 bg-brand-primary/20 rounded-xl flex items-center justify-center mx-auto mb-2">
                <ArrowRight className="h-6 w-6 text-brand-primary" />
              </div>
              <p className="text-xs text-gray-300">Quick Start</p>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
    </RadiantLayout>
  );
};

export { Signup };
