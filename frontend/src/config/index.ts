export interface FeatureConfig {
  showOnboarding: boolean
  showAnalytics: boolean
  showAdvancedFeatures: boolean
}

export const getFeatureConfig = (): FeatureConfig => {
  return {
    showOnboarding: true,
    showAnalytics: true,
    showAdvancedFeatures: true
  }
}
