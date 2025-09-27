import React from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { 
  Shield, 
  Lock, 
  Eye, 
  Database, 
  User, 
  Mail, 
  Phone,
  ArrowLeft,
  Calendar,
  AlertTriangle,
  CheckCircle,
  Settings
} from 'lucide-react';
import { FikiriLogo } from '../components/FikiriLogo';

const PrivacyPolicy: React.FC = () => {
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
              <Link to="/home" className="flex items-center">
                <FikiriLogo size="md" variant="full" />
              </Link>
              <div>
                <h1 className="text-2xl font-bold text-brand-text dark:text-white font-serif">
                  Privacy Policy
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Last updated: {lastUpdated}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <Link
                to="/privacy-settings"
                className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
              >
                <Settings className="h-4 w-4 mr-2" />
                Privacy Settings
              </Link>
              <Link
                to="/home"
                className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Dashboard
              </Link>
            </div>
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
                <Shield className="h-6 w-6 text-brand-primary" />
              </div>
              <h2 className="text-xl font-semibold text-brand-text dark:text-white">
                Your Privacy Matters
              </h2>
            </div>
            <p className="text-gray-600 dark:text-gray-300 leading-relaxed">
              At Fikiri Solutions, we are committed to protecting your privacy and ensuring the security of your personal information. 
              This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our AI-powered 
              business automation platform.
            </p>
          </div>

          {/* Privacy Sections */}
          <div className="space-y-8">
            {/* Section 1: Information We Collect */}
            <motion.section
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
            >
              <div className="flex items-start">
                <div className="p-2 bg-brand-accent/10 rounded-lg mr-4 mt-1">
                  <Database className="h-5 w-5 text-brand-accent" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-3">
                    1. Information We Collect
                  </h3>
                  <div className="text-gray-600 dark:text-gray-300 space-y-3">
                    <p><strong>Personal Information:</strong></p>
                    <ul className="list-disc list-inside ml-4 space-y-2">
                      <li>Name, email address, and company information</li>
                      <li>Account credentials and authentication data</li>
                      <li>Billing and payment information</li>
                      <li>Contact information and communication preferences</li>
                    </ul>
                    <p><strong>Business Data:</strong></p>
                    <ul className="list-disc list-inside ml-4 space-y-2">
                      <li>Email content and metadata for automation processing</li>
                      <li>Customer relationship management (CRM) data</li>
                      <li>Lead information and business communications</li>
                      <li>Analytics and usage data</li>
                    </ul>
                    <p><strong>Technical Information:</strong></p>
                    <ul className="list-disc list-inside ml-4 space-y-2">
                      <li>IP addresses and device information</li>
                      <li>Browser type and version</li>
                      <li>Operating system and platform information</li>
                      <li>Usage patterns and service interactions</li>
                    </ul>
                  </div>
                </div>
              </div>
            </motion.section>

            {/* Section 2: How We Use Your Information */}
            <motion.section
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
            >
              <div className="flex items-start">
                <div className="p-2 bg-brand-secondary/10 rounded-lg mr-4 mt-1">
                  <Eye className="h-5 w-5 text-brand-secondary" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-3">
                    2. How We Use Your Information
                  </h3>
                  <div className="text-gray-600 dark:text-gray-300 space-y-3">
                    <p>We use your information to:</p>
                    <ul className="list-disc list-inside ml-4 space-y-2">
                      <li>Provide and maintain our AI automation services</li>
                      <li>Process and analyze your business communications</li>
                      <li>Generate leads and manage customer relationships</li>
                      <li>Improve our services and develop new features</li>
                      <li>Send important service updates and notifications</li>
                      <li>Process payments and manage billing</li>
                      <li>Ensure security and prevent fraud</li>
                      <li>Comply with legal obligations</li>
                    </ul>
                  </div>
                </div>
              </div>
            </motion.section>

            {/* Section 3: Data Sharing and Disclosure */}
            <motion.section
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.5 }}
            >
              <div className="flex items-start">
                <div className="p-2 bg-brand-primary/10 rounded-lg mr-4 mt-1">
                  <User className="h-5 w-5 text-brand-primary" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-3">
                    3. Data Sharing and Disclosure
                  </h3>
                  <div className="text-gray-600 dark:text-gray-300 space-y-3">
                    <p>We do not sell, trade, or rent your personal information to third parties. We may share your information only in the following circumstances:</p>
                    <ul className="list-disc list-inside ml-4 space-y-2">
                      <li><strong>Service Providers:</strong> Trusted third-party vendors who assist in providing our services</li>
                      <li><strong>Legal Requirements:</strong> When required by law or to protect our rights and safety</li>
                      <li><strong>Business Transfers:</strong> In connection with mergers, acquisitions, or asset sales</li>
                      <li><strong>Consent:</strong> When you explicitly consent to sharing your information</li>
                      <li><strong>Emergency Situations:</strong> To protect the safety of users or the public</li>
                    </ul>
                  </div>
                </div>
              </div>
            </motion.section>

            {/* Section 4: Data Security */}
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
                    4. Data Security
                  </h3>
                  <div className="text-gray-600 dark:text-gray-300 space-y-3">
                    <p>We implement industry-standard security measures to protect your information:</p>
                    <ul className="list-disc list-inside ml-4 space-y-2">
                      <li><strong>Encryption:</strong> Data encrypted in transit and at rest</li>
                      <li><strong>Access Controls:</strong> Strict access controls and authentication</li>
                      <li><strong>Regular Audits:</strong> Security audits and vulnerability assessments</li>
                      <li><strong>Employee Training:</strong> Privacy and security training for all staff</li>
                      <li><strong>Infrastructure Security:</strong> Secure cloud infrastructure and monitoring</li>
                      <li><strong>Incident Response:</strong> Rapid response procedures for security incidents</li>
                    </ul>
                  </div>
                </div>
              </div>
            </motion.section>

            {/* Section 5: Your Rights and Choices */}
            <motion.section
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.7 }}
            >
              <div className="flex items-start">
                <div className="p-2 bg-brand-secondary/10 rounded-lg mr-4 mt-1">
                  <CheckCircle className="h-5 w-5 text-brand-secondary" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-3">
                    5. Your Rights and Choices
                  </h3>
                  <div className="text-gray-600 dark:text-gray-300 space-y-3">
                    <p>You have the following rights regarding your personal information:</p>
                    <ul className="list-disc list-inside ml-4 space-y-2">
                      <li><strong>Access:</strong> Request access to your personal information</li>
                      <li><strong>Correction:</strong> Request correction of inaccurate information</li>
                      <li><strong>Deletion:</strong> Request deletion of your personal information</li>
                      <li><strong>Portability:</strong> Request data portability in a structured format</li>
                      <li><strong>Restriction:</strong> Request restriction of processing</li>
                      <li><strong>Objection:</strong> Object to processing of your information</li>
                      <li><strong>Withdraw Consent:</strong> Withdraw consent for data processing</li>
                    </ul>
                    <p>To exercise these rights, contact us using the information provided below.</p>
                  </div>
                </div>
              </div>
            </motion.section>

            {/* Section 6: Data Retention */}
            <motion.section
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.8 }}
            >
              <div className="flex items-start">
                <div className="p-2 bg-brand-primary/10 rounded-lg mr-4 mt-1">
                  <Calendar className="h-5 w-5 text-brand-primary" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-3">
                    6. Data Retention
                  </h3>
                  <div className="text-gray-600 dark:text-gray-300 space-y-3">
                    <p>We retain your information for as long as necessary to:</p>
                    <ul className="list-disc list-inside ml-4 space-y-2">
                      <li>Provide our services to you</li>
                      <li>Comply with legal obligations</li>
                      <li>Resolve disputes and enforce agreements</li>
                      <li>Improve our services and develop new features</li>
                    </ul>
                    <p>
                      When you delete your account, we will delete your personal information within 30 days, 
                      except where we are required to retain it for legal or regulatory purposes.
                    </p>
                  </div>
                </div>
              </div>
            </motion.section>

            {/* Section 7: Cookies and Tracking */}
            <motion.section
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.9 }}
            >
              <div className="flex items-start">
                <div className="p-2 bg-brand-accent/10 rounded-lg mr-4 mt-1">
                  <Eye className="h-5 w-5 text-brand-accent" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-3">
                    7. Cookies and Tracking Technologies
                  </h3>
                  <div className="text-gray-600 dark:text-gray-300 space-y-3">
                    <p>We use cookies and similar technologies to:</p>
                    <ul className="list-disc list-inside ml-4 space-y-2">
                      <li>Remember your preferences and settings</li>
                      <li>Analyze how you use our services</li>
                      <li>Improve our website performance</li>
                      <li>Provide personalized experiences</li>
                      <li>Ensure security and prevent fraud</li>
                    </ul>
                    <p>
                      You can control cookie settings through your browser preferences. 
                      Note that disabling cookies may affect the functionality of our services.
                    </p>
                  </div>
                </div>
              </div>
            </motion.section>

            {/* Section 8: International Data Transfers */}
            <motion.section
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 1.0 }}
            >
              <div className="flex items-start">
                <div className="p-2 bg-brand-secondary/10 rounded-lg mr-4 mt-1">
                  <Shield className="h-5 w-5 text-brand-secondary" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-3">
                    8. International Data Transfers
                  </h3>
                  <div className="text-gray-600 dark:text-gray-300 space-y-3">
                    <p>
                      Your information may be transferred to and processed in countries other than your own. 
                      We ensure appropriate safeguards are in place for international transfers, including:
                    </p>
                    <ul className="list-disc list-inside ml-4 space-y-2">
                      <li>Standard contractual clauses approved by relevant authorities</li>
                      <li>Adequacy decisions by data protection authorities</li>
                      <li>Certification schemes and codes of conduct</li>
                      <li>Binding corporate rules for intra-group transfers</li>
                    </ul>
                  </div>
                </div>
              </div>
            </motion.section>

            {/* Section 9: Children's Privacy */}
            <motion.section
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 1.1 }}
            >
              <div className="flex items-start">
                <div className="p-2 bg-red-100 dark:bg-red-900/20 rounded-lg mr-4 mt-1">
                  <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-3">
                    9. Children's Privacy
                  </h3>
                  <div className="text-gray-600 dark:text-gray-300 space-y-3">
                    <p>
                      Our services are not intended for children under 13 years of age. 
                      We do not knowingly collect personal information from children under 13.
                    </p>
                    <p>
                      If you are a parent or guardian and believe your child has provided us with personal information, 
                      please contact us immediately so we can delete such information.
                    </p>
                  </div>
                </div>
              </div>
            </motion.section>

            {/* Section 10: Changes to Privacy Policy */}
            <motion.section
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 1.2 }}
            >
              <div className="flex items-start">
                <div className="p-2 bg-brand-primary/10 rounded-lg mr-4 mt-1">
                  <Calendar className="h-5 w-5 text-brand-primary" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-brand-text dark:text-white mb-3">
                    10. Changes to Privacy Policy
                  </h3>
                  <div className="text-gray-600 dark:text-gray-300 space-y-3">
                    <p>
                      We may update this Privacy Policy from time to time. We will notify you of any material changes 
                      via email or through our platform.
                    </p>
                    <p>
                      We encourage you to review this Privacy Policy periodically to stay informed about how we protect your information.
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
                  <p className="text-sm text-gray-600 dark:text-gray-400">info@fikirisolutions.com</p>
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
              If you have any questions about this Privacy Policy or our data practices, please contact us using the information above.
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
                to="/terms"
                className="text-sm text-brand-primary hover:text-brand-secondary transition-colors"
              >
                Terms of Service
              </Link>
              <Link
                to="/privacy-settings"
                className="text-sm text-brand-primary hover:text-brand-secondary transition-colors"
              >
                Privacy Settings
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

export { PrivacyPolicy };
