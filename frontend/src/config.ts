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
  mockData: false,       // Use real API data (set to true for development)
} as const

/**
 * Environment Configuration
 */
export const config = {
  // API Configuration
  apiUrl: import.meta.env.VITE_API_URL || (features.mockData 
    ? 'http://localhost:3000/api'  // Mock API for local testing
    : 'https://fikirisolutions.onrender.com/api'),  // ✅ WORKING Render backend
  
  // Domain Configuration
  domain: 'fikirisolutions.com',
  productionUrl: 'https://fikirisolutions.com',
  wwwUrl: 'https://www.fikirisolutions.com',
  
  // App Configuration
  appName: 'Fikiri Solutions',
  version: '1.0.16', // Force deployment refresh - fixed missing icon imports
  buildTimestamp: '2025-09-25T19:25:00Z', // Force cache refresh
  cacheVersion: 'v1.0.16-20250925', // Force cache refresh
  
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

// Deployment timestamp: Wed Sep 25 18:35:00 EDT 2025 - Fix landing page loading issue
