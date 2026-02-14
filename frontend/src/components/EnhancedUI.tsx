import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowUp, ArrowDown, TrendingUp, TrendingDown } from "lucide-react";

interface EnhancedMetricCardProps {
  title: string;
  value: string | number;
  change?: number | null;
  positive?: boolean;
  icon?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
  onClick?: () => void;
  loading?: boolean;
}

export const EnhancedMetricCard: React.FC<EnhancedMetricCardProps> = ({ 
  title, 
  value, 
  change, 
  positive = true, 
  icon,
  children,
  className = "",
  onClick,
  loading = false
}) => {
  const formatValue = (val: string | number) => {
    if (typeof val === "number") {
      return val.toLocaleString();
    }
    return val;
  };

  return (
    <motion.div 
      className={`rounded-2xl shadow-lg p-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 flex flex-col gap-4 hover:shadow-xl transition-all duration-300 cursor-pointer ${className}`}
      onClick={onClick}
      whileHover={{ 
        scale: 1.02,
        boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)"
      }}
      whileTap={{ scale: 0.98 }}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Header */}
      <div className="flex justify-between items-start">
        <div className="flex items-center gap-3">
          <motion.div 
            className="p-2 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400"
            whileHover={{ rotate: 5 }}
            transition={{ duration: 0.2 }}
          >
            {icon}
          </motion.div>
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            {title}
          </h3>
        </div>
        
        <AnimatePresence>
          {change !== null && (
            <motion.div 
              className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold ${
                positive ? "text-green-700 bg-green-50 dark:text-green-300 dark:bg-green-900/20" : "text-red-700 bg-red-50 dark:text-red-300 dark:bg-red-900/20"
              }`}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ duration: 0.2 }}
            >
              {positive ? (
                <ArrowUp size={12} className="text-green-600 dark:text-green-400" />
              ) : (
                <ArrowDown size={12} className="text-red-600 dark:text-red-400" />
              )}
              {Math.abs(change ?? 0)}%
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Value */}
      <motion.div 
        className="text-3xl font-bold text-gray-900 dark:text-gray-100"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1, duration: 0.3 }}
      >
        {loading ? (
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
        ) : (
          formatValue(value)
        )}
      </motion.div>

      {/* Children (charts, etc.) */}
      <AnimatePresence>
        {children && (
          <motion.div 
            className="mt-2"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Trend indicator */}
      <AnimatePresence>
        {change !== null && (
          <motion.div 
            className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            {positive ? (
              <TrendingUp size={12} className="text-green-500" />
            ) : (
              <TrendingDown size={12} className="text-red-500" />
            )}
            <span>{positive ? "Up" : "Down"} from last period</span>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

// Enhanced Activity Item with animations
interface EnhancedActivityItemProps {
  id: string | number;
  type: string;
  message: string;
  status: string;
  timestamp: string;
  icon?: React.ReactNode;
}

export const EnhancedActivityItem: React.FC<EnhancedActivityItemProps> = ({
  message,
  status,
  timestamp,
  icon
}) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'text-green-600 dark:text-green-400';
      case 'warning':
        return 'text-yellow-600 dark:text-yellow-400';
      case 'error':
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getStatusBg = (status: string) => {
    switch (status) {
      case 'success':
        return 'bg-green-100 dark:bg-green-900/20';
      case 'warning':
        return 'bg-yellow-100 dark:bg-yellow-900/20';
      case 'error':
        return 'bg-red-100 dark:bg-red-900/20';
      default:
        return 'bg-gray-100 dark:bg-gray-900/20';
    }
  };

  return (
    <motion.div 
      className="flex items-center space-x-4 p-4 rounded-lg bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      transition={{ duration: 0.3 }}
      whileHover={{ x: 4 }}
    >
      <motion.div 
        className={`p-2 rounded-full ${getStatusBg(status)}`}
        whileHover={{ scale: 1.1 }}
        transition={{ duration: 0.2 }}
      >
        {icon}
      </motion.div>
      
      <div className="flex-1 min-w-0">
        <motion.p 
          className="text-sm font-medium text-gray-900 dark:text-white truncate"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
        >
          {message}
        </motion.p>
        <motion.p 
          className="text-xs text-gray-500 dark:text-gray-400"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          {timestamp}
        </motion.p>
      </div>
      
      <motion.div 
        className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusBg(status)} ${getStatusColor(status)}`}
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.3 }}
      >
        {status}
      </motion.div>
    </motion.div>
  );
};

// Loading skeleton with animation
export const AnimatedSkeleton: React.FC<{ className?: string }> = ({ className = "" }) => {
  return (
    <motion.div 
      className={`bg-gray-200 dark:bg-gray-700 rounded ${className}`}
      animate={{ 
        opacity: [0.5, 1, 0.5],
      }}
      transition={{ 
        duration: 1.5,
        repeat: Infinity,
        ease: "easeInOut"
      }}
    />
  );
};

// Staggered list animation wrapper
export const StaggeredList: React.FC<{
  children: React.ReactNode;
  className?: string;
}> = ({ children, className = "" }) => {
  return (
    <motion.div 
      className={className}
      initial="hidden"
      animate="visible"
      variants={{
        hidden: { opacity: 0 },
        visible: {
          opacity: 1,
          transition: {
            staggerChildren: 0.1
          }
        }
      }}
    >
      {children}
    </motion.div>
  );
};

// Staggered item animation wrapper
export const StaggeredItem: React.FC<{
  children: React.ReactNode;
  className?: string;
}> = ({ children, className = "" }) => {
  return (
    <motion.div
      className={className}
      variants={{
        hidden: { opacity: 0, y: 20 },
        visible: { opacity: 1, y: 0 }
      }}
      transition={{ duration: 0.3 }}
    >
      {children}
    </motion.div>
  );
};

