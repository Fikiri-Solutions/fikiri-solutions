import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, CheckCircle, Clock, Users, TrendingUp, Shield, Zap } from 'lucide-react';

interface VerticalLandingProps {
  industry: string;
  title: string;
  subtitle: string;
  icon: string;
  painPoints: string[];
  solutions: string[];
  workflows: string[];
  pricing: {
    tier: string;
    price: number;
    features: string[];
  };
  testimonials?: Array<{
    name: string;
    business: string;
    quote: string;
  }>;
  ctaText: string;
  ctaLink: string;
}

export const VerticalLanding: React.FC<VerticalLandingProps> = ({
  industry,
  title,
  subtitle,
  icon,
  painPoints,
  solutions,
  workflows,
  pricing,
  testimonials = [],
  ctaText,
  ctaLink
}) => {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-300">
      {/* Hero Section */}
      <div className="bg-gradient-to-br from-blue-600 to-purple-700 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="text-center">
            <div className="text-6xl mb-6">{icon}</div>
            <h1 className="text-4xl md:text-6xl font-bold mb-6">
              {title}
            </h1>
            <p className="text-xl md:text-2xl mb-8 max-w-3xl mx-auto opacity-90">
              {subtitle}
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                to={ctaLink}
                className="bg-white text-blue-600 px-8 py-4 rounded-lg font-semibold text-lg hover:bg-gray-100 hover:scale-105 transition-all duration-200 inline-flex items-center justify-center shadow-lg"
              >
                {ctaText}
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
              <Link
                to="/industry"
                className="border-2 border-white text-white px-8 py-4 rounded-lg font-semibold text-lg hover:bg-white hover:text-blue-600 hover:scale-105 transition-all duration-200 inline-flex items-center justify-center"
              >
                Try AI Assistant
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Pain Points Section */}
      <div className="py-20 bg-white dark:bg-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-4">
              Stop Losing Business to These Common Problems
            </h2>
            <p className="text-xl text-gray-600 dark:text-gray-400">
              Every {industry} business faces these challenges. Fikiri Solutions eliminates them.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {painPoints.map((point, index) => (
              <div key={index} className="bg-red-50 dark:bg-red-900/20 p-6 rounded-lg border border-red-200 dark:border-red-800">
                <div className="text-red-600 dark:text-red-400 text-2xl mb-4">❌</div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  Problem {index + 1}
                </h3>
                <p className="text-gray-700 dark:text-gray-300">
                  {point}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Solutions Section */}
      <div className="py-20 bg-gray-50 dark:bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-4">
              How Fikiri Solutions Fixes Everything
            </h2>
            <p className="text-xl text-gray-600 dark:text-gray-400">
              AI-powered automation designed specifically for {industry} businesses
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {solutions.map((solution, index) => (
              <div key={index} className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
                <div className="text-green-600 dark:text-green-400 text-2xl mb-4">✅</div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  Solution {index + 1}
                </h3>
                <p className="text-gray-700 dark:text-gray-300">
                  {solution}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Workflows Section */}
      <div className="py-20 bg-white dark:bg-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-4">
              Automated Workflows That Work
            </h2>
            <p className="text-xl text-gray-600 dark:text-gray-400">
              See how Fikiri Solutions handles your {industry} business processes automatically
            </p>
          </div>
          
          <div className="space-y-8">
            {workflows.map((workflow, index) => (
              <div key={index} className="flex items-center space-x-4 p-6 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <div className="flex-shrink-0">
                  <div className="w-12 h-12 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold">
                    {index + 1}
                  </div>
                </div>
                <div className="flex-1">
                  <p className="text-lg text-gray-900 dark:text-white font-medium">
                    {workflow}
                  </p>
                </div>
                <div className="flex-shrink-0">
                  <Zap className="h-6 w-6 text-blue-600" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Pricing Section */}
      <div className="py-20 bg-gray-50 dark:bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-4">
              Simple, Transparent Pricing
            </h2>
            <p className="text-xl text-gray-600 dark:text-gray-400">
              Choose the plan that fits your {industry} business needs
            </p>
          </div>
          
          <div className="max-w-md mx-auto">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg border-2 border-blue-500 p-8">
              <div className="text-center mb-6">
                <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                  {pricing.tier}
                </h3>
                <div className="text-4xl font-bold text-blue-600 mb-2">
                  ${pricing.price}
                  <span className="text-lg text-gray-600 dark:text-gray-400">/month</span>
                </div>
                <p className="text-gray-600 dark:text-gray-400">
                  Perfect for {industry} businesses
                </p>
              </div>
              
              <ul className="space-y-3 mb-8">
                {pricing.features.map((feature, index) => (
                  <li key={index} className="flex items-center">
                    <CheckCircle className="h-5 w-5 text-green-500 mr-3" />
                    <span className="text-gray-700 dark:text-gray-300">{feature}</span>
                  </li>
                ))}
              </ul>
              
              <Link
                to={ctaLink}
                className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold text-center hover:bg-blue-700 transition-colors inline-flex items-center justify-center"
              >
                Get Started Today
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Testimonials Section */}
      {testimonials.length > 0 && (
        <div className="py-20 bg-white dark:bg-gray-800">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-4">
                What {industry} Businesses Are Saying
              </h2>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {testimonials.map((testimonial, index) => (
                <div key={index} className="bg-gray-50 dark:bg-gray-900 p-6 rounded-lg">
                  <p className="text-gray-700 dark:text-gray-300 mb-4 italic">
                    "{testimonial.quote}"
                  </p>
                  <div className="font-semibold text-gray-900 dark:text-white">
                    {testimonial.name}
                  </div>
                  <div className="text-gray-600 dark:text-gray-400 text-sm">
                    {testimonial.business}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* CTA Section */}
      <div className="py-20 bg-blue-600 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Ready to Transform Your {industry} Business?
          </h2>
          <p className="text-xl mb-8 max-w-2xl mx-auto">
            Join hundreds of {industry} businesses already using Fikiri Solutions to automate their operations and grow their revenue.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              to={ctaLink}
              className="bg-white text-blue-600 px-8 py-4 rounded-lg font-semibold text-lg hover:bg-gray-100 transition-colors inline-flex items-center justify-center"
            >
              Start Free Trial
              <ArrowRight className="ml-2 h-5 w-5" />
            </Link>
            <Link
              to="/contact"
              className="border-2 border-white text-white px-8 py-4 rounded-lg font-semibold text-lg hover:bg-white hover:text-blue-600 transition-colors inline-flex items-center justify-center"
            >
              Schedule Demo
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
