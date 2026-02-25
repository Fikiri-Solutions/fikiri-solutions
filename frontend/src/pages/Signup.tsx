import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
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
import { FikiriLogo } from '../components/FikiriLogo';
import { RadiantLayout } from '../components/radiant';
import { useAuth } from '../contexts/AuthContext';
import { useUserActivityTracking } from '../contexts/ActivityContext';

const Signup: React.FC = () => {
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
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  
  const { signup, getRedirectPath, user } = useAuth();
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

  const handleMouseMove = (e: React.MouseEvent) => {
    setMousePosition({
      x: (e.clientX / window.innerWidth) * 100,
      y: (e.clientY / window.innerHeight) * 100,
    });
  };

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
        `${formData.firstName} ${formData.lastName}`
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
        
        // Get the appropriate redirect path based on user state
        const redirectPath = getRedirectPath();
        navigate(redirectPath);
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
    <RadiantLayout>
    <div 
      id="main-content"
      className="min-h-screen bg-brand-tan dark:bg-gray-900 relative overflow-hidden"
      onMouseMove={handleMouseMove}
    >
      {/* Animated Background */}
      <div className="absolute inset-0">
        {/* Floating orbs with brand colors */}
        <motion.div 
          className="absolute w-72 h-72 bg-brand-accent/20 rounded-full blur-3xl"
          animate={{
            x: mousePosition.x * 0.1,
            y: mousePosition.y * 0.1,
            scale: [1, 1.1, 1],
          }}
          transition={{
            duration: 4,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        <motion.div 
          className="absolute w-96 h-96 bg-brand-secondary/20 rounded-full blur-3xl"
          animate={{
            x: mousePosition.x * 0.05,
            y: mousePosition.y * 0.05,
            scale: [1.1, 1, 1.1],
          }}
          transition={{
            duration: 6,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        <motion.div 
          className="absolute w-64 h-64 bg-brand-primary/20 rounded-full blur-3xl"
          animate={{
            x: mousePosition.x * 0.08,
            y: mousePosition.y * 0.1,
            scale: [1, 1.2, 1],
          }}
          transition={{
            duration: 5,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        
        {/* Geometric shapes */}
        <motion.div
          className="absolute top-20 left-20 w-32 h-32 border-2 border-white/10 rounded-lg"
          animate={{
            rotate: [0, 90, 180, 270, 360],
            scale: [1, 1.1, 1],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: "linear"
          }}
        />
        <motion.div
          className="absolute bottom-32 right-32 w-24 h-24 bg-brand-accent/10 rounded-full"
          animate={{
            y: [-20, 20, -20],
            x: [-10, 10, -10],
          }}
          transition={{
            duration: 7,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        <motion.div
          className="absolute top-1/2 right-20 w-16 h-16 border-2 border-brand-secondary/20 rounded-full"
          animate={{
            rotate: [0, 180, 360],
            scale: [1, 1.2, 1],
          }}
          transition={{
            duration: 6,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        
        {/* Grid pattern */}
        <div className="absolute inset-0 opacity-20" style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.1'%3E%3Ccircle cx='30' cy='30' r='1'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`
        }} />
        
        {/* Floating particles */}
        {[...Array(30)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-2 h-2 bg-white/30 rounded-full"
            animate={{
              y: [-20, 20, -20],
              x: [-10, 10, -10],
              opacity: [0.3, 0.8, 0.3],
            }}
            transition={{
              duration: 3 + Math.random() * 2,
              repeat: Infinity,
              ease: "easeInOut",
              delay: Math.random() * 2,
            }}
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
            }}
          />
        ))}
      </div>

      {/* Main Content */}
      <div className="relative z-10 min-h-screen flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full">
          {/* Logo and Branding */}
          <motion.div 
            className="text-center mb-8"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="flex items-center justify-center mb-6">
              <Link 
                to={user ? "/dashboard" : "/"}
                className="cursor-pointer hover:opacity-80 transition-opacity"
                aria-label={user ? "Fikiri Solutions - Go to dashboard" : "Fikiri Solutions - Return to homepage"}
              >
                <FikiriLogo size="xl" variant="full" textColor="white" className="mx-auto" />
              </Link>
            </div>
            <motion.h1 
              className="text-5xl font-bold text-white mb-2 font-serif tracking-tight"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
            >
              Join Fikiri
            </motion.h1>
            <motion.p 
              className="text-xl text-white/90 mb-1 font-medium"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
            >
              Start Your Automation Journey
            </motion.p>
            <motion.p 
              className="text-sm text-white/70 font-light"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
            >
              Transform your business with intelligent automation
            </motion.p>
          </motion.div>

          {/* Signup Form */}
          <motion.div 
            className="bg-white/10 backdrop-blur-xl rounded-3xl p-8 shadow-2xl border border-white/20"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.5 }}
          >
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-white text-center mb-2 font-serif">
                Create Your Account
              </h2>
              <p className="text-white text-center text-sm font-light opacity-80">
                Get started with Fikiri Solutions today
              </p>
            </div>
            
            <form className="space-y-6" onSubmit={handleSubmit}>
              {errors.submit && (
                <div className="bg-red-500/20 border border-red-500/50 rounded-xl p-4 backdrop-blur-sm">
                  <div className="flex items-center">
                    <AlertCircle className="h-5 w-5 text-red-300 mr-2" />
                    <p className="text-sm text-red-200">{errors.submit}</p>
                  </div>
                </div>
              )}
              
              {/* Name Fields */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="firstName" className="block text-sm font-medium text-gray-200 mb-2">
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
                  <label htmlFor="lastName" className="block text-sm font-medium text-gray-200 mb-2">
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
                <label htmlFor="email" className="block text-sm font-medium text-gray-200 mb-2">
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
                    autoComplete="email"
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
                <label htmlFor="company" className="block text-sm font-medium text-gray-200 mb-2">
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

              {/* Optional Phone + SMS Consent (CTIA/TCPA express consent) */}
              <div>
                <label htmlFor="phone" className="block text-sm font-medium text-gray-200 mb-2">
                  Phone Number <span className="text-gray-500 font-normal">(optional)</span>
                </label>
                <div className="relative">
                  <input
                    id="phone"
                    name="phone"
                    type="tel"
                    autoComplete="tel"
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
                      checked={formData.smsConsent}
                      onChange={handleInputChange}
                      className="w-4 h-4 text-brand-accent bg-white/10 border-white/20 rounded focus:ring-brand-accent focus:ring-2"
                    />
                  </div>
                  <label htmlFor="smsConsent" className="ml-3 text-sm text-gray-300">
                    I agree to receive account and security-related SMS messages from Fikiri Solutions. Reply STOP to opt out. Reply HELP for help. Msg &amp; data rates may apply. Consent is not a condition of purchase.
                  </label>
                </div>
              </div>
              
              {/* Password Fields */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-gray-200 mb-2">
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
                      autoComplete="new-password"
                      required
                      className={`w-full pl-12 pr-12 py-3 bg-white border border-gray-300 rounded-xl text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-all duration-200 ${errors.password ? 'border-red-500 focus:ring-red-500' : ''}`}
                      placeholder="••••••••"
                      value={formData.password}
                      onChange={handleInputChange}
                    />
                    <button
                      type="button"
                      className="absolute inset-y-0 right-0 pr-4 flex items-center"
                      onClick={() => setShowPassword(!showPassword)}
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
                  <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-200 mb-2">
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
                      autoComplete="new-password"
                      required
                      className={`w-full pl-12 pr-12 py-3 bg-white border border-gray-300 rounded-xl text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-all duration-200 ${errors.confirmPassword ? 'border-red-500 focus:ring-red-500' : ''}`}
                      placeholder="••••••••"
                      value={formData.confirmPassword}
                      onChange={handleInputChange}
                    />
                    <button
                      type="button"
                      className="absolute inset-y-0 right-0 pr-4 flex items-center"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
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
                className="w-full flex justify-center items-center py-3 px-4 border border-transparent rounded-xl shadow-sm text-sm font-medium text-white bg-gradient-to-r from-brand-primary to-brand-secondary hover:from-brand-secondary hover:to-brand-primary focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-accent disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
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

              <div className="mt-6 grid grid-cols-2 gap-3">
                <button
                  type="button"
                  disabled
                  title="Coming soon"
                  className="w-full inline-flex justify-center py-3 px-4 border border-white/10 rounded-xl bg-white/5 text-sm font-medium text-gray-400 cursor-not-allowed"
                >
                  <Chrome className="h-5 w-5 mr-2" />
                  Gmail (coming soon)
                </button>

                <button
                  type="button"
                  disabled
                  title="Coming soon"
                  className="w-full inline-flex justify-center py-3 px-4 border border-white/10 rounded-xl bg-white/5 text-sm font-medium text-gray-400 cursor-not-allowed"
                >
                  <Github className="h-5 w-5 mr-2" />
                  GitHub (coming soon)
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
          </motion.div>

          {/* Features Preview */}
          <motion.div 
            className="mt-8 grid grid-cols-3 gap-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.8 }}
          >
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
          </motion.div>
        </div>
      </div>
    </div>
    </RadiantLayout>
  );
};

export { Signup };
