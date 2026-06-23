import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'react-hot-toast';
import { config } from '../config';
import { apiGet, apiPut, apiPost } from '../lib/api';

export const Onboarding: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, checkAuthStatus } = useAuth();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const [formData, setFormData] = useState({
    name: '',
    company: '',
    industry: ''
  });

  // A/B Testing Hook
  const [variant] = useState<'A' | 'B'>(() => {
    // Persist variant across sessions
    const savedVariant = localStorage.getItem('fikiri-onboarding-variant');
    if (savedVariant && (savedVariant === 'A' || savedVariant === 'B')) {
      return savedVariant as 'A' | 'B';
    }
    const newVariant = Math.random() < 0.5 ? 'A' : 'B';
    localStorage.setItem('fikiri-onboarding-variant', newVariant);
    return newVariant;
  });

  // Sync step with server state on mount
  useEffect(() => {
    const initializeStep = async () => {
      try {
        setInitializing(true);

        // Check URL parameters first
        const urlParams = new URLSearchParams(location.search);
        const stepParam = urlParams.get('step');

        // If user exists, sync with server state
        if (user) {
          try {
            // Fetch current onboarding status from server
            const status = await apiGet<{
              completed: boolean;
              step: number;
              data?: any;
            }>('/onboarding/status');

            if (status.completed) {
              // User already completed onboarding, redirect to dashboard
              navigate('/dashboard');
              return;
            }

            // Use server step if available, otherwise use URL param or default to 1
            const serverStep = status.step || 1;
            const urlStep = stepParam ? parseInt(stepParam) : null;

            // Validate step is between 1-4
            const validStep = Math.max(1, Math.min(4, urlStep || serverStep || 1));
            setStep(validStep);

            // If we have onboarding data, populate form
            if (status.data) {
              setFormData({
                name: status.data.name || '',
                company: status.data.company || '',
                industry: status.data.industry || ''
              });
            }
          } catch (error) {
            if (import.meta.env.DEV) {
              console.warn('Failed to fetch onboarding status, using local state:', error);
            }
            // Fallback to URL param or user's onboarding_step
            const urlStep = stepParam ? parseInt(stepParam) : null;
            const userStep = user.onboarding_step || 1;
            const validStep = Math.max(1, Math.min(4, urlStep || userStep || 1));
            setStep(validStep);
          }
        } else {
          // No user, use URL param or default to 1
          const urlStep = stepParam ? parseInt(stepParam) : 1;
          setStep(Math.max(1, Math.min(4, urlStep)));
        }
      } catch (error) {
        if (import.meta.env.DEV) {
          console.error('Error initializing onboarding step:', error);
        }
        setStep(1);
      } finally {
        setInitializing(false);
      }
    };

    initializeStep();
  }, [location.search, user, navigate]);

  const nextStep = async () => {
    const newStep = Math.min(4, step + 1);

    // Update step on server
    try {
      const token = localStorage.getItem('fikiri-token');
      if (!token) {
        toast.error('Authentication required');
        return;
      }

      await apiPut('/user/onboarding-step', { step: newStep });

      // Refresh user state to get updated onboarding_step
      await checkAuthStatus();

      setStep(newStep);
    } catch (error: any) {
      if (import.meta.env.DEV) {
        console.error('Failed to update step:', error);
      }
      // Still allow step progression in UI, but log the error
      setStep(newStep);
    }
  };

  const prevStep = () => {
    const newStep = Math.max(1, step - 1);
    setStep(newStep);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleGoogleAuth = () => {
    // Use config API URL
    const baseUrl = config.apiUrl.replace('/api', '');

    fetch(`${baseUrl}/api/oauth/gmail/start`)
      .then(response => response.json())
      .then(data => {
        if (data.url) {
          window.location.href = data.url;
        } else {
          toast.error(data.error || 'Failed to connect to Google OAuth');
        }
      })
      .catch(error => {
        if (import.meta.env.DEV) {
          console.error('OAuth error:', error);
        }
        toast.error('Failed to connect to Google OAuth');
      });
  };

  const handleSubmit = async () => {
    if (!formData.name || !formData.company) {
      toast.error('Please fill in required fields');
      return;
    }

    setLoading(true);

    try {
      // First save the onboarding data (this will also mark onboarding as completed)
      const response = await apiPost('/onboarding', formData);

      if (response) {
        // Refresh user state to get updated onboarding status
        await checkAuthStatus();

        toast.success('Onboarding completed!');
        // Set flag to show welcome banner
        localStorage.setItem('fikiri-onboarding-just-completed', 'true');
        navigate('/dashboard');
      }
    } catch (error: any) {
      if (import.meta.env.DEV) {
        console.error('Onboarding error:', error);
      }
      toast.error(error.message || 'Failed to save onboarding data');
    } finally {
      setLoading(false);
    }
  };

  const skipStep = () => {
    if (import.meta.env.DEV) {
      console.log('Skip button clicked!');
      console.log('User object:', user);
      console.log('User ID:', user?.id);
      console.log('Is authenticated:', !!user);
    }

    try {
      toast('Skipping onboarding...', { icon: 'ℹ️' });

      // Always navigate to login for now - this is the safest approach
      // The login page will handle redirecting authenticated users appropriately
      if (import.meta.env.DEV) {
        console.log('Navigating to login page');
      }
      navigate('/login');
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error('Error in skipStep:', error);
      }
      // Fallback navigation
      navigate('/login');
    }
  };

        return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8">
        {/* Progress indicator */}
        <div className="mb-8">
          <div className="flex justify-between text-sm text-gray-500 mb-2">
            <span>Step {step} of 4</span>
            <span>{Math.round((step / 4) * 100)}% Complete</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${(step / 4) * 100}%` }}
            ></div>
              </div>
            </div>

        {/* Step 1: Google OAuth */}
        {step === 1 && (
          <div className="text-center">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Welcome to Fikiri Solutions</h2>
            <p className="text-gray-600 mb-8">Connect your Google account to get started</p>

            <button
              onClick={handleGoogleAuth}
              className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-200 flex items-center justify-center"
            >
              <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Continue with Google
            </button>

            <button
              onClick={skipStep}
              className="mt-4 text-gray-500 hover:text-gray-700 text-sm underline"
            >
              Skip for now
            </button>
          </div>
        )}

        {/* Step 2: Company Info */}
        {step === 2 && (
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Tell Us About Your Company</h2>
            <p className="text-gray-600 mb-6">Help us customize your experience</p>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Your Name *
                </label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="Enter your full name"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Company Name *
                </label>
                <input
                  type="text"
                  name="company"
                  value={formData.company}
                  onChange={handleChange}
                  placeholder="Enter your company name"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Industry
                </label>
                <input
                  type="text"
                  name="industry"
                  value={formData.industry}
                  onChange={handleChange}
                  placeholder="e.g., Technology, Healthcare, Finance"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            <div className="flex justify-between mt-8">
              <button
                onClick={prevStep}
                className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 focus:ring-2 focus:ring-blue-500"
              >
                Back
              </button>
              <button
                onClick={nextStep}
                disabled={!formData.name || !formData.company}
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg transition-colors duration-200"
              >
                {variant === 'A' ? 'Next' : 'Continue'}
              </button>
            </div>

            {/* Skip option on Step 2 */}
            <div className="mt-6 text-center">
              <button
                onClick={skipStep}
                className="text-sm text-gray-500 hover:text-gray-700 underline"
              >
                Skip for now
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Email Integration */}
        {step === 3 && (
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Connect Your Email</h2>
            <p className="text-gray-600 mb-6">Connect your email to start automating responses</p>

            <div className="space-y-4">
              <div className="p-4 border border-gray-200 rounded-lg">
                <h3 className="font-semibold text-gray-900 mb-2">Gmail Integration</h3>
                <p className="text-sm text-gray-600 mb-4">Connect your Gmail account to enable email automation</p>
                <button
                  onClick={handleGoogleAuth}
                  className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors duration-200 flex items-center justify-center"
                >
                  <svg className="w-4 h-4 mr-2" viewBox="0 0 24 24">
                    <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  Connect Gmail
                </button>
              </div>

              <div className="p-4 border border-gray-200 rounded-lg">
                <h3 className="font-semibold text-gray-900 mb-2">Other Email Providers</h3>
                <p className="text-sm text-gray-600 mb-4">We support Outlook, Yahoo, and other IMAP providers</p>
                <button
                  onClick={nextStep}
                  className="w-full bg-gray-600 hover:bg-gray-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors duration-200"
                >
                  Skip for now
                </button>
              </div>
            </div>

            <div className="flex justify-between mt-8">
              <button
                onClick={prevStep}
                className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 focus:ring-2 focus:ring-blue-500"
              >
                Back
              </button>
              <button
                onClick={nextStep}
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors duration-200"
              >
                Next
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Complete Setup */}
        {step === 4 && (
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Complete Your Setup</h2>
            <p className="text-gray-600 mb-6">Review your information and finish onboarding</p>

            <div className="space-y-4">
              <div className="p-4 bg-gray-50 rounded-lg">
                <h3 className="font-semibold text-gray-900 mb-2">Your Information</h3>
                <div className="space-y-2 text-sm">
                  <div><span className="font-medium">Name:</span> {formData.name || 'Not provided'}</div>
                  <div><span className="font-medium">Company:</span> {formData.company || 'Not provided'}</div>
                  <div><span className="font-medium">Industry:</span> {formData.industry || 'Not provided'}</div>
                </div>
              </div>

              <div className="p-4 bg-blue-50 rounded-lg">
                <h3 className="font-semibold text-blue-900 mb-2">What's Next?</h3>
                <ul className="text-sm text-blue-800 space-y-1">
                  <li>• Access your personalized dashboard</li>
                  <li>• Set up email automation rules</li>
                  <li>• Connect additional integrations</li>
                  <li>• Start managing your leads</li>
                </ul>
              </div>
            </div>

            <div className="flex justify-between mt-8">
              <button
                onClick={prevStep}
                className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 focus:ring-2 focus:ring-blue-500"
              >
                Back
              </button>
              <button
                onClick={handleSubmit}
                disabled={loading}
                className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors duration-200 flex items-center"
              >
                {loading && (
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                )}
                {loading ? 'Completing Setup...' : (variant === 'A' ? 'Complete Setup' : 'Finish & Launch')}
              </button>
            </div>
          </div>
        )}

        {/* Loading state */}
        {initializing && (
          <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center rounded-2xl">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
              <p className="text-sm text-gray-600">Loading...</p>
            </div>
          </div>
        )}

        {/* Debug info for development */}
        {process.env.NODE_ENV === 'development' && !initializing && (
          <div className="mt-8 p-4 bg-gray-100 rounded-lg text-xs text-gray-600">
            <div>Current user: {user?.email || 'Not logged in'}</div>
            <div>User onboarding_step: {user?.onboarding_step || 'N/A'}</div>
            <div>User onboarding_completed: {user?.onboarding_completed ? 'Yes' : 'No'}</div>
            <div>Current step: {step}</div>
            <div>Form data: {JSON.stringify(formData)}</div>
          </div>
        )}
      </div>
    </div>
  );
};
