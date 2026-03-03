import React from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Home, MessageSquare } from 'lucide-react';
import { RadiantLayout } from '../components/radiant';

/**
 * Public SMS opt-in disclosure page for toll-free verification (CTIA/Twilio).
 * Submit this URL as "Proof of consent (opt-in) collected" so reviewers see
 * the exact opt-in language and where consent is collected.
 */
const SmsOptIn: React.FC = () => {
  const navigate = useNavigate();
  const siteUrl = 'https://fikirisolutions.com';

  return (
    <RadiantLayout>
      <>
        <Helmet>
          <title>SMS Opt-In - Fikiri Solutions</title>
          <meta name="description" content="SMS opt-in process and consent disclosure for Fikiri Solutions account and security notifications" />
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
                SMS Opt-In
              </h1>
              <p className="text-center text-gray-400 text-sm mb-8">Fikiri Solutions LLC – Account &amp; security notifications only</p>

              <section className="mb-8">
                <h2 className="text-xl font-semibold text-white mb-4">How we collect consent</h2>
                <p className="text-gray-300 leading-relaxed mb-4">
                  Consent to receive SMS messages is collected through a <strong>web form</strong> in two places:
                </p>
                <ul className="list-disc list-inside text-gray-300 space-y-2 mb-4">
                  <li><Link to="/signup" className="text-brand-primary hover:underline">{siteUrl}/signup</Link> – during account registration (optional phone field and unchecked-by-default consent checkbox)</li>
                  <li>Account Settings (after login) – Profile tab: optional phone number and unchecked-by-default checkbox to enable SMS notifications</li>
                </ul>
                <p className="text-gray-300 leading-relaxed">
                  The checkbox is <strong>unchecked by default</strong>. Users must voluntarily enter their mobile number and check the box to opt in.
                </p>
              </section>

              <section className="mb-8 rounded-lg border border-gray-600 bg-gray-900/50 p-6">
                <h2 className="text-xl font-semibold text-white mb-4">Upfront disclosure (shown at point of collection)</h2>
                <p className="text-gray-300 leading-relaxed mb-4">
                  Fikiri Solutions LLC may send you <strong>account and security-related text messages only</strong>—for example, verification codes, login and security alerts, and account status notifications. Message frequency varies as needed, typically under 10 per month. No marketing or promotional messages will be sent.
                </p>
                <p className="text-gray-300 leading-relaxed mb-4">
                  Reply <strong>STOP</strong> to opt out at any time; reply <strong>HELP</strong> for help. Message and data rates may apply. Consent is not required to use our services or make a purchase.
                </p>
                <p className="text-gray-400 text-sm">
                  Checkbox label: &ldquo;I agree to receive account and security-related SMS messages from Fikiri Solutions LLC as described above. Reply STOP to opt out. Reply HELP for help. Msg &amp; data rates may apply. Consent is not a condition of purchase.&rdquo;
                </p>
              </section>

              <section className="mb-8">
                <h2 className="text-xl font-semibold text-white mb-4">Use case</h2>
                <p className="text-gray-300 leading-relaxed">
                  This toll-free number is used strictly for <strong>transactional messaging</strong>: (1) account verification codes, (2) login and security alerts, (3) system-generated account status notifications. Not used for marketing, promotional, or advertising messages.
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
