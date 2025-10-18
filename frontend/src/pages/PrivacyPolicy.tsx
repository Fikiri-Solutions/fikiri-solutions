import React from 'react';
import { Helmet } from 'react-helmet-async';

const PrivacyPolicy: React.FC = () => {
  return (
    <>
      <Helmet>
        <title>Privacy Policy - Fikiri Solutions</title>
        <meta name="description" content="Privacy Policy for Fikiri Solutions AI-powered Gmail automation platform" />
      </Helmet>
      
      <div className="min-h-screen bg-gray-900 text-white">
        <div className="container mx-auto px-4 py-8 max-w-4xl">
          <div className="bg-gray-800 rounded-lg p-8 shadow-xl">
            <h1 className="text-4xl font-bold text-center mb-8 text-blue-400">
                  Privacy Policy
                </h1>
            
            <div className="prose prose-invert max-w-none">
              <p className="text-gray-300 mb-6">
                <strong>Effective Date:</strong> October 18, 2025<br />
                <strong>Last Updated:</strong> October 18, 2025
              </p>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-blue-300 mb-4">Introduction</h2>
                <p className="text-gray-300 leading-relaxed">
                  Fikiri Solutions ("we," "our," or "us") is committed to protecting your privacy. 
                  This Privacy Policy explains how we collect, use, disclose, and safeguard your 
                  information when you use our AI-powered Gmail automation platform at 
                  <a href="https://fikirisolutions.com" className="text-blue-400 hover:text-blue-300"> https://fikirisolutions.com</a> (the "Service").
                </p>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-blue-300 mb-4">Information We Collect</h2>
                
                <h3 className="text-xl font-medium text-green-300 mb-3">Information You Provide</h3>
                <ul className="list-disc list-inside text-gray-300 mb-4 space-y-2">
                  <li><strong>Account Information:</strong> Email address, name, and password</li>
                  <li><strong>Gmail Data:</strong> Emails, contacts, and calendar information (with your explicit consent)</li>
                  <li><strong>Usage Data:</strong> How you interact with our Service</li>
                  <li><strong>Communication Data:</strong> Messages you send through our platform</li>
                    </ul>

                <h3 className="text-xl font-medium text-green-300 mb-3">Information We Collect Automatically</h3>
                <ul className="list-disc list-inside text-gray-300 mb-4 space-y-2">
                  <li><strong>Device Information:</strong> IP address, browser type, operating system</li>
                  <li><strong>Usage Analytics:</strong> Feature usage, performance metrics, error logs</li>
                  <li><strong>Cookies and Tracking:</strong> Session data, preferences, authentication tokens</li>
                    </ul>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-blue-300 mb-4">How We Use Your Information</h2>
                <p className="text-gray-300 mb-3">We use your information to:</p>
                <ul className="list-disc list-inside text-gray-300 space-y-2">
                  <li><strong>Provide Services:</strong> Process emails, generate AI responses, manage automation rules</li>
                  <li><strong>Improve Platform:</strong> Analyze usage patterns, optimize performance, develop new features</li>
                  <li><strong>Communicate:</strong> Send service updates, security alerts, and support responses</li>
                  <li><strong>Comply with Legal Requirements:</strong> Meet regulatory obligations and protect user rights</li>
                    </ul>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-blue-300 mb-4">Gmail API Integration</h2>
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
                <h2 className="text-2xl font-semibold text-blue-300 mb-4">Data Security</h2>
                <p className="text-gray-300 mb-3">We implement industry-standard security measures:</p>
                <ul className="list-disc list-inside text-gray-300 space-y-2">
                  <li><strong>Encryption:</strong> All data transmitted using TLS 1.3 encryption</li>
                  <li><strong>Access Controls:</strong> Role-based permissions and multi-factor authentication</li>
                  <li><strong>Data Minimization:</strong> We only collect data necessary for service functionality</li>
                  <li><strong>Regular Audits:</strong> Security assessments and vulnerability testing</li>
                    </ul>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-blue-300 mb-4">Your Rights and Choices</h2>
                <p className="text-gray-300 mb-3">You have the right to:</p>
                <ul className="list-disc list-inside text-gray-300 space-y-2">
                  <li><strong>Access:</strong> Request copies of your personal data</li>
                  <li><strong>Correction:</strong> Update or correct inaccurate information</li>
                  <li><strong>Deletion:</strong> Request deletion of your account and data</li>
                  <li><strong>Portability:</strong> Export your data in a machine-readable format</li>
                  <li><strong>Opt-out:</strong> Unsubscribe from marketing communications</li>
                    </ul>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-blue-300 mb-4">Contact Information</h2>
                <p className="text-gray-300">
                  If you have questions about this Privacy Policy or our data practices, please contact us:
                </p>
                <div className="bg-gray-700 p-4 rounded-lg mt-4">
                  <p className="text-gray-300">
                    <strong>Email:</strong> privacy@fikirisolutions.com<br />
                    <strong>Address:</strong> Fikiri Solutions, Privacy Department<br />
                    <strong>Website:</strong> <a href="/contact" className="text-blue-400 hover:text-blue-300">https://fikirisolutions.com/contact</a>
                  </p>
                </div>
              </section>

              <div className="border-t border-gray-600 pt-6 mt-8">
                <p className="text-gray-400 text-sm text-center">
                  <em>This Privacy Policy is effective as of the date listed above and applies to all users of Fikiri Solutions.</em>
                </p>
              </div>
            </div>
          </div>
            </div>
      </div>
    </>
  );
};

export default PrivacyPolicy;