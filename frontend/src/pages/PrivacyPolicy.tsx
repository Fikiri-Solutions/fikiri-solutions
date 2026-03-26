import React from 'react';
import { Helmet } from 'react-helmet-async';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Home, FileText } from 'lucide-react';
import { RadiantLayout } from '../components/radiant';
import { PublicChatbotWidget } from '../components/PublicChatbotWidget';
import { useAuth } from '../contexts/AuthContext';

const PrivacyPolicy: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuth();
  const homeTo = isAuthenticated && user?.onboarding_completed ? '/dashboard' : '/';

  const handleBack = () => {
    if (window.history.length > 2) {
      navigate(-1);
    } else {
      navigate(homeTo);
    }
  };

  return (
    <RadiantLayout>
    <>
      <Helmet>
        <title>Privacy Policy - Fikiri Solutions</title>
        <meta name="description" content="Privacy Policy for Fikiri Solutions AI-powered Gmail automation platform" />
      </Helmet>
      
      <div className="min-h-screen bg-gray-900 text-white">
        <div className="container mx-auto px-4 py-8 max-w-4xl">
          {/* Navigation Buttons */}
          <div className="mb-6 flex flex-wrap items-center gap-4">
            <button
              onClick={handleBack}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-300 hover:text-white bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </button>
            <button
              onClick={() => navigate(homeTo)}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-300 hover:text-white bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
            >
              <Home className="h-4 w-4" />
              Home
            </button>
            <button
              onClick={() => navigate('/terms')}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-300 hover:text-white bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
            >
              <FileText className="h-4 w-4" />
              Terms of Service
            </button>
          </div>

          <div className="bg-gray-800 rounded-lg p-8 shadow-xl">
            <h1 className="text-4xl font-bold text-center mb-8 text-brand-primary">
                  Privacy Policy
                </h1>
            
            <div className="prose prose-invert max-w-none">
              <p className="text-gray-300 mb-6">
                <strong>Effective Date:</strong> October 18, 2025<br />
                <strong>Last Updated:</strong> March 12, 2026
              </p>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">Introduction</h2>
                <p className="text-gray-300 leading-relaxed">
                  Fikiri Solutions ("we," "our," or "us") is committed to protecting your privacy. 
                  This Privacy Policy explains how we collect, use, disclose, and safeguard your 
                  information when you use our AI-powered Gmail automation platform at 
                  <a href="https://fikirisolutions.com" className="text-brand-primary hover:text-muted-foreground"> https://fikirisolutions.com</a> (the "Service").
                </p>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">Information We Collect</h2>
                
                <h3 className="text-xl font-medium text-green-300 mb-3">Information You Provide</h3>
                <ul className="list-disc list-inside text-gray-300 mb-4 space-y-2">
                  <li><strong>Account Information:</strong> Email address, name, and password</li>
                  <li><strong>Gmail Data:</strong> Emails, contacts, and calendar information (with your explicit consent)</li>
                  <li><strong>Usage Data:</strong> How you interact with our Service</li>
                  <li><strong>Communication Data:</strong> Messages you send through our platform</li>
                    </ul>

                <h3 className="text-xl font-medium text-green-300 mb-3">Information We Collect Automatically</h3>
                <ul className="list-disc list-inside text-gray-300 mb-4 space-y-2">
                  <li><strong>Device Information:</strong> IP address, browser type, operating system, device identifiers</li>
                  <li><strong>Usage Analytics:</strong> Feature usage, performance metrics, error logs</li>
                  <li><strong>Location:</strong> We may collect approximate location (e.g., country or region) from IP address for security and compliance; we do not collect precise GPS location</li>
                  <li><strong>Cookies and Similar Technologies:</strong> See the "Cookies and Tracking" section below</li>
                    </ul>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">How We Use Your Information (Data Use & Processing)</h2>
                <p className="text-gray-300 mb-3">We use your information to:</p>
                <ul className="list-disc list-inside text-gray-300 space-y-2">
                  <li><strong>Service Delivery:</strong> Process emails, generate AI responses, manage automation rules, and provide account features</li>
                  <li><strong>Personalization:</strong> Remember your preferences and tailor the Service to your use</li>
                  <li><strong>Security:</strong> Detect and prevent fraud, abuse, and unauthorized access; enforce our Terms</li>
                  <li><strong>Improvement:</strong> Analyze usage patterns (in aggregated form where possible), optimize performance, and develop new features</li>
                  <li><strong>Communication:</strong> Send service updates, security alerts, and support responses; with your consent, we may send marketing (you can opt out at any time)</li>
                  <li><strong>Legal & Compliance:</strong> Meet regulatory obligations and respond to lawful requests</li>
                    </ul>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">Third-Party Sharing</h2>
                <p className="text-gray-300 mb-3">
                  We do not sell your personal information for money. We may share your information only in these circumstances:
                </p>
                <ul className="list-disc list-inside text-gray-300 mb-4 space-y-2">
                  <li><strong>Service Providers:</strong> With vendors who help us operate the Service (e.g., hosting, analytics, payment processing, email delivery), under contracts that limit their use of your data</li>
                  <li><strong>Legal & Safety:</strong> When required by law, court order, or government request, or to protect the rights, safety, or property of Fikiri, our users, or the public</li>
                  <li><strong>Business Transfers:</strong> In connection with a merger, sale, or acquisition, subject to the same privacy commitments</li>
                </ul>
                <p className="text-gray-300">
                  We do not share your Gmail or email content with third parties for their advertising or marketing. Any analytics we use are configured to support service operation and improvement, not to track you across other sites for ads.
                </p>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">Gmail API Integration</h2>
                <p className="text-gray-300 mb-3">Our Service integrates with Gmail API to:</p>
                <ul className="list-disc list-inside text-gray-300 mb-4 space-y-2">
                  <li><strong>Read Emails:</strong> Process incoming messages for AI analysis and automation</li>
                  <li><strong>Send Emails:</strong> Deliver AI-generated responses on your behalf</li>
                  <li><strong>Manage Labels:</strong> Organize emails according to your automation rules</li>
                  <li><strong>Access Metadata:</strong> Retrieve email headers, timestamps, and thread information</li>
                    </ul>
                <p className="text-gray-300">
                  <strong>Your Consent:</strong> We only access your Gmail data with your explicit permission through Google's OAuth consent process.
                </p>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">Cookies and Tracking Technologies</h2>
                <p className="text-gray-300 mb-3">
                  We use cookies and similar technologies (e.g., local storage, session storage) to:
                </p>
                <ul className="list-disc list-inside text-gray-300 mb-4 space-y-2">
                  <li>Keep you signed in and maintain your session</li>
                  <li>Remember your preferences and settings</li>
                  <li>Understand how the Service is used (e.g., page views, feature usage) to improve performance</li>
                  <li>Support security (e.g., fraud detection, rate limiting)</li>
                </ul>
                <p className="text-gray-300 mb-3">
                  <strong>Your controls:</strong> You can manage or block cookies through your browser settings. 
                  Blocking certain cookies may affect sign-in and some features. We do not use third-party advertising cookies that track you across other websites.
                </p>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">Data Security</h2>
                <p className="text-gray-300 mb-3">We implement measures to protect your information:</p>
                <ul className="list-disc list-inside text-gray-300 space-y-2">
                  <li><strong>Encryption:</strong> Data in transit is protected with TLS; sensitive data at rest is encrypted where applicable</li>
                  <li><strong>Access Controls:</strong> Role-based access and authentication measures to limit who can access your data</li>
                  <li><strong>Data Minimization:</strong> We collect only what is needed for the Service</li>
                  <li><strong>Monitoring & Audits:</strong> Security monitoring and periodic assessments to address risks</li>
                    </ul>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">Your Rights and Choices (User Rights & Controls)</h2>
                <p className="text-gray-300 mb-3">You have the right to:</p>
                <ul className="list-disc list-inside text-gray-300 mb-4 space-y-2">
                  <li><strong>Access:</strong> Request a copy of the personal data we hold about you</li>
                  <li><strong>Correction:</strong> Update or correct inaccurate information (e.g., via account settings or by contacting us)</li>
                  <li><strong>Deletion:</strong> Request deletion of your account and associated data</li>
                  <li><strong>Portability:</strong> Receive your data in a machine-readable format where feasible</li>
                  <li><strong>Opt-out:</strong> Unsubscribe from marketing emails at any time (e.g., via link in emails or account preferences)</li>
                  <li><strong>Restrict or Object:</strong> In certain jurisdictions, you may have the right to restrict processing or object to certain uses of your data</li>
                    </ul>
                <p className="text-gray-300">
                  To exercise these rights, contact us at the email below. We will respond within the timeframes required by applicable law. 
                  If you are in the European Economic Area (EEA), UK, or California, you may have additional rights under GDPR, UK GDPR, or CCPA (e.g., right to know, right to delete, right to non-discrimination). We will honor those rights where they apply.
                </p>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">Policy Updates</h2>
                <p className="text-gray-300">
                  We may update this Privacy Policy from time to time. When we do, we will change the "Last Updated" date at the top and, for material changes, we will notify you by email (to the address on your account) and/or by a prominent notice on our website or in the Service. Your continued use of the Service after the updated policy is posted constitutes acceptance of the changes. We encourage you to review this page periodically.
                </p>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">Contact Information</h2>
                <p className="text-gray-300">
                  If you have questions about this Privacy Policy or our data practices, please contact us:
                </p>
                <div className="bg-gray-700 p-4 rounded-lg mt-4">
                  <p className="text-gray-300">
                    <strong>Email:</strong> privacy@fikirisolutions.com<br />
                    <strong>Address:</strong> Fikiri Solutions, Privacy Department<br />
                    <strong>Website:</strong> <a href="/contact" className="text-brand-primary hover:text-muted-foreground">https://fikirisolutions.com/contact</a>
                  </p>
                </div>
              </section>

              <div className="border-t border-gray-600 pt-6 mt-8">
                <p className="text-gray-400 text-sm text-center">
                  <em>This Privacy Policy is effective as of the date listed above and applies to all users of Fikiri Solutions.</em>
                </p>
                <p className="text-gray-500 text-xs text-center mt-3">
                  This policy is for informational purposes only and does not constitute legal advice. If you have questions about your rights or our practices, please contact us or consult your own legal advisor.
                </p>
              </div>
            </div>
          </div>
            </div>
      </div>
      <PublicChatbotWidget />
    </>
    </RadiantLayout>
  );
};

export { PrivacyPolicy };
export default PrivacyPolicy;
