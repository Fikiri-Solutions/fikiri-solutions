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
          <meta name="description" content="Consent to receive SMS text messages from Fikiri Solutions LLC. Opt-in language and proof of consent for toll-free verification." />
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
                SMS &amp; Text Message Opt-In
              </h1>
              <p className="text-center text-gray-400 text-sm mb-6">Fikiri Solutions LLC – consent to receive SMS text messages</p>

              {/* Prominent consent statement (Error 30513: clear language requesting consent for SMS) */}
              <section className="mb-8 rounded-lg border-2 border-brand-primary/50 bg-gray-900/80 p-6">
                <h2 className="text-lg font-semibold text-white mb-3">Consent to receive SMS text messages</h2>
                <p className="text-white text-lg leading-relaxed">
                  Users consent by checking a box that states:
                </p>
                <p className="mt-3 text-xl font-semibold text-brand-primary leading-snug">
                  &ldquo;{SMS_CONSENT.checkboxLabel}&rdquo;
                </p>
                <p className="mt-4 text-gray-400 text-sm">
                  This consent is collected only via our web form (signup and account settings). It is separate from our Privacy Policy and Terms of Service. The checkbox is unchecked by default.
                </p>
              </section>

              <section className="mb-8">
                <h2 className="text-xl font-semibold text-white mb-4">Where we collect consent</h2>
                <p className="text-gray-300 leading-relaxed mb-4">
                  We collect consent for <strong>SMS text messages</strong> via a web form in two places. The consent checkbox is <strong>unchecked by default</strong>.
                </p>
                <ul className="list-disc list-inside text-gray-300 space-y-2 mb-4">
                  <li><Link to="/signup" className="text-brand-primary hover:underline">{siteUrl}/signup</Link> – Signup form: optional mobile number and consent checkbox (unchecked by default).</li>
                  <li>Account Settings → Profile – Optional phone number and consent checkbox (unchecked by default).</li>
                </ul>
                <p className="text-gray-300 leading-relaxed">
                  We send SMS only after the user enters a mobile number and checks the consent box. No messages are sent without this explicit opt-in.
                </p>
              </section>

              <section className="mb-8 rounded-lg border border-gray-600 bg-gray-900/50 p-6">
                <h2 className="text-xl font-semibold text-white mb-4">Exact language on the opt-in form</h2>
                <p className="text-gray-400 text-sm mb-2 uppercase tracking-wide">Disclosure above the checkbox</p>
                <p className="text-gray-300 leading-relaxed mb-6">
                  {SMS_CONSENT.upfrontDisclosure}
                </p>
                <p className="text-gray-400 text-sm mb-2 uppercase tracking-wide">Checkbox label (user must check to opt in)</p>
                <p className="text-white font-medium text-base">
                  {SMS_CONSENT.checkboxLabel}
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
