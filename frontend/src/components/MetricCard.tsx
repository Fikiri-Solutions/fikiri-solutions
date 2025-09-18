import React from "react";
import { ArrowUp, ArrowDown, TrendingUp, TrendingDown } from "lucide-react";

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: number | null;
  positive?: boolean;
  icon?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
}

export function MetricCard({ 
  title, 
  value, 
  change, 
  positive = true, 
  icon,
  children,
  className = ""
}: MetricCardProps) {
  const formatValue = (val: string | number) => {
    if (typeof val === "number") {
      return val.toLocaleString();
    }
    return val;
  };

  return (
    <div className={`rounded-2xl shadow-lg p-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 flex flex-col gap-4 hover:shadow-xl transition-all duration-300 ${className}`}>
      {/* Header */}
      <div className="flex justify-between items-start">
        <div className="flex items-center gap-3">
          {icon && (
            <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400">
              {icon}
            </div>
          )}
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            {title}
          </h3>
        </div>
        
        {change !== null && change !== undefined && (
          <div
            className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold ${
              positive 
                ? "text-green-700 bg-green-50 dark:text-green-300 dark:bg-green-900/20" 
                : "text-red-700 bg-red-50 dark:text-red-300 dark:bg-red-900/20"
            }`}
          >
            {positive ? (
              <ArrowUp size={12} className="text-green-600 dark:text-green-400" />
            ) : (
              <ArrowDown size={12} className="text-red-600 dark:text-red-400" />
            )}
            {Math.abs(change)}%
          </div>
        )}
      </div>

      {/* Value */}
      <div className="text-3xl font-bold text-gray-900 dark:text-gray-100">
        {formatValue(value)}
      </div>

      {/* Trend/Chart Area */}
      {children && (
        <div className="mt-2">
          {children}
        </div>
      )}

      {/* Optional trend indicator */}
      {change !== null && change !== undefined && (
        <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
          {positive ? (
            <TrendingUp size={12} className="text-green-500" />
          ) : (
            <TrendingDown size={12} className="text-red-500" />
          )}
          <span>
            {positive ? "Up" : "Down"} from last period
          </span>
        </div>
      )}
    </div>
  );
}