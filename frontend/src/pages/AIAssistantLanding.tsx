import React from 'react';
import { Brain, MessageSquare, Zap, BarChart3, Clock, Shield } from 'lucide-react';
import { FeatureStatus, getFeatureStatus } from '../components/FeatureStatus';

export const AIAssistantLanding: React.FC = () => {
  const capabilities = [
    {
      icon: <MessageSquare className="h-6 w-6 text-blue-500" />,
      title: "Intelligent Email Responses",
      description: "AI that understands context and responds naturally to customer inquiries",
      status: getFeatureStatus('ai-assistant')
    },
    {
      icon: <Brain className="h-6 w-6 text-purple-500" />,
      title: "Learning & Adaptation",
      description: "Gets smarter with every interaction, learning your business tone and style",
      status: getFeatureStatus('ai-assistant')
    },
    {
      icon: <BarChart3 className="h-6 w-6 text-green-500" />,
      title: "Performance Analytics",
      description: "Track response quality, customer satisfaction, and business impact",
      status: getFeatureStatus('analytics')
    },
    {
      icon: <Clock className="h-6 w-6 text-orange-500" />,
      title: "24/7 Availability",
      description: "Never miss a customer inquiry with round-the-clock AI assistance",
      status: getFeatureStatus('automation')
    }
  ];

  const useCases = [
    {
      industry: "E-commerce",
      scenario: "Product inquiries and order support",
      result: "50% faster response times, 30% increase in conversions"
    },
    {
      industry: "Real Estate",
      scenario: "Property inquiries and appointment scheduling",
      result: "Qualify leads automatically, 40% more appointments booked"
    },
    {
      industry: "Healthcare",
      scenario: "Appointment scheduling and patient communication",
      result: "Reduce admin workload by 60%, improve patient satisfaction"
    },
    {
      industry: "Professional Services",
      scenario: "Client inquiries and project updates",
      result: "Professional responses 24/7, never miss a business opportunity"
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-100">
      <div className="container mx-auto px-4 py-16">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            AI Assistant That Works Like Your Best Employee
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
            Deploy an AI assistant that understands your business, responds to customers 
            naturally, and learns from every interaction to get better over time.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button className="bg-purple-600 text-white px-8 py-3 rounded-lg text-lg font-semibold hover:bg-purple-700 transition-colors">
              Try AI Assistant
            </button>
            <button className="border border-purple-600 text-purple-600 px-8 py-3 rounded-lg text-lg font-semibold hover:bg-purple-50 transition-colors">
              See Live Demo
            </button>
          </div>
        </div>

        {/* AI Capabilities */}
        <div className="mb-16">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
            Powerful AI Capabilities
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {capabilities.map((capability, index) => (
              <div key={index} className="bg-white p-6 rounded-xl shadow-lg">
                <div className="flex items-center justify-between mb-4">
                  {capability.icon}
                  <FeatureStatus status={capability.status} />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  {capability.title}
                </h3>
                <p className="text-gray-600">{capability.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Use Cases */}
        <div className="mb-16">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
            Proven Results Across Industries
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {useCases.map((useCase, index) => (
              <div key={index} className="bg-white p-6 rounded-xl shadow-lg">
                <div className="flex items-center mb-4">
                  <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-blue-500 rounded-lg flex items-center justify-center mr-4">
                    <span className="text-white font-bold text-lg">{useCase.industry[0]}</span>
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900">{useCase.industry}</h3>
                </div>
                <p className="text-gray-600 mb-3">{useCase.scenario}</p>
                <div className="bg-green-50 p-3 rounded-lg">
                  <p className="text-green-800 font-medium">{useCase.result}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* CTA Section */}
        <div className="bg-gradient-to-r from-purple-600 to-blue-600 rounded-xl p-12 text-center text-white">
          <h2 className="text-3xl font-bold mb-4">
            Ready to Deploy Your AI Assistant?
          </h2>
          <p className="text-xl mb-8 opacity-90">
            Join hundreds of businesses already using AI to scale their customer communication
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button className="bg-white text-purple-600 px-8 py-3 rounded-lg text-lg font-semibold hover:bg-gray-100 transition-colors">
              Start Free Trial
            </button>
            <button className="border border-white text-white px-8 py-3 rounded-lg text-lg font-semibold hover:bg-white hover:text-purple-600 transition-colors">
              Schedule Demo
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

