import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mail, Brain, Users, Calendar, BarChart3, Zap } from 'lucide-react';

interface WorkflowStep {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  delay: number;
}

export const AnimatedWorkflow: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);

  const workflowSteps: WorkflowStep[] = [
    {
      id: 'email',
      title: 'Email Received',
      description: 'Customer sends inquiry via email',
      icon: <Mail className="h-6 w-6" />,
      color: 'from-blue-500 to-blue-600',
      delay: 0
    },
    {
      id: 'ai',
      title: 'AI Processing',
      description: 'AI analyzes intent and generates response',
      icon: <Brain className="h-6 w-6" />,
      color: 'from-purple-500 to-purple-600',
      delay: 0.5
    },
    {
      id: 'crm',
      title: 'CRM Update',
      description: 'Lead automatically added to CRM',
      icon: <Users className="h-6 w-6" />,
      color: 'from-green-500 to-green-600',
      delay: 1
    },
    {
      id: 'schedule',
      title: 'Schedule Follow-up',
      description: 'Appointment automatically scheduled',
      icon: <Calendar className="h-6 w-6" />,
      color: 'from-orange-500 to-orange-600',
      delay: 1.5
    },
    {
      id: 'analytics',
      title: 'Analytics Update',
      description: 'Performance metrics updated in real-time',
      icon: <BarChart3 className="h-6 w-6" />,
      color: 'from-teal-500 to-teal-600',
      delay: 2
    }
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setIsAnimating(true);
      setTimeout(() => {
        setCurrentStep((prev) => (prev + 1) % workflowSteps.length);
        setIsAnimating(false);
      }, 300);
    }, 3000);

    return () => clearInterval(interval);
  }, [workflowSteps.length]);

  return (
    <div className="relative max-w-4xl mx-auto" data-testid="animated-workflow-component">
      {/* Workflow Steps */}
      <div className="flex items-center justify-between mb-8">
        {workflowSteps.map((step, index) => (
          <div key={step.id} className="flex flex-col items-center flex-1" data-testid="workflow-step">
            <motion.div
              initial={{ scale: 0.8, opacity: 0.5 }}
              animate={{
                scale: currentStep === index ? 1.2 : 1,
                opacity: currentStep === index ? 1 : 0.6
              }}
              transition={{ duration: 0.3 }}
              className={`w-16 h-16 rounded-full bg-gradient-to-r ${step.color} flex items-center justify-center text-white mb-3 relative`}
            >
              {step.icon}
              
              {/* Pulse effect for active step */}
              <AnimatePresence>
                {currentStep === index && (
                  <motion.div
                    initial={{ scale: 1, opacity: 0.8 }}
                    animate={{ scale: 1.5, opacity: 0 }}
                    transition={{ duration: 1, repeat: Infinity }}
                    className="absolute inset-0 rounded-full bg-white"
                  />
                )}
              </AnimatePresence>
            </motion.div>
            
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: currentStep === index ? 1 : 0.7, y: 0 }}
              transition={{ duration: 0.3 }}
              className="text-center"
            >
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-1">
                {step.title}
              </h3>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                {step.description}
              </p>
            </motion.div>
          </div>
        ))}
      </div>

      {/* Connecting Lines */}
      <div className="absolute top-8 left-0 right-0 h-0.5 bg-gray-200 dark:bg-gray-700 -z-10">
        <motion.div
          className="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-green-500"
          initial={{ width: '0%' }}
          animate={{ width: `${((currentStep + 1) / workflowSteps.length) * 100}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>

      {/* Active Step Details */}
      <motion.div
        key={currentStep}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700 shadow-lg"
      >
        <div className="flex items-center space-x-4">
          <div className={`w-12 h-12 rounded-full bg-gradient-to-r ${workflowSteps[currentStep].color} flex items-center justify-center text-white`}>
            {workflowSteps[currentStep].icon}
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {workflowSteps[currentStep].title}
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              {workflowSteps[currentStep].description}
            </p>
          </div>
        </div>
      </motion.div>

      {/* Floating Elements */}
      <div className="absolute -top-4 -right-4">
        <motion.div
          animate={{ 
            y: [0, -10, 0],
            rotate: [0, 5, 0]
          }}
          transition={{ 
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center"
        >
          <Zap className="h-4 w-4 text-white" />
        </motion.div>
      </div>

      <div className="absolute -bottom-4 -left-4">
        <motion.div
          animate={{ 
            y: [0, 10, 0],
            rotate: [0, -5, 0]
          }}
          transition={{ 
            duration: 2.5,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          className="w-6 h-6 bg-purple-500 rounded-full flex items-center justify-center"
        >
          <BarChart3 className="h-3 w-3 text-white" />
        </motion.div>
      </div>
    </div>
  );
};
