import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Home, FileText } from 'lucide-react';
import { RadiantLayout } from '../components/radiant';
import { MarketingChatWidget } from '../components/MarketingChatWidget';
import { useAuth } from '../contexts/AuthContext';
import { PageMeta } from '../components/PageMeta';

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
      <PageMeta route="/privacy" />
      
      <div className="min-h-screen bg-gray-900 font-serif text-white">
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
                <strong>Last Updated:</strong> September 28, 2026
              </p>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">Introduction</h2>
                <p className="text-gray-300 leading-relaxed mb-4">
                  Fikiri Solutions LLC, doing business as Fikiri Solutions (&quot;we,&quot; &quot;our,&quot; or &quot;us&quot;), is committed to protecting your privacy.
                  This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you visit or use our
                  websites and AI-powered business automation platform at{' '}
                  <a href="https://fikirisolutions.com" className="text-brand-primary hover:text-muted-foreground">https://fikirisolutions.com</a>{' '}
                  (the &quot;Service&quot;).
                </p>
                <p className="text-gray-300 leading-relaxed">
                  <strong>In plain terms:</strong> We collect information so we can operate our software and make your experience with
                  Fikiri better—personalization, reliability, security, and product improvement. We do <strong>not</strong> sell your
                  personal information. We do <strong>not</strong> sell Google or Gmail user data. We use industry-standard safeguards
                  designed to keep your data secure while we provide the Service.
                </p>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">Information We Collect</h2>

                <h3 className="text-xl font-medium text-green-300 mb-3">Information You Provide</h3>
                <ul className="list-disc list-inside text-gray-300 mb-4 space-y-2">
                  <li><strong>Account Information:</strong> Email address, name, password, and profile preferences</li>
                  <li><strong>Contact and intake forms:</strong> Details you submit when you contact us or request a demo (for example, name, email, company, and message content)</li>
                  <li><strong>Billing information:</strong> Payment and subscription details processed by our payment provider (we do not store full payment card numbers on our servers when Stripe or a similar processor handles checkout)</li>
                  <li><strong>Gmail and Google account data (when you connect Google):</strong> With your explicit consent through Google&apos;s OAuth screens, we may access categories of data needed to run the Service, including your Google Account email address; basic profile details you have made available to the app (such as name or profile photo, depending on what you grant); email message content, headers, metadata, and thread identifiers; labels and organization data; and permissions needed to read, send, modify, or organize mail in Gmail as described at connect time. We only request the scopes necessary for the features you use.</li>
                  <li><strong>Communications:</strong> Messages you send through the Service, support channels, or our site chat</li>
                  <li><strong>Marketing preferences:</strong> Whether you opt in to product or marketing emails (separate from required service messages)</li>
                </ul>

                <h3 className="text-xl font-medium text-green-300 mb-3">Information We Collect Automatically</h3>
                <ul className="list-disc list-inside text-gray-300 mb-4 space-y-2">
                  <li><strong>Device and log information:</strong> IP address, browser type, operating system, device identifiers, and diagnostic logs</li>
                  <li><strong>Usage analytics:</strong> Pages and features used, performance metrics, and error reports—so we can improve reliability and UX</li>
                  <li><strong>Approximate location:</strong> Country or region inferred from IP for security and compliance; we do not collect precise GPS location</li>
                  <li><strong>Cookies and similar technologies:</strong> See the &quot;Cookies and Tracking Technologies&quot; section below</li>
                </ul>

                <h3 className="text-xl font-medium text-green-300 mb-3">Sources</h3>
                <p className="text-gray-300 mb-3">
                  We collect personal information from you directly, automatically when you use the Service, and from services you connect
                  (such as Google). We may also receive limited information from service providers that help us host, secure, bill, or
                  analyze the Service.
                </p>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">How We Use Your Information</h2>
                <p className="text-gray-300 mb-3">
                  We use your information to provide, personalize, secure, and improve the Service—not to sell it. Specifically, we use it to:
                </p>
                <ul className="list-disc list-inside text-gray-300 space-y-2">
                  <li><strong>Deliver the Service:</strong> Process emails and workflows you configure, generate AI-assisted drafts and automations, manage CRM and related features, and operate your account</li>
                  <li><strong>Improve your experience:</strong> Remember preferences, tailor in-app behavior, understand which features help (or confuse) users, fix bugs, and build better product UX</li>
                  <li><strong>Security and integrity:</strong> Detect and prevent fraud, abuse, and unauthorized access; enforce our Terms</li>
                  <li><strong>Communicate with you:</strong> Send service updates, security alerts, and support responses; with your separate consent where required, we may send Fikiri product or marketing emails (you can opt out anytime). We do not use Google user data to send third-party promotional or interest-based ads on our behalf</li>
                  <li><strong>Legal and compliance:</strong> Meet regulatory obligations and respond to lawful requests</li>
                </ul>
                <p className="text-gray-300 mt-4">
                  <strong>AI features:</strong> When you use AI-assisted features, we may process relevant content (for example, email text or prompts you provide) to generate outputs for you. That processing is to operate those features for your account. We do not sell that content, and we do not use Google user data to train generalized foundation models for unrelated purposes.
                </p>
                <p className="text-gray-300 mt-4">
                  <strong>Google user data — limited use:</strong> We use Google user data only to provide and improve user-facing features of the Service (for example, reading and sending mail as you direct, inbox organization, and security). We do not use Google user data for targeted advertising, selling personal information, sale to data brokers, providing data to information resellers, creditworthiness or lending decisions, user retargeting, interest-based advertising, or building standalone contact databases unrelated to operating the Service for you. We do not use Google user data to train or improve generalized or foundation machine-learning models for unrelated purposes; processing supports the Service you signed up for (such as drafting or classifying your messages in context), not third-party ad profiling.
                </p>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">How We Share Information</h2>
                <p className="text-gray-300 mb-3">
                  <strong>We do not sell your personal information.</strong> We do not sell Google user data. We share information only as needed to run the Service, including:
                </p>
                <ul className="list-disc list-inside text-gray-300 mb-4 space-y-2">
                  <li><strong>Service providers (subprocessors):</strong> Vendors that host infrastructure, databases, payments, transactional email, analytics, or security on our behalf (for example, cloud hosting, application hosting, payment processing such as Stripe, and first-party site analytics such as Vercel Analytics). They may process data only to provide services to us and must protect it appropriately.</li>
                  <li><strong>Legal and safety:</strong> When required by law, court order, or government request, or to protect the rights, safety, or property of Fikiri, our users, or the public</li>
                  <li><strong>Business transfers:</strong> In connection with a merger, financing, or acquisition, subject to ongoing privacy commitments</li>
                  <li><strong>Professional advisors:</strong> Lawyers, auditors, or insurers as needed in the ordinary course of business</li>
                </ul>
                <p className="text-gray-300 mb-3">
                  We do not transfer or disclose Google user data or Gmail content to third parties for their advertising, marketing, data brokerage, or the prohibited purposes listed under &quot;Google user data — limited use&quot; above. Subprocessors receive data only as needed to host and run the Service, not to monetize your mailbox content.
                </p>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">Gmail API Integration</h2>
                <p className="text-gray-300 mb-3">Our Service integrates with Gmail API to:</p>
                <ul className="list-disc list-inside text-gray-300 mb-4 space-y-2">
                  <li><strong>Read Emails:</strong> Process incoming messages for analysis and automation you enable</li>
                  <li><strong>Send Emails:</strong> Deliver responses and outbound messages you initiate or configure</li>
                  <li><strong>Manage Labels:</strong> Organize emails according to your automation rules</li>
                  <li><strong>Access Metadata:</strong> Retrieve email headers, timestamps, and thread information needed for those features</li>
                    </ul>
                <p className="text-gray-300 mb-3">
                  <strong>Your Consent:</strong> We only access your Gmail data with your explicit permission through Google&apos;s OAuth consent process. You can review or revoke the connection anytime in your Google Account (Third-party access) and through in-app disconnect options where available.
                </p>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">Retention and Deletion</h2>
                <p className="text-gray-300 mb-3">
                  We retain personal information, including Google OAuth tokens and data processed from Gmail, for as long as your account is active and as needed to provide the Service, unless a longer period is required or permitted by law (for example, security logs or billing records).
                </p>
                <ul className="list-disc list-inside text-gray-300 mb-4 space-y-2">
                  <li><strong>While you use the Service:</strong> We keep connection credentials (for example, encrypted OAuth tokens) and operational copies of data needed to run automations and show you results.</li>
                  <li><strong>When you disconnect Google:</strong> We stop new access using that connection; we may retain limited records as described in your account settings and as needed for security or legal compliance.</li>
                  <li><strong>Deletion requests:</strong> You may request deletion of your account and associated data by contacting <a href="mailto:info@fikirisolutions.com" className="text-brand-primary hover:text-muted-foreground">info@fikirisolutions.com</a> and, where offered, through in-app privacy or account tools. When retention periods expire or after a completed deletion request (subject to legal holds), we delete or irreversibly anonymize data in line with our technical and organizational capabilities.</li>
                </ul>
                <p className="text-gray-300">
                  If we materially change how we collect, use, store, or share Google user data, we will update this Privacy Policy and notify you as described under &quot;Policy Updates&quot; below.
                </p>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">Cookies and Tracking Technologies</h2>
                <p className="text-gray-300 mb-3">
                  We use cookies and similar technologies (for example, local storage and session storage) for:
                </p>
                <ul className="list-disc list-inside text-gray-300 mb-4 space-y-2">
                  <li><strong>Essential / functional:</strong> Keep you signed in, maintain session security, and remember preferences needed for the Service to work</li>
                  <li><strong>Analytics / performance:</strong> Understand page views, feature usage, and performance (including tools such as Vercel Analytics and Speed Insights) so we can improve the product experience</li>
                  <li><strong>Security:</strong> Support fraud detection, rate limiting, and abuse prevention</li>
                </ul>
                <p className="text-gray-300 mb-3">
                  <strong>Your controls:</strong> You can manage or block cookies through your browser settings. Blocking certain cookies may affect sign-in and some features.
                  Signed-in users may also manage related privacy preferences in{' '}
                  <a href="/privacy-settings" className="text-brand-primary hover:text-muted-foreground">Privacy Settings</a> where available.
                  We do not use third-party advertising cookies that track you across other websites, and we do not sell data collected via cookies.
                </p>
                <p className="text-gray-300 mb-3">
                  <strong>Do Not Track:</strong> Some browsers send a &quot;Do Not Track&quot; signal. There is no consistent industry standard for responding to these signals; we currently do not alter our practices solely based on a Do Not Track signal. You can still use the controls above.
                </p>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">Data Security</h2>
                <p className="text-gray-300 mb-3">We implement administrative, technical, and organizational measures designed to protect Google user data and other personal information, including:</p>
                <ul className="list-disc list-inside text-gray-300 space-y-2">
                  <li><strong>Encryption:</strong> Data in transit is protected with TLS; sensitive credentials (including OAuth tokens) are stored encrypted where our systems support encryption at rest</li>
                  <li><strong>Access Controls:</strong> Authentication, authorization, and least-privilege practices to limit access to production systems and customer data</li>
                  <li><strong>Data Minimization:</strong> We collect and retain only what is needed to provide and improve the Service</li>
                  <li><strong>Monitoring &amp; Reviews:</strong> Security monitoring and periodic review to address risks</li>
                </ul>
                <p className="text-gray-300 mt-4">
                  No method of transmission or storage is completely secure. We work to protect your information, but we cannot guarantee absolute security.
                </p>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">Children&apos;s Privacy</h2>
                <p className="text-gray-300">
                  The Service is not directed to children under 18, and we do not knowingly collect personal information from children under 18.
                  If you believe we have collected information from a child, contact us and we will take steps to delete it as required by law.
                </p>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">International Data Transfers</h2>
                <p className="text-gray-300">
                  We are based in the United States and may use service providers that process data in the United States or other countries.
                  If you access the Service from outside the U.S., your information may be transferred to and processed in locations where privacy laws may differ from those in your jurisdiction.
                  We take steps designed to protect information consistent with this Privacy Policy.
                </p>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">Your Rights and Choices</h2>
                <p className="text-gray-300 mb-3">Depending on where you live, you may have the right to:</p>
                <ul className="list-disc list-inside text-gray-300 mb-4 space-y-2">
                  <li><strong>Access:</strong> Request a copy of the personal data we hold about you</li>
                  <li><strong>Correction:</strong> Update or correct inaccurate information (for example via account settings or by contacting us)</li>
                  <li><strong>Deletion:</strong> Request deletion of your account and associated data</li>
                  <li><strong>Portability:</strong> Receive your data in a machine-readable format where feasible</li>
                  <li><strong>Opt out of marketing:</strong> Unsubscribe from marketing emails at any time (service and security messages may still be sent)</li>
                  <li><strong>Restrict or object:</strong> In certain jurisdictions, restrict processing or object to certain uses</li>
                </ul>
                <p className="text-gray-300">
                  To exercise these rights, contact us at the email below. We will respond within the timeframes required by applicable law.
                  If you are in the European Economic Area (EEA), UK, or California, you may have additional rights under GDPR, UK GDPR, or CCPA/CPRA (for example, right to know, delete, and non-discrimination). We will honor those rights where they apply.
                  Because we do not sell personal information, a &quot;Do Not Sell&quot; request is not needed for a sale we do not perform; contact us if you have questions about sharing with service providers.
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
                    <strong>Email:</strong> info@fikirisolutions.com<br />
                    <strong>Address:</strong> Fikiri Solutions LLC, Privacy Department<br />
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
      <MarketingChatWidget />
    </>
    </RadiantLayout>
  );
};

export { PrivacyPolicy };
export default PrivacyPolicy;
