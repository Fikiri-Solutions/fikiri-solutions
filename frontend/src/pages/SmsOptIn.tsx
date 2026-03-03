import React from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Home, MessageSquare } from 'lucide-react';
import { RadiantLayout } from '../components/radiant';
import { SMS_CONSENT } from '../constants/smsConsent';

/**
 * Public SMS opt-in disclosure page for toll-free verification (CTIA/Twilio).
 * This URL is submitted as "Proof of consent (opt-in) collected." It shows the
 * exact express-consent workflow and opt-in language used at point of collection.
 * Errors 30446 (express consent) and 30513 (unclear language) are addressed by
 * documenting voluntary, informed consent with explicit SMS/text language.
 */
const SmsOptIn: React.FC = () => {
  const navigate = useNavigate();
  const siteUrl = 'https://fikirisolutions.com';

  return (
    <RadiantLayout>
      <>
        <Helmet>
          <title>SMS Opt-In - Fikiri Solutions</title>
          <meta name="description" content="SMS opt-in process and express consent disclosure for Fikiri Solutions account and security text messages (CTIA/TCPA compliant)" />
        </Helmet>

        <div className="min-h-screen bg-gray-900 text-white">
          <div className="container mx-auto px-4 py-8 max-w-4xl">
            <div className="mb-6 flex items-center gap-4">
              <button
                onClick={() => navigate(-1)}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-300 hover:text-white bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
              >
                <ArrowLeft className="h-4 w-4" />
                Back
              </button>
              <button
                onClick={() => navigate('/')}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-300 hover:text-white bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
              >
                <Home className="h-4 w-4" />
                Home
              </button>
            </div>

            <div className="bg-gray-800 rounded-lg p-8 shadow-xl">
              <h1 className="text-3xl font-bold text-center mb-2 text-brand-primary flex items-center justify-center gap-2">
                <MessageSquare className="h-8 w-8" />
                SMS Opt-In &amp; Express Consent
              </h1>
              <p className="text-center text-gray-400 text-sm mb-8">Fikiri Solutions LLC – Account &amp; security text messages only (transactional)</p>

              <section className="mb-8">
                <h2 className="text-xl font-semibold text-white mb-4">Express consent workflow</h2>
                <p className="text-gray-300 leading-relaxed mb-4">
                  We collect <strong>express consent</strong> for text messages (SMS) via a web form in two places. Consent is voluntary, informed, and requires an intentional action (unchecked-by-default checkbox + optional mobile number).
                </p>
                <ul className="list-disc list-inside text-gray-300 space-y-2 mb-4">
                  <li><Link to="/signup" className="text-brand-primary hover:underline">{siteUrl}/signup</Link> – During account registration: optional mobile number field and a consent checkbox that is <strong>unchecked by default</strong>.</li>
                  <li>Account Settings (after login) – Profile tab: optional phone number and a consent checkbox that is <strong>unchecked by default</strong> to enable SMS notifications.</li>
                </ul>
                <p className="text-gray-300 leading-relaxed">
                  The user must voluntarily enter their mobile number and <strong>check the box</strong> to opt in. We do not send any SMS until both the number and consent are provided.
                </p>
              </section>

              <section className="mb-8 rounded-lg border border-gray-600 bg-gray-900/50 p-6">
                <h2 className="text-xl font-semibold text-white mb-4">Exact opt-in language (shown at point of collection)</h2>
                <p className="text-gray-400 text-sm mb-2 uppercase tracking-wide">Upfront disclosure (above phone field and checkbox)</p>
                <p className="text-gray-300 leading-relaxed mb-6 whitespace-pre-line">
                  {SMS_CONSENT.upfrontDisclosure}
                </p>
                <p className="text-gray-400 text-sm mb-2 uppercase tracking-wide">Consent checkbox label (explicit request for text messages/SMS)</p>
                <p className="text-gray-300 leading-relaxed font-medium">
                  &ldquo;{SMS_CONSENT.checkboxLabel}&rdquo;
                </p>
              </section>

              <section className="mb-8">
                <h2 className="text-xl font-semibold text-white mb-4">Use case</h2>
                <p className="text-gray-300 leading-relaxed">
                  This toll-free number is used strictly for <strong>transactional messaging</strong>: (1) account verification codes (2FA), (2) login and security alerts, (3) system-generated account status notifications. It is not used for marketing, promotional, or advertising messages.
                </p>
              </section>

              <section className="flex flex-wrap gap-4 text-sm">
                <Link to="/signup" className="text-brand-primary hover:underline">Sign up (opt-in form)</Link>
                <a href={`${siteUrl}/privacy`} className="text-brand-primary hover:underline">Privacy Policy</a>
                <a href={`${siteUrl}/terms`} className="text-brand-primary hover:underline">Terms of Service</a>
              </section>
            </div>
          </div>
        </div>
      </>
    </RadiantLayout>
  );
};

export default SmsOptIn;
