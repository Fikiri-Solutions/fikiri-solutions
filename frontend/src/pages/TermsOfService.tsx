import React from 'react';
import { Helmet } from 'react-helmet-async';
import { RadiantLayout } from '../components/radiant';

const TermsOfService: React.FC = () => {
  return (
    <RadiantLayout>
    <>
      <Helmet>
        <title>Terms of Service - Fikiri Solutions</title>
        <meta name="description" content="Terms of Service for Fikiri Solutions AI-powered Gmail automation platform" />
      </Helmet>
      
      <div className="min-h-screen bg-gray-900 text-white">
        <div className="container mx-auto px-4 py-8 max-w-4xl">
          <div className="bg-gray-800 rounded-lg p-8 shadow-xl">
            <h1 className="text-4xl font-bold text-center mb-8 text-brand-primary">
                  Terms of Service
                </h1>
            
            <div className="prose prose-invert max-w-none">
              <p className="text-gray-300 mb-6">
                <strong>Effective Date:</strong> October 18, 2025<br />
                <strong>Last Updated:</strong> October 18, 2025
              </p>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">Agreement to Terms</h2>
                <p className="text-gray-300 leading-relaxed">
                  By accessing or using Fikiri Solutions ("Service") at 
                  <a href="https://fikirisolutions.com" className="text-brand-primary hover:text-muted-foreground"> https://fikirisolutions.com</a>, 
                  you agree to be bound by these Terms of Service ("Terms"). If you disagree with any part of these terms, 
                  you may not access the Service.
                </p>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">Description of Service</h2>
                <p className="text-gray-300 mb-3">Fikiri Solutions is an AI-powered Gmail automation platform that:</p>
                <ul className="list-disc list-inside text-gray-300 space-y-2">
                  <li><strong>Processes Emails:</strong> Analyzes incoming messages using artificial intelligence</li>
                  <li><strong>Generates Responses:</strong> Creates intelligent, context-aware email replies</li>
                  <li><strong>Manages Automation:</strong> Sets up rules and workflows for email management</li>
                  <li><strong>Provides Analytics:</strong> Offers insights into email patterns and performance</li>
                </ul>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">Gmail Integration and Permissions</h2>
                
                <h3 className="text-xl font-medium text-green-300 mb-3">OAuth Consent</h3>
                <p className="text-gray-300 mb-3">
                  Our Service integrates with Gmail through Google's OAuth 2.0 system. By connecting your Gmail account, you grant us permission to:
                </p>
                <ul className="list-disc list-inside text-gray-300 mb-4 space-y-2">
                  <li><strong>Read Emails:</strong> Access messages for AI processing and automation</li>
                  <li><strong>Send Emails:</strong> Deliver AI-generated responses on your behalf</li>
                  <li><strong>Manage Labels:</strong> Organize emails according to your automation rules</li>
                  <li><strong>Access Metadata:</strong> Retrieve email headers, timestamps, and thread information</li>
                    </ul>

                <h3 className="text-xl font-medium text-green-300 mb-3">Data Usage</h3>
                <ul className="list-disc list-inside text-gray-300 space-y-2">
                  <li>We only access Gmail data necessary for Service functionality</li>
                  <li>We do not read, store, or process emails beyond what's required for automation</li>
                  <li>You can revoke Gmail access at any time through your Google account settings</li>
                    </ul>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">Acceptable Use Policy</h2>
                
                <h3 className="text-xl font-medium text-green-300 mb-3">Permitted Uses</h3>
                <p className="text-gray-300 mb-3">You may use our Service to:</p>
                <ul className="list-disc list-inside text-gray-300 mb-4 space-y-2">
                  <li>Automate legitimate business email communications</li>
                  <li>Improve email productivity and response times</li>
                  <li>Organize and manage email workflows</li>
                  <li>Generate appropriate, professional email responses</li>
                    </ul>

                <h3 className="text-xl font-medium text-green-300 mb-3">Prohibited Uses</h3>
                <p className="text-gray-300 mb-3">You may not use our Service to:</p>
                <ul className="list-disc list-inside text-gray-300 space-y-2">
                  <li><strong>Spam:</strong> Send unsolicited, bulk, or promotional emails</li>
                  <li><strong>Harassment:</strong> Send threatening, abusive, or inappropriate content</li>
                  <li><strong>Illegal Activities:</strong> Violate any applicable laws or regulations</li>
                  <li><strong>Impersonation:</strong> Misrepresent your identity or affiliation</li>
                  <li><strong>Malware:</strong> Distribute viruses, malware, or harmful code</li>
                  <li><strong>Circumvention:</strong> Attempt to bypass security measures or access controls</li>
                    </ul>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">Google API Services Compliance</h2>
                <p className="text-gray-300 mb-3">Our Service complies with Google API Services User Data Policy, including:</p>
                <ul className="list-disc list-inside text-gray-300 space-y-2">
                  <li><strong>Data Usage:</strong> Limited to providing or improving user-facing features</li>
                  <li><strong>Data Transfer:</strong> No selling or transferring user data to third parties</li>
                  <li><strong>Security:</strong> Implementing appropriate security measures</li>
                  <li><strong>User Consent:</strong> Obtaining explicit user consent for data access</li>
                </ul>
              </section>

              <section className="mb-8">
                <h2 className="text-2xl font-semibold text-muted-foreground mb-4">Contact Information</h2>
                <p className="text-gray-300">
                  For questions about these Terms, please contact us:
                </p>
                <div className="bg-gray-700 p-4 rounded-lg mt-4">
                  <p className="text-gray-300">
                    <strong>Email:</strong> legal@fikirisolutions.com<br />
                    <strong>Address:</strong> Fikiri Solutions, Legal Department<br />
                    <strong>Website:</strong> <a href="/contact" className="text-brand-primary hover:text-muted-foreground">https://fikirisolutions.com/contact</a>
                  </p>
                </div>
              </section>

              <div className="border-t border-gray-600 pt-6 mt-8">
                <p className="text-gray-400 text-sm text-center">
                  <em>These Terms of Service are effective as of the date listed above and apply to all users of Fikiri Solutions.</em>
                </p>
              </div>
                  </div>
                </div>
              </div>
      </div>
    </>
    </RadiantLayout>
  );
};

export { TermsOfService };
export default TermsOfService;