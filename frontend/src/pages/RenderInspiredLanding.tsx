import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ArrowRight, 
  Sparkles, 
  Mail, 
  Users, 
  Brain, 
  Zap, 
  CheckCircle,
  Play,
  ChevronRight,
  BarChart3,
  MessageSquare,
  Calendar,
  TrendingUp
} from 'lucide-react';
import { AnimatedWorkflow } from '../components/AnimatedWorkflow';
import logo from '../assets/logo.svg';

export const RenderInspiredLanding: React.FC = () => {
  const [isVisible, setIsVisible] = useState(false);
  const [activeDemo, setActiveDemo] = useState(0);

  useEffect(() => {
    setIsVisible(true);
  }, []);

  const demos = [
    {
      title: "AI Email Assistant",
      description: "Automatically respond to customer emails with industry-specific intelligence",
      icon: <MessageSquare className="h-6 w-6" />,
      color: "from-blue-500 to-purple-600"
    },
    {
      title: "Smart CRM",
      description: "Track leads and manage customer relationships with AI insights",
      icon: <Users className="h-6 w-6" />,
      color: "from-green-500 to-teal-600"
    },
    {
      title: "Workflow Automation",
      description: "Automate repetitive tasks and streamline business processes",
      icon: <Zap className="h-6 w-6" />,
      color: "from-orange-500 to-red-600"
    }
  ];

  const features = [
    {
      title: "Industry-Specific AI",
      description: "Tailored automation for landscaping, restaurants, medical practices, and more",
      icon: <Brain className="h-8 w-8 text-brand-primary" />
    },
    {
      title: "Real-Time Analytics",
      description: "Track performance with detailed reports and ROI insights",
      icon: <BarChart3 className="h-8 w-8 text-brand-secondary" />
    },
    {
      title: "Seamless Integration",
      description: "Connect with your existing tools and workflows effortlessly",
      icon: <Zap className="h-8 w-8 text-brand-accent" />
    }
  ];

  const stats = [
    { number: "24", label: "Industry Verticals" },
    { number: "50+", label: "Automation Tools" },
    { number: "95%", label: "Time Savings" },
    { number: "500+", label: "Happy Customers" }
  ];

  return (
    <div className="min-h-screen bg-brand-background dark:bg-gray-900 transition-colors duration-300" data-testid="render-landing-page">
      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 bg-brand-background/80 dark:bg-gray-900/80 backdrop-blur-md border-b border-brand-text/10 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link to="/home" className="flex items-center space-x-2 hover:opacity-80 transition-opacity duration-200">
              <img
                src={logo}
                alt="Fikiri Solutions Logo"
                className="h-8 w-8 md:h-10 md:w-10 object-contain"
              />
              <span className="text-xl font-bold text-brand-text dark:text-white">Fikiri Solutions</span>
            </Link>
            
            <div className="hidden md:flex items-center space-x-8">
              <Link to="/services" className="text-brand-text/70 dark:text-gray-300 hover:text-brand-primary dark:hover:text-white transition-colors duration-200">
                Services
              </Link>
              <Link to="/industry" className="text-brand-text/70 dark:text-gray-300 hover:text-brand-primary dark:hover:text-white transition-colors duration-200">
                Industries
              </Link>
              <Link to="/pricing" className="text-brand-text/70 dark:text-gray-300 hover:text-brand-primary dark:hover:text-white transition-colors duration-200">
                Pricing
              </Link>
              <Link to="/docs" className="text-brand-text/70 dark:text-gray-300 hover:text-brand-primary dark:hover:text-white transition-colors duration-200">
                Docs
              </Link>
            </div>

            <div className="flex items-center space-x-4">
              <Link
                to="/login"
                className="text-brand-text/70 dark:text-gray-300 hover:text-brand-primary dark:hover:text-white transition-colors duration-200"
              >
                Sign In
              </Link>
              <Link
                to="/signup"
                className="bg-brand-primary hover:bg-brand-secondary text-white px-4 py-2 rounded-lg font-medium transition-all duration-200 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-brand-accent focus:ring-offset-2 dark:focus:ring-offset-gray-900"
              >
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-20 pb-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="mb-8"
            >
              <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold text-brand-text dark:text-white mb-6 leading-tight">
                Automate emails, leads, and{' '}
                <span className="fikiri-gradient bg-clip-text text-transparent">
                  workflows
                </span>{' '}
                <span className="relative inline-block">
                  in minutes
                  <motion.div
                    initial={{ scaleX: 0, opacity: 0 }}
                    animate={{ scaleX: 1, opacity: 0.3 }}
                    transition={{ duration: 1, delay: 0.5, ease: "easeOut" }}
                    className="absolute -bottom-1 left-0 right-0 h-3 bg-gradient-to-r from-orange-400 to-red-500 rounded-full -z-10"
                  />
                </span>{' '}
                with AI
              </h1>
              <p className="text-xl md:text-2xl text-brand-text/70 dark:text-gray-400 mb-8 max-w-3xl mx-auto">
                Industry-specific AI automation that handles your business processes while you focus on growth
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="flex flex-col sm:flex-row gap-4 justify-center mb-12"
            >
              <Link
                to="/signup"
                className="bg-brand-primary hover:bg-brand-secondary text-white px-8 py-4 rounded-lg font-semibold text-lg transition-all duration-200 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-brand-accent focus:ring-offset-2 dark:focus:ring-offset-gray-900 inline-flex items-center justify-center shadow-lg"
              >
                Try for Free
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
              <Link
                to="/contact"
                className="border-2 border-brand-text/20 dark:border-gray-600 text-brand-text dark:text-gray-300 hover:border-brand-accent dark:hover:border-gray-500 px-8 py-4 rounded-lg font-semibold text-lg transition-all duration-200 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-brand-accent focus:ring-offset-2 dark:focus:ring-offset-gray-900 inline-flex items-center justify-center"
              >
                <Play className="mr-2 h-5 w-5" />
                Watch Demo
              </Link>
            </motion.div>

            {/* Animated Demo Cards */}
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.4 }}
              className="relative max-w-4xl mx-auto"
            >
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                {demos.map((demo, index) => (
                  <motion.div
                    key={index}
                    data-testid="demo-card"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.6 + index * 0.1 }}
                    whileHover={{ scale: 1.05, y: -5 }}
                    className={`bg-gradient-to-br ${demo.color} p-6 rounded-xl text-white cursor-pointer transition-all duration-300 ${
                      activeDemo === index ? 'ring-4 ring-white/50' : ''
                    }`}
                    onClick={() => setActiveDemo(index)}
                  >
                    <div className="flex items-center justify-between mb-4">
                      {demo.icon}
                      <ChevronRight className="h-5 w-5" />
                    </div>
                    <h3 className="text-lg font-semibold mb-2">{demo.title}</h3>
                    <p className="text-sm opacity-90">{demo.description}</p>
                  </motion.div>
                ))}
              </div>

              {/* Enhanced Animated Workflow */}
              <motion.div
                key={activeDemo}
                data-testid="animated-workflow"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5 }}
                className="bg-brand-background dark:bg-gray-800 rounded-2xl p-8 border border-brand-text/10 dark:border-gray-700"
              >
                <AnimatedWorkflow />
              </motion.div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-16 bg-brand-background/50 dark:bg-gray-800" data-testid="stats-section">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((stat, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                viewport={{ once: true }}
                className="text-center"
              >
                <motion.div
                  initial={{ scale: 0 }}
                  whileInView={{ scale: 1 }}
                  transition={{ duration: 0.5, delay: index * 0.1 + 0.3 }}
                  viewport={{ once: true }}
                  className="text-3xl md:text-4xl font-bold text-brand-text dark:text-white mb-2"
                >
                  {stat.number}
                </motion.div>
                <p className="text-brand-text/70 dark:text-gray-400">{stat.label}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8" data-testid="features-section">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl md:text-4xl font-bold text-brand-text dark:text-white mb-4">
              Why Choose Fikiri Solutions?
            </h2>
            <p className="text-xl text-brand-text/70 dark:text-gray-400 max-w-2xl mx-auto">
              Built for modern businesses that need intelligent automation without the complexity
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                viewport={{ once: true }}
                whileHover={{ y: -5 }}
                className="bg-brand-background dark:bg-gray-800 p-8 rounded-xl border border-brand-text/10 dark:border-gray-700 hover:shadow-lg transition-all duration-300"
              >
                <div className="mb-4">{feature.icon}</div>
                <h3 className="text-xl font-semibold text-brand-text dark:text-white mb-3">
                  {feature.title}
                </h3>
                <p className="text-brand-text/70 dark:text-gray-400">
                  {feature.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 fikiri-gradient text-white" data-testid="cta-section">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Ready to Transform Your Business?
            </h2>
            <p className="text-xl mb-8 max-w-2xl mx-auto opacity-90">
              Join hundreds of businesses already using Fikiri Solutions to automate their operations
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                to="/signup"
                className="bg-white text-brand-primary px-8 py-4 rounded-lg font-semibold text-lg hover:bg-gray-100 transition-all duration-200 hover:scale-105 inline-flex items-center justify-center shadow-lg"
              >
                Start Free Trial
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
              <Link
                to="/contact"
                className="border-2 border-white text-white px-8 py-4 rounded-lg font-semibold text-lg hover:bg-white hover:text-brand-primary transition-all duration-200 hover:scale-105 inline-flex items-center justify-center"
              >
                Contact Sales
              </Link>
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  );
};
