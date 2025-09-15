/**
 * Feature Flags Configuration
 * 
 * Toggle features on/off for incremental testing and deployment.
 * Keep this simple - no complex logic, just boolean toggles.
 */

export const features = {
  // Core features
  onboarding: true,
  dashboard: true,
  services: true,
  
  // Advanced features (hide until ready)
  crmPage: true,         // Enable CRM page
  darkMode: false,       // Dark mode toggle
  analytics: false,     // Advanced analytics dashboard
  
  // Experimental features
  realTimeUpdates: false, // WebSocket real-time updates
  advancedSettings: false, // Advanced service configuration
  
  // Debug features
  debugMode: false,     // Show debug info in development
  mockData: true,        // Use mock data for instant loading (set to false for production)
} as const

/**
 * Environment Configuration
 */
export const config = {
  // API Configuration
  apiUrl: import.meta.env.VITE_API_URL || (features.mockData 
    ? 'http://localhost:3000/api'  // Mock API for local testing
    : 'https://fikirisolutions.com/api'),  // Real backend
  
  // Domain Configuration
  domain: 'fikirisolutions.com',
  productionUrl: 'https://fikirisolutions.com',
  
  // App Configuration
  appName: 'Fikiri Solutions',
  version: '1.0.2', // Updated for Vercel deployment
  
  // Development flags
  isDevelopment: typeof window !== 'undefined' && window.location.hostname === 'localhost',
  isProduction: typeof window !== 'undefined' && window.location.hostname !== 'localhost',
} as const

/**
 * Helper function to check if a feature is enabled
 */
export const isFeatureEnabled = (feature: keyof typeof features): boolean => {
  return features[feature]
}

/**
 * Get feature configuration for conditional rendering
 */
export const getFeatureConfig = () => ({
  showOnboarding: isFeatureEnabled('onboarding'),
  showCrmPage: isFeatureEnabled('crmPage'),
  showDarkMode: isFeatureEnabled('darkMode'),
  showAnalytics: isFeatureEnabled('analytics'),
  useMockData: isFeatureEnabled('mockData'),
  debugMode: isFeatureEnabled('debugMode'),
})

