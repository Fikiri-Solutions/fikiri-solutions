import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'react-hot-toast';
import { apiClient } from '../services/apiClient';
import { config } from '../config';
import { CheckCircle, Mail, Building, User, ArrowRight, Sparkles, Zap } from 'lucide-react';

export const Onboarding: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, updateUser } = useAuth();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [checkingEmail, setCheckingEmail] = useState(false);
  const [emailConnected, setEmailConnected] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    company: '',
    industry: ''
  });
  
  // Check if user is returning from OAuth redirect
  useEffect(() => {
    const checkEmailConnection = async () => {
      if (user?.id && step === 2) {
        setCheckingEmail(true);
        try {
          const status = await apiClient.getGmailConnectionStatus();
          if (status?.connected) {
            setEmailConnected(true);
            toast.success('Email connected successfully!');
            // Auto-advance to next step after 2 seconds, preserving redirect
            setTimeout(() => {
              const redirectPath = getRedirectPath()
              if (redirectPath) {
                navigate(`/onboarding-flow/3?redirect=${encodeURIComponent(redirectPath)}`, { replace: true })
              } else {
                setStep(3)
              }
            }, 2000);
          }
        } catch (error) {
          // Email not connected yet, that's okay
        } finally {
          setCheckingEmail(false);
        }
      }
    };

    checkEmailConnection();
  }, [user?.id, step, location.search]);

  // Check URL parameters for step or path
  useEffect(() => {
    const urlParams = new URLSearchParams(location.search);
    const stepParam = urlParams.get('step');
    if (stepParam) {
      setStep(parseInt(stepParam) || 1);
    } else if (location.pathname.includes('/sync')) {
      // Handle old /onboarding-flow/sync route
      setStep(2);
      // Redirect to clean URL
      navigate('/onboarding-flow/2', { replace: true });
    } else {
      // Check if step is in the path (e.g., /onboarding-flow/2)
      const pathMatch = location.pathname.match(/\/onboarding-flow\/(\d+)/);
      if (pathMatch) {
        setStep(parseInt(pathMatch[1]) || 1);
      }
    }
  }, [location.search, location.pathname, navigate]);

  // Get redirect parameter from URL
  const getRedirectPath = () => {
    const urlParams = new URLSearchParams(location.search);
    const redirectParam = urlParams.get('redirect');
    // Only allow safe internal redirects
    if (redirectParam && redirectParam.startsWith('/') && !redirectParam.startsWith('//')) {
      return redirectParam;
    }
    return null;
  };

  const nextStep = () => {
    if (step === 2 && !formData.name && !formData.company) {
      toast.error('Please fill in your name and company');
      return;
    }
    // Preserve redirect parameter when moving to next step
    const redirectPath = getRedirectPath()
    const newStep = Math.min(step + 1, 4)
    if (redirectPath) {
      navigate(`/onboarding-flow/${newStep}?redirect=${encodeURIComponent(redirectPath)}`, { replace: true })
    } else {
      setStep(newStep)
    }
  };

  const prevStep = () => setStep(prev => Math.max(prev - 1, 1));

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleGoogleAuth = async () => {
    // Preserve redirect parameter through OAuth flow
    const redirectPath = getRedirectPath()
    const redirectParam = redirectPath ? `?redirect=${encodeURIComponent(redirectPath)}` : ''
    const redirectUri = `${window.location.origin}/onboarding-flow/2${redirectParam}`
    try {
      const data = await apiClient.startGmailOAuth(redirectUri)
      if (data.url) {
        toast.loading('Redirecting to Gmail...', { id: 'oauth-redirect' })
        window.location.href = data.url
      } else {
        toast.error(data.error || 'Failed to connect to Google OAuth')
      }
    } catch (error) {
      console.error('OAuth error:', error)
      toast.error('Failed to connect to Google OAuth')
    }
  };

  const handleSubmit = async () => {
    if (!formData.name || !formData.company) {
      toast.error('Please fill in required fields');
      return;
    }

    if (!user) {
      toast.error('Please log in to continue onboarding');
      navigate('/login');
      return;
    }

    setLoading(true);
    
    try {
      await apiClient.updateOnboardingStep(4);
    } catch (error) {
      console.warn('Failed to update onboarding step, continuing anyway', error);
    }

    try {
      await apiClient.saveOnboarding(formData);
        toast.success('Onboarding completed!');
        localStorage.setItem('fikiri-onboarding-just-completed', 'true');
      updateUser({
        ...user,
        onboarding_completed: true,
        onboarding_step: 4
      });
        // Check for redirect parameter, otherwise go to dashboard
        const redirectPath = getRedirectPath();
        navigate(redirectPath || '/dashboard');
    } catch (error: any) {
      console.error('Onboarding error:', error);
      const message = error?.response?.data?.error || error?.message || 'Failed to save onboarding data';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

        return (
    <div className="min-h-screen bg-gradient-to-br from-brand-background via-brand-tan/20 to-brand-background flex items-center justify-center px-4 py-12">
      <div className="max-w-2xl w-full">
        {/* Progress indicator */}
        <div className="mb-8">
          <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
            <span className="font-medium">Step {step} of 4</span>
            <span className="font-medium">{Math.round((step / 4) * 100)}% Complete</span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
            <div 
              className="bg-gradient-to-r from-brand-primary to-brand-secondary h-3 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${(step / 4) * 100}%` }}
            ></div>
              </div>
            </div>

        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl p-8 md:p-10">
          {/* Step 1: Welcome & Company Info */}
        {step === 1 && (
            <div className="space-y-6">
          <div className="text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-brand-primary to-brand-secondary rounded-full mb-4">
                  <Sparkles className="h-8 w-8 text-white" />
                </div>
                <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                  Welcome to Fikiri Solutions
                </h2>
                <p className="text-lg text-gray-600 dark:text-gray-300">
                  Let's set up your account in just a few steps
                </p>
          </div>

            <div className="space-y-4">
              <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
                    <User className="h-4 w-4" />
                  Your Name *
                </label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                    placeholder="John Doe"
                    className="w-full border-2 border-gray-300 dark:border-gray-600 rounded-xl px-4 py-3 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition-all"
                  required
                />
              </div>

              <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
                    <Building className="h-4 w-4" />
                  Company Name *
                </label>
                <input
                  type="text"
                  name="company"
                  value={formData.company}
                  onChange={handleChange}
                    placeholder="Acme Inc."
                    className="w-full border-2 border-gray-300 dark:border-gray-600 rounded-xl px-4 py-3 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition-all"
                  required
                />
              </div>

              <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                    Industry (Optional)
                </label>
                <input
                  type="text"
                  name="industry"
                  value={formData.industry}
                  onChange={handleChange}
                    placeholder="e.g., Real Estate, Property Management, Construction"
                    className="w-full border-2 border-gray-300 dark:border-gray-600 rounded-xl px-4 py-3 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition-all"
                />
              </div>
            </div>

              <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl p-4 border border-blue-200 dark:border-blue-800">
                <p className="text-sm text-blue-800 dark:text-blue-200">
                  <strong>Why we need this:</strong> We'll use this information to personalize your experience and provide industry-specific automation suggestions.
                </p>
              </div>

              <button
                onClick={nextStep}
                disabled={!formData.name || !formData.company}
                className="w-full bg-gradient-to-r from-brand-primary to-brand-secondary hover:from-brand-secondary hover:to-brand-primary text-white font-semibold py-4 px-6 rounded-xl transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl"
              >
                Continue
                <ArrowRight className="h-5 w-5" />
              </button>
            </div>
          )}

          {/* Step 2: Email Connection */}
          {step === 2 && (
            <div className="space-y-6">
              <div className="text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full mb-4">
                  <Mail className="h-8 w-8 text-white" />
                </div>
                <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                  Connect Your Email
                </h2>
                <p className="text-lg text-gray-600 dark:text-gray-300">
                  This is the foundation of your automation
                </p>
            </div>
            
              {checkingEmail && (
                <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl p-4 border border-blue-200 dark:border-blue-800">
                  <div className="flex items-center gap-3">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                    <p className="text-sm text-blue-800 dark:text-blue-200">
                      Checking email connection...
                    </p>
            </div>
          </div>
        )}

              {emailConnected && (
                <div className="bg-green-50 dark:bg-green-900/20 rounded-xl p-6 border-2 border-green-500 dark:border-green-600">
                  <div className="flex items-center gap-3 mb-2">
                    <CheckCircle className="h-6 w-6 text-green-600 dark:text-green-400" />
                    <h3 className="font-semibold text-green-900 dark:text-green-100">
                      Email Connected Successfully!
                    </h3>
                  </div>
                  <p className="text-sm text-green-800 dark:text-green-200">
                    Your email is now connected. We'll start syncing your emails automatically.
                  </p>
                </div>
              )}

              {!emailConnected && !checkingEmail && (
                <>
            <div className="space-y-4">
                    <div className="p-6 border-2 border-gray-200 dark:border-gray-700 rounded-xl hover:border-brand-primary dark:hover:border-brand-primary transition-all bg-gradient-to-br from-white to-gray-50 dark:from-gray-800 dark:to-gray-900">
                      <div className="flex items-start justify-between mb-4">
                        <div>
                          <h3 className="font-semibold text-gray-900 dark:text-white text-lg mb-2">
                            Gmail / Google Workspace
                          </h3>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            Connect your Gmail account to enable email automation, lead capture, and AI-powered responses.
                          </p>
                        </div>
                        <div className="w-12 h-12 bg-red-100 dark:bg-red-900/20 rounded-lg flex items-center justify-center flex-shrink-0">
                          <svg className="w-6 h-6 text-red-600 dark:text-red-400" viewBox="0 0 24 24">
                            <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                            <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                            <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                            <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                          </svg>
                        </div>
                      </div>
                <button
                  onClick={handleGoogleAuth}
                        className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-3 px-6 rounded-lg transition-all duration-200 flex items-center justify-center gap-2 shadow-md hover:shadow-lg"
                >
                        <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  Connect Gmail
                </button>
              </div>

                    <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-xl border border-yellow-200 dark:border-yellow-800">
                      <p className="text-sm text-yellow-800 dark:text-yellow-200">
                        <strong>Note:</strong> Email connection is required for Fikiri to work. Without it, you won't be able to automate emails, capture leads, or use AI responses.
                      </p>
                    </div>
                  </div>

                  <div className="flex justify-between gap-4">
                    <button
                      onClick={prevStep}
                      className="px-6 py-3 border-2 border-gray-300 dark:border-gray-600 rounded-xl text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-all font-medium"
                    >
                      Back
                    </button>
                    <button
                      onClick={nextStep}
                      className="px-6 py-3 bg-gray-600 hover:bg-gray-700 text-white rounded-xl transition-all font-medium"
                    >
                      Skip for now
                    </button>
                  </div>
                </>
              )}

              {emailConnected && (
                <button
                  onClick={nextStep}
                  className="w-full bg-gradient-to-r from-brand-primary to-brand-secondary hover:from-brand-secondary hover:to-brand-primary text-white font-semibold py-4 px-6 rounded-xl transition-all duration-200 flex items-center justify-center gap-2 shadow-lg hover:shadow-xl"
                >
                  Continue
                  <ArrowRight className="h-5 w-5" />
                </button>
              )}
            </div>
          )}

          {/* Step 3: What's Next */}
          {step === 3 && (
            <div className="space-y-6">
              <div className="text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-green-500 to-green-600 rounded-full mb-4">
                  <Zap className="h-8 w-8 text-white" />
                </div>
                <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                  You're Almost There!
                </h2>
                <p className="text-lg text-gray-600 dark:text-gray-300">
                  Here's what happens next
                </p>
              </div>

              <div className="space-y-4">
                <div className="p-6 bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/10 rounded-xl border-2 border-blue-200 dark:border-blue-800">
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 w-10 h-10 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold text-lg">
                      1
                    </div>
                    <div>
                      <h3 className="font-semibold text-blue-900 dark:text-blue-100 text-lg mb-1">
                        Email Sync Begins
                      </h3>
                      <p className="text-sm text-blue-800 dark:text-blue-200">
                        We'll start syncing your emails automatically. This usually takes 5-10 minutes.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="p-6 bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-800/10 rounded-xl border-2 border-purple-200 dark:border-purple-800">
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 w-10 h-10 bg-purple-600 text-white rounded-full flex items-center justify-center font-bold text-lg">
                      2
                    </div>
                    <div>
                      <h3 className="font-semibold text-purple-900 dark:text-purple-100 text-lg mb-1">
                        Leads Appear Automatically
                      </h3>
                      <p className="text-sm text-purple-800 dark:text-purple-200">
                        As emails sync, we'll automatically identify leads and add them to your CRM.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="p-6 bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-800/10 rounded-xl border-2 border-green-200 dark:border-green-800">
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 w-10 h-10 bg-green-600 text-white rounded-full flex items-center justify-center font-bold text-lg">
                      3
                    </div>
                    <div>
                      <h3 className="font-semibold text-green-900 dark:text-green-100 text-lg mb-1">
                        Set Up Your First Automation
                      </h3>
                      <p className="text-sm text-green-800 dark:text-green-200">
                        Visit the Automations page to enable workflows that save you time.
                      </p>
                    </div>
                  </div>
              </div>
            </div>

              <div className="flex justify-between gap-4">
              <button
                onClick={prevStep}
                  className="px-6 py-3 border-2 border-gray-300 dark:border-gray-600 rounded-xl text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-all font-medium"
              >
                Back
              </button>
              <button
                onClick={nextStep}
                  className="px-6 py-3 bg-gradient-to-r from-brand-primary to-brand-secondary hover:from-brand-secondary hover:to-brand-primary text-white rounded-xl transition-all font-medium flex items-center gap-2"
              >
                  Continue
                  <ArrowRight className="h-5 w-5" />
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Complete Setup */}
        {step === 4 && (
            <div className="space-y-6">
              <div className="text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-green-500 to-green-600 rounded-full mb-4">
                  <CheckCircle className="h-8 w-8 text-white" />
                </div>
                <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                  Complete Your Setup
                </h2>
                <p className="text-lg text-gray-600 dark:text-gray-300">
                  Review your information and launch your dashboard
                </p>
              </div>

              <div className="space-y-4">
                <div className="p-6 bg-gray-50 dark:bg-gray-700/50 rounded-xl border border-gray-200 dark:border-gray-600">
                  <h3 className="font-semibold text-gray-900 dark:text-white mb-4 text-lg">Your Information</h3>
                  <div className="space-y-3 text-sm">
                    <div className="flex justify-between">
                      <span className="font-medium text-gray-600 dark:text-gray-400">Name:</span>
                      <span className="text-gray-900 dark:text-white">{formData.name || 'Not provided'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-medium text-gray-600 dark:text-gray-400">Company:</span>
                      <span className="text-gray-900 dark:text-white">{formData.company || 'Not provided'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-medium text-gray-600 dark:text-gray-400">Industry:</span>
                      <span className="text-gray-900 dark:text-white">{formData.industry || 'Not provided'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-medium text-gray-600 dark:text-gray-400">Email:</span>
                      <span className="text-gray-900 dark:text-white">{emailConnected ? 'Connected ✓' : 'Not connected'}</span>
                    </div>
                  </div>
                </div>

                <div className="p-6 bg-gradient-to-br from-brand-primary/10 to-brand-secondary/10 rounded-xl border-2 border-brand-primary/20">
                  <h3 className="font-semibold text-gray-900 dark:text-white mb-3 text-lg">What's Next?</h3>
                  <ul className="text-sm text-gray-700 dark:text-gray-300 space-y-2">
                    <li className="flex items-start gap-2">
                      <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
                      <span>Access your personalized dashboard with real-time insights</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
                      <span>Set up email automation rules to save time</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
                      <span>Start managing leads in your CRM</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
                      <span>Get AI-powered business recommendations</span>
                    </li>
                </ul>
              </div>
            </div>

              <div className="flex justify-between gap-4">
              <button
                onClick={prevStep}
                  className="px-6 py-3 border-2 border-gray-300 dark:border-gray-600 rounded-xl text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-all font-medium"
              >
                Back
              </button>
              <button
                onClick={handleSubmit}
                disabled={loading}
                  className="px-8 py-3 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white rounded-xl transition-all font-semibold flex items-center gap-2 shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                      Completing Setup...
                    </>
                  ) : (
                    <>
                      Launch Dashboard
                      <ArrowRight className="h-5 w-5" />
                    </>
                  )}
              </button>
            </div>
          </div>
        )}
          </div>
      </div>
    </div>
  );
};
