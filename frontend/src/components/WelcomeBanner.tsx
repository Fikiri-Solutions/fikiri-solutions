import React, { useState, useEffect } from 'react';
import { CheckCircle, X, Settings } from 'lucide-react';

interface WelcomeBannerProps {
  onDismiss?: () => void;
  onRevisitOnboarding?: () => void;
}

export const WelcomeBanner: React.FC<WelcomeBannerProps> = ({ 
  onDismiss, 
  onRevisitOnboarding 
}) => {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Show banner if user just completed onboarding
    const justCompleted = localStorage.getItem('fikiri-onboarding-just-completed');
    if (justCompleted === 'true') {
      setIsVisible(true);
      // Clear the flag
      localStorage.removeItem('fikiri-onboarding-just-completed');
    }
  }, []);

  const handleDismiss = () => {
    setIsVisible(false);
    onDismiss?.();
  };

  const handleRevisitOnboarding = () => {
    setIsVisible(false);
    onRevisitOnboarding?.();
  };

  if (!isVisible) return null;

  return (
    <div className="fixed top-4 right-4 z-50 max-w-md">
      <div className="bg-green-50 border border-green-200 rounded-lg shadow-lg p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <CheckCircle className="h-6 w-6 text-green-600" />
          </div>
          <div className="ml-3 flex-1">
            <h3 className="text-sm font-medium text-green-800">
              🎉 Welcome to Fikiri!
            </h3>
            <p className="mt-1 text-sm text-green-700">
              Your onboarding is complete! You can revisit onboarding anytime in{' '}
              <button
                onClick={handleRevisitOnboarding}
                className="font-medium text-green-800 hover:text-green-900 underline"
              >
                Settings → Onboarding
              </button>
              .
            </p>
            <div className="mt-3 flex space-x-2">
              <button
                onClick={handleRevisitOnboarding}
                className="inline-flex items-center px-3 py-1.5 border border-green-300 text-xs font-medium rounded text-green-700 bg-green-100 hover:bg-green-200 focus:outline-none focus:ring-2 focus:ring-green-500"
              >
                <Settings className="h-3 w-3 mr-1" />
                Settings
              </button>
              <button
                onClick={handleDismiss}
                className="inline-flex items-center px-3 py-1.5 border border-green-300 text-xs font-medium rounded text-green-700 bg-white hover:bg-green-50 focus:outline-none focus:ring-2 focus:ring-green-500"
              >
                Dismiss
              </button>
            </div>
          </div>
          <div className="ml-4 flex-shrink-0">
            <button
              onClick={handleDismiss}
              className="inline-flex text-green-400 hover:text-green-600 focus:outline-none focus:ring-2 focus:ring-green-500 rounded"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WelcomeBanner;
