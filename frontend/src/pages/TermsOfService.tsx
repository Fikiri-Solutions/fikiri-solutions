import React from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { 
  FileText, 
  Shield, 
  Users, 
  Lock, 
  AlertTriangle,
  CheckCircle,
  ArrowLeft,
  Calendar,
  Mail,
  Phone
} from 'lucide-react';
import { FikiriLogo } from '../components/FikiriLogo';

const TermsOfService: React.FC = () => {
  const lastUpdated = "December 2024";

  return (
    <div className="min-h-screen bg-brand-background dark:bg-gray-900">
      {/* Header */}
      <motion.div 
        className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Link to="/" className="flex items-center">
                <FikiriLogo size="md" variant="default" />
              </Link>
              <div>
                <h1 className="text-2xl font-bold text-brand-text dark:text-white font-serif">
                  Terms of Service
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Last updated: {lastUpdated}
                </p>
              </div>
            </div>
            <Link
              to="/"
              className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Dashboard
            </Link>
          </div>
        </div>
      </motion.div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <motion.div
          className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 p-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          {/* Introduction */}
          <div className="mb-8">
            <div className="flex items-center mb-4">
              <div className="p-3 bg-brand-primary/10 rounded-lg mr-4">
                <FileText className="h-6 w-6 text-brand-primary" />
              </div>
              <h2 className="text-xl font-semibold text-brand-text dark:text-white">
                Welcome to Fikiri Solutions
              </h2>
            </div>
            <p className="text-gray-600 dark:text-gray-300 leading-relaxed">
              These Terms of Service ("Terms") govern your use of Fikiri Solutions' AI-powered business automation platform. 
              By accessing or using our services, you agree to be bound by these Terms.
            </p>
          </div>

          {/* Terms Sections */}
          <div className="space-y-8">
            {/* Section 1: Acceptance of Terms */}
            <motion.section
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
            >
              <div className="flex items-start">
                <div className="p-2 bg-brand-accent/10 rounded-lg mr-4 mt-1">
                  <CheckCircle className="h-5 w-5 text-brand-accent" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-3">
                    1. Acceptance of Terms
                  </h3>
                  <div className="text-gray-600 dark:text-gray-300 space-y-3">
                    <p>
                      By creating an account, accessing our platform, or using any of our services, you acknowledge that you have read, 
                      understood, and agree to be bound by these Terms of Service and our Privacy Policy.
                    </p>
                    <p>
                      If you do not agree to these Terms, you may not access or use our services.
                    </p>
                  </div>
                </div>
              </div>
            </motion.section>

            {/* Section 2: Service Description */}
            <motion.section
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
            >
              <div className="flex items-start">
                <div className="p-2 bg-brand-secondary/10 rounded-lg mr-4 mt-1">
                  <Shield className="h-5 w-5 text-brand-secondary" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-3">
                    2. Service Description
                  </h3>
                  <div className="text-gray-600 dark:text-gray-300 space-y-3">
                    <p>
                      Fikiri Solutions provides AI-powered business automation services including but not limited to:
                    </p>
                    <ul className="list-disc list-inside ml-4 space-y-2">
                      <li>Email automation and management</li>
                      <li>Customer relationship management (CRM)</li>
                      <li>Lead generation and qualification</li>
                      <li>Industry-specific AI assistants</li>
                      <li>Business process automation</li>
                      <li>Analytics and reporting tools</li>
                    </ul>
                  </div>
                </div>
              </div>
            </motion.section>

            {/* Section 3: User Accounts */}
            <motion.section
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.5 }}
            >
              <div className="flex items-start">
                <div className="p-2 bg-brand-primary/10 rounded-lg mr-4 mt-1">
                  <Users className="h-5 w-5 text-brand-primary" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-3">
                    3. User Accounts
                  </h3>
                  <div className="text-gray-600 dark:text-gray-300 space-y-3">
                    <p>
                      To access our services, you must create an account and provide accurate, complete information. 
                      You are responsible for:
                    </p>
                    <ul className="list-disc list-inside ml-4 space-y-2">
                      <li>Maintaining the confidentiality of your account credentials</li>
                      <li>All activities that occur under your account</li>
                      <li>Notifying us immediately of any unauthorized use</li>
                      <li>Providing accurate and up-to-date information</li>
                    </ul>
                  </div>
                </div>
              </div>
            </motion.section>

            {/* Section 4: Privacy and Data Protection */}
            <motion.section
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.6 }}
            >
              <div className="flex items-start">
                <div className="p-2 bg-brand-accent/10 rounded-lg mr-4 mt-1">
                  <Lock className="h-5 w-5 text-brand-accent" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-3">
                    4. Privacy and Data Protection
                  </h3>
                  <div className="text-gray-600 dark:text-gray-300 space-y-3">
                    <p>
                      Your privacy is important to us. Our collection, use, and protection of your personal information 
                      is governed by our Privacy Policy, which is incorporated into these Terms by reference.
                    </p>
                    <p>
                      We implement industry-standard security measures to protect your data and comply with applicable 
                      data protection regulations including GDPR and CCPA.
                    </p>
                  </div>
                </div>
              </div>
            </motion.section>

            {/* Section 5: Acceptable Use */}
            <motion.section
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.7 }}
            >
              <div className="flex items-start">
                <div className="p-2 bg-red-100 dark:bg-red-900/20 rounded-lg mr-4 mt-1">
                  <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-3">
                    5. Acceptable Use Policy
                  </h3>
                  <div className="text-gray-600 dark:text-gray-300 space-y-3">
                    <p>You agree not to use our services for any unlawful or prohibited activities, including:</p>
                    <ul className="list-disc list-inside ml-4 space-y-2">
                      <li>Violating any applicable laws or regulations</li>
                      <li>Transmitting malicious code or harmful content</li>
                      <li>Attempting to gain unauthorized access to our systems</li>
                      <li>Interfering with the proper functioning of our services</li>
                      <li>Using our services to spam or harass others</li>
                      <li>Violating intellectual property rights</li>
                    </ul>
                  </div>
                </div>
              </div>
            </motion.section>

            {/* Section 6: Payment Terms */}
            <motion.section
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.8 }}
            >
              <div className="flex items-start">
                <div className="p-2 bg-brand-secondary/10 rounded-lg mr-4 mt-1">
                  <Calendar className="h-5 w-5 text-brand-secondary" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-3">
                    6. Payment Terms
                  </h3>
                  <div className="text-gray-600 dark:text-gray-300 space-y-3">
                    <p>
                      Our services are offered on a subscription basis with the following pricing tiers:
                    </p>
                    <ul className="list-disc list-inside ml-4 space-y-2">
                      <li><strong>Starter:</strong> $39/month - 200 AI responses</li>
                      <li><strong>Growth:</strong> $79/month - 800 AI responses</li>
                      <li><strong>Business:</strong> $199/month - 4,000 AI responses</li>
                      <li><strong>Enterprise:</strong> $399/month - Unlimited responses</li>
                    </ul>
                    <p>
                      All payments are processed securely through Stripe. Subscriptions automatically renew unless cancelled 
                      before the next billing cycle.
                    </p>
                  </div>
                </div>
              </div>
            </motion.section>

            {/* Section 7: Service Availability */}
            <motion.section
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.9 }}
            >
              <div className="flex items-start">
                <div className="p-2 bg-brand-primary/10 rounded-lg mr-4 mt-1">
                  <Shield className="h-5 w-5 text-brand-primary" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-3">
                    7. Service Availability
                  </h3>
                  <div className="text-gray-600 dark:text-gray-300 space-y-3">
                    <p>
                      We strive to maintain high service availability but cannot guarantee uninterrupted access. 
                      We may temporarily suspend services for maintenance, updates, or technical issues.
                    </p>
                    <p>
                      We are not liable for any downtime or service interruptions beyond our reasonable control.
                    </p>
                  </div>
                </div>
              </div>
            </motion.section>

            {/* Section 8: Limitation of Liability */}
            <motion.section
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 1.0 }}
            >
              <div className="flex items-start">
                <div className="p-2 bg-red-100 dark:bg-red-900/20 rounded-lg mr-4 mt-1">
                  <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-3">
                    8. Limitation of Liability
                  </h3>
                  <div className="text-gray-600 dark:text-gray-300 space-y-3">
                    <p>
                      To the maximum extent permitted by law, Fikiri Solutions shall not be liable for any indirect, 
                      incidental, special, consequential, or punitive damages arising from your use of our services.
                    </p>
                    <p>
                      Our total liability shall not exceed the amount you paid for our services in the 12 months 
                      preceding the claim.
                    </p>
                  </div>
                </div>
              </div>
            </motion.section>

            {/* Section 9: Termination */}
            <motion.section
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 1.1 }}
            >
              <div className="flex items-start">
                <div className="p-2 bg-brand-accent/10 rounded-lg mr-4 mt-1">
                  <FileText className="h-5 w-5 text-brand-accent" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-3">
                    9. Termination
                  </h3>
                  <div className="text-gray-600 dark:text-gray-300 space-y-3">
                    <p>
                      Either party may terminate this agreement at any time. Upon termination:
                    </p>
                    <ul className="list-disc list-inside ml-4 space-y-2">
                      <li>Your access to our services will be revoked</li>
                      <li>You may export your data within 30 days</li>
                      <li>We will delete your data according to our retention policy</li>
                      <li>Outstanding payments remain due</li>
                    </ul>
                  </div>
                </div>
              </div>
            </motion.section>

            {/* Section 10: Changes to Terms */}
            <motion.section
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 1.2 }}
            >
              <div className="flex items-start">
                <div className="p-2 bg-brand-secondary/10 rounded-lg mr-4 mt-1">
                  <Calendar className="h-5 w-5 text-brand-secondary" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-3">
                    10. Changes to Terms
                  </h3>
                  <div className="text-gray-600 dark:text-gray-300 space-y-3">
                    <p>
                      We may update these Terms from time to time. We will notify you of any material changes 
                      via email or through our platform.
                    </p>
                    <p>
                      Continued use of our services after changes constitutes acceptance of the new Terms.
                    </p>
                  </div>
                </div>
              </div>
            </motion.section>
          </div>

          {/* Contact Information */}
          <motion.div
            className="mt-12 p-6 bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 1.3 }}
          >
            <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-4">
              Contact Information
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-center">
                <Mail className="h-5 w-5 text-brand-primary mr-3" />
                <div>
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Email</p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">legal@fikirisolutions.com</p>
                </div>
              </div>
              <div className="flex items-center">
                <Phone className="h-5 w-5 text-brand-primary mr-3" />
                <div>
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Phone</p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">+1 (555) 123-4567</p>
                </div>
              </div>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-4">
              If you have any questions about these Terms of Service, please contact us using the information above.
            </p>
          </motion.div>

          {/* Footer Links */}
          <motion.div
            className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 1.4 }}
          >
            <div className="flex flex-wrap justify-center space-x-6">
              <Link
                to="/privacy"
                className="text-sm text-brand-primary hover:text-brand-secondary transition-colors"
              >
                Privacy Policy
              </Link>
              <Link
                to="/about"
                className="text-sm text-brand-primary hover:text-brand-secondary transition-colors"
              >
                About Us
              </Link>
              <Link
                to="/contact"
                className="text-sm text-brand-primary hover:text-brand-secondary transition-colors"
              >
                Contact
              </Link>
            </div>
            <p className="text-center text-xs text-gray-500 dark:text-gray-400 mt-4">
              © 2024 Fikiri Solutions. All rights reserved.
            </p>
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
};

export { TermsOfService };
