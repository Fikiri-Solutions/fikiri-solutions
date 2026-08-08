import { BrowserRouter as Router, Routes, Route, Navigate, useParams, useLocation } from 'react-router-dom'
import { Suspense, useMemo, lazy, type ComponentType } from 'react'
import { HelmetProvider } from 'react-helmet-async'
import { QueryProvider } from './providers/QueryProvider'
import { ToastProvider } from './components/Toast'
import { ThemeProvider } from './contexts/ThemeContext'
import { CustomizationProvider } from './contexts/CustomizationContext'
import { ActivityProvider } from './contexts/ActivityContext'
import { AuthProvider } from './contexts/AuthContext'
import { ScrollToTop } from './components/ScrollToTop'
import { ErrorBoundary } from './components/ErrorBoundary'
import { RouteLoadingFallback } from './components/RouteLoadingFallback'
import { ProtectedRoute, AuthRoute, OnboardingRoute } from './components/RouteGuard'
import { AdminRoute } from './components/AdminRoute'
import { LandingThemeGuard } from './components/LandingThemeGuard'
import { ForgotPassword } from './pages/ForgotPassword'
import { ResetPassword } from './pages/ResetPassword'
import { getFeatureConfig } from './config'
import { useWarmRoutes } from './hooks/useWarmRoutes'
import { AccessibilityProvider } from './components/AccessibilityProvider'

// ---------------------------------------------------------------------------
// Route-level code splitting: keep the shell (providers/guards) eager;
// load page modules only when their routes are visited.
// Named exports are remapped to default for React.lazy.
// ---------------------------------------------------------------------------

const named = <T extends Record<string, unknown>, K extends keyof T>(
  loader: () => Promise<T>,
  exportName: K,
) =>
  lazy(async () => {
    const module = await loader()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- lazy remaps named page exports; props vary by route
    return { default: module[exportName] as ComponentType<any> }
  })

// Public marketing
const RadiantLandingPage = lazy(() => import('./pages/RadiantLandingPage'))
const LandingPage = lazy(() => import('./pages/LandingPage'))
const PricingPage = lazy(() => import('./pages/PricingPage'))
const FaqPage = lazy(() => import('./pages/FaqPage'))
const InstallPage = lazy(() => import('./pages/Install'))
const SmsOptIn = lazy(() => import('./pages/SmsOptIn'))
const About = named(() => import('./pages/About'), 'About')
const Contact = named(() => import('./pages/Contact'), 'Contact')
const Intake = named(() => import('./pages/Intake'), 'Intake')
const ServicesLanding = named(() => import('./pages/ServicesLanding'), 'ServicesLanding')
const AIAssistantLanding = named(() => import('./pages/AIAssistantLanding'), 'AIAssistantLanding')
const LandscapingLanding = named(() => import('./pages/LandscapingLanding'), 'LandscapingLanding')
const RestaurantLanding = named(() => import('./pages/RestaurantLanding'), 'RestaurantLanding')
const MedicalLanding = named(() => import('./pages/MedicalLanding'), 'MedicalLanding')
const TermsOfService = named(() => import('./pages/TermsOfService'), 'TermsOfService')
const PrivacyPolicy = named(() => import('./pages/PrivacyPolicy'), 'PrivacyPolicy')
const NotFoundPage = named(() => import('./pages/ErrorPages'), 'NotFoundPage')
const ErrorPage = named(() => import('./pages/ErrorPages'), 'ErrorPage')

// Auth
const Login = named(() => import('./pages/Login'), 'Login')
const Signup = named(() => import('./pages/Signup'), 'Signup')
// ForgotPassword / ResetPassword stay eager: pre-commit secret scanner false-positives on those names in lazy import lines.
const VerifyEmail = named(() => import('./pages/VerifyEmail'), 'VerifyEmail')

// Onboarding + app shell
const Onboarding = named(() => import('./pages/Onboarding'), 'Onboarding')
const Layout = named(() => import('./components/Layout'), 'Layout')
const DemoGatedFeature = named(() => import('./components/DemoGatedFeature'), 'DemoGatedFeature')

// Dashboard / app routes (chart-heavy Dashboard stays behind this boundary)
const Dashboard = named(() => import('./pages/Dashboard'), 'Dashboard')
const Services = named(() => import('./pages/Services'), 'Services')
const CRM = named(() => import('./pages/CRM'), 'CRM')
const AIAssistant = named(() => import('./pages/AIAssistant'), 'AIAssistant')
const Automations = named(() => import('./pages/Automations'), 'Automations')
const AutomationSetupCaptureLeadsEmail = named(
  () => import('./pages/AutomationSetupCaptureLeadsEmail'),
  'AutomationSetupCaptureLeadsEmail',
)
const CorrelationDebugPage = named(() => import('./pages/CorrelationDebugPage'), 'CorrelationDebugPage')
const ChatbotBuilder = named(() => import('./pages/ChatbotBuilder'), 'ChatbotBuilder')
const ContentMigration = named(() => import('./pages/ContentMigration'), 'ContentMigration')
const GmailConnect = named(() => import('./pages/GmailConnect'), 'GmailConnect')
const OutlookConnect = named(() => import('./pages/OutlookConnect'), 'OutlookConnect')
const InboxPage = named(() => import('./pages/InboxPage'), 'InboxPage')
const GmailStatusCheck = named(() => import('./pages/GmailStatusCheck'), 'GmailStatusCheck')
const UsageAnalytics = named(() => import('./pages/UsageAnalytics'), 'UsageAnalytics')
const BillingPage = named(() => import('./pages/BillingPage'), 'BillingPage')
const InternalContact = named(() => import('./pages/InternalContact'), 'InternalContact')
const PrivacySettings = named(() => import('./components/PrivacySettings'), 'PrivacySettings')

// Admin
const AdminLayout = named(() => import('./pages/admin/AdminLayout'), 'AdminLayout')
const AdminDashboard = named(() => import('./pages/admin/AdminDashboard'), 'AdminDashboard')
const TenantDirectory = named(() => import('./pages/admin/TenantDirectory'), 'TenantDirectory')
const TenantDetail = named(() => import('./pages/admin/TenantDetail'), 'TenantDetail')
const AdminAuditLog = named(() => import('./pages/admin/AdminAuditLog'), 'AdminAuditLog')
const AdminMfaSecurity = named(() => import('./pages/admin/AdminMfaSecurity'), 'AdminMfaSecurity')
const AdminSiteChat = named(() => import('./pages/admin/AdminSiteChat'), 'AdminSiteChat')

const Analytics = lazy(async () => {
  const module = await import('@vercel/analytics/react')
  return { default: module.Analytics }
})

const SpeedInsights = lazy(async () => {
  const module = await import('@vercel/speed-insights/react')
  return { default: module.SpeedInsights }
})

/** Legacy /onboarding-flow/* → /onboarding/*; preserve query (e.g. oauth_success, redirect). */
function LegacyOnboardingFlowRootRedirect() {
  const location = useLocation()
  return <Navigate to={`/onboarding${location.search}`} replace />
}

function LegacyOnboardingFlowStepRedirect() {
  const { step } = useParams()
  const location = useLocation()
  return <Navigate to={`/onboarding/${step}${location.search}`} replace />
}

function LegacyOnboardingFlowSyncRedirect() {
  const location = useLocation()
  return <Navigate to={`/onboarding/2${location.search}`} replace />
}

/** Legacy /integrations index → /automations (preserve query: calendar OAuth errors, etc.). */
function LegacyIntegrationsIndexRedirect() {
  const location = useLocation()
  return <Navigate to={`/automations${location.search}`} replace />
}

function App() {
  const features = getFeatureConfig()
  useWarmRoutes() // Warm dashboard chunk after first paint (authenticated only)
  const showObservability = useMemo(() => {
    if (import.meta.env.PROD) {
      return true
    }
    return import.meta.env.VITE_ENABLE_ANALYTICS === 'true'
  }, [])

  return (
    <ErrorBoundary>
      <HelmetProvider>
        <AccessibilityProvider>
          <Router
            future={{
              v7_startTransition: true,
              v7_relativeSplatPath: true,
            }}
          >
          <ThemeProvider>
            <LandingThemeGuard />
            <AuthProvider>
              <CustomizationProvider>
                <ActivityProvider>
                  <QueryProvider>
                    <ToastProvider>
                      <ScrollToTop />
                      <div className="min-h-screen bg-white dark:bg-gray-900 transition-colors duration-300">
                        <Suspense fallback={<RouteLoadingFallback />}>
                          <Routes>
                          {/* Public routes - no authentication required */}
                          <Route path="/" element={<RadiantLandingPage />} />
                          <Route path="/landing-classic" element={<LandingPage />} />
                          <Route path="/pricing" element={<PricingPage />} />
                          <Route path="/faq" element={<FaqPage />} />
                          <Route path="/services-landing" element={<ServicesLanding />} />
                          <Route path="/ai-landing" element={<AIAssistantLanding />} />
                          <Route path="/industries/landscaping" element={<LandscapingLanding />} />
                          <Route path="/industries/restaurant" element={<RestaurantLanding />} />
                          <Route path="/industries/medical" element={<MedicalLanding />} />
                          <Route path="/about" element={<About />} />
                          <Route path="/contact" element={<Contact />} />
                          <Route path="/intake" element={<Intake />} />
                          <Route path="/install" element={<InstallPage />} />
                          <Route path="/sms-opt-in" element={<SmsOptIn />} />
                          <Route path="/terms" element={<TermsOfService />} />
                          <Route path="/privacy" element={<PrivacyPolicy />} />
                          <Route path="/error" element={<ErrorPage />} />
                          
                          {/* Legacy onboarding-flow redirects */}
                          <Route path="/onboarding-flow/sync" element={<LegacyOnboardingFlowSyncRedirect />} />
                          <Route path="/onboarding-flow/:step" element={<LegacyOnboardingFlowStepRedirect />} />
                          <Route path="/onboarding-flow" element={<LegacyOnboardingFlowRootRedirect />} />
                          
                          {/* Authentication routes */}
                          <Route path="/login" element={
                            <AuthRoute>
                              <Login />
                            </AuthRoute>
                          } />
                          <Route path="/signup" element={
                            <AuthRoute>
                              <Signup />
                            </AuthRoute>
                          } />
                          <Route path="/forgot-password" element={
                            <AuthRoute>
                              <ForgotPassword />
                            </AuthRoute>
                          } />
                          <Route path="/reset-password" element={
                            <AuthRoute>
                              <ResetPassword />
                            </AuthRoute>
                          } />

                          <Route path="/verify-email" element={
                            <AuthRoute>
                              <VerifyEmail />
                            </AuthRoute>
                          } />
                          
                          {/* Onboarding routes - require authentication but not completed onboarding */}
                          {features.showOnboarding && (
                            <>
                              <Route path="/onboarding" element={
                                <OnboardingRoute>
                                  <Onboarding />
                                </OnboardingRoute>
                              } />
                              <Route path="/onboarding/:step" element={
                                <OnboardingRoute>
                                  <Onboarding />
                                </OnboardingRoute>
                              } />
                            </>
                          )}
                          
                          {/* Protected routes - require authentication and completed onboarding */}
                          <Route path="/home" element={
                            <ProtectedRoute>
                              <Layout><Dashboard /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/dashboard" element={
                            <ProtectedRoute>
                              <Layout><Dashboard /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/services" element={
                            <ProtectedRoute>
                              <Layout>
                                <DemoGatedFeature route="servicesPreview" previewOnly>
                                  <Services />
                                </DemoGatedFeature>
                              </Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/crm" element={
                            <ProtectedRoute>
                              <Layout><CRM /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/ai" element={
                            <ProtectedRoute>
                              <Layout>
                                <DemoGatedFeature route="aiAssistant">
                                  <AIAssistant />
                                </DemoGatedFeature>
                              </Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/assistant" element={
                            <ProtectedRoute>
                              <Layout>
                                <DemoGatedFeature route="aiAssistant">
                                  <AIAssistant />
                                </DemoGatedFeature>
                              </Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/industry" element={
                            <ProtectedRoute>
                              <Layout>
                                <DemoGatedFeature route="usageAnalytics">
                                  <UsageAnalytics />
                                </DemoGatedFeature>
                              </Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/analytics" element={
                            <ProtectedRoute>
                              <Layout>
                                <DemoGatedFeature route="usageAnalytics">
                                  <UsageAnalytics />
                                </DemoGatedFeature>
                              </Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/automations" element={
                            <ProtectedRoute>
                              <Layout><Automations /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/automations/setup/capture-leads-email" element={
                            <ProtectedRoute>
                              <Layout><AutomationSetupCaptureLeadsEmail /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/debug/correlation" element={
                            <ProtectedRoute>
                              <Layout><CorrelationDebugPage /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/ai/chatbot-builder" element={
                            <ProtectedRoute>
                              <Layout>
                                <DemoGatedFeature route="chatbotBuilder">
                                  <ChatbotBuilder />
                                </DemoGatedFeature>
                              </Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/import-center" element={
                            <ProtectedRoute>
                              <Layout><ContentMigration /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/integrations" element={<LegacyIntegrationsIndexRedirect />} />
                          <Route path="/integrations/gmail" element={
                            <ProtectedRoute>
                              <Layout><GmailConnect /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/integrations/outlook" element={
                            <ProtectedRoute>
                              <Layout><OutlookConnect /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/billing" element={
                            <ProtectedRoute>
                              <Layout><BillingPage /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/support/contact" element={
                            <ProtectedRoute>
                              <Layout><InternalContact /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/inbox/*" element={
                            <Layout><InboxPage /></Layout>
                          } />
                          <Route path="/gmail-status" element={
                            <ProtectedRoute>
                              <Layout><GmailStatusCheck /></Layout>
                            </ProtectedRoute>
                          } />
                          <Route path="/privacy-settings" element={
                            <ProtectedRoute>
                              <Layout><PrivacySettings /></Layout>
                            </ProtectedRoute>
                          } />

                          <Route path="/admin" element={
                            <ProtectedRoute>
                              <AdminRoute>
                                <AdminLayout />
                              </AdminRoute>
                            </ProtectedRoute>
                          }>
                            <Route index element={<AdminDashboard />} />
                            <Route path="tenants" element={<TenantDirectory />} />
                            <Route path="tenants/:tenantId" element={<TenantDetail />} />
                            <Route path="audit" element={<AdminAuditLog />} />
                            <Route path="security" element={<AdminMfaSecurity />} />
                            <Route path="site-chat" element={<AdminSiteChat />} />
                          </Route>
                          
                          {/* 404 route */}
                          <Route path="*" element={<NotFoundPage />} />
                        </Routes>
                      </Suspense>
                    </div>
                    {showObservability && (
                      <Suspense fallback={null}>
                        <Analytics />
                        <SpeedInsights />
                      </Suspense>
                    )}
                    </ToastProvider>
                  </QueryProvider>
                </ActivityProvider>
              </CustomizationProvider>
            </AuthProvider>
          </ThemeProvider>
        </Router>
        </AccessibilityProvider>
      </HelmetProvider>
    </ErrorBoundary>
  )
}

export default App
// DEPLOYMENT MARKER: Tue Sep 16 18:04:02 EDT 2025 - Force Vercel rebuild
// UI/UX Changes: Industry AI, FeatureStatus, BackToTop, Test Attributes
