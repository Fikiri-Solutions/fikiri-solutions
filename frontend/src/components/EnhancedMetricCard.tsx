import React, { useState } from "react";
import { ArrowUp, ArrowDown, TrendingUp, TrendingDown, Info, HelpCircle } from "lucide-react";
import { Card, CardContent, CardHeader } from "./ui/card";
import { Badge } from "./ui/badge";
import { cn } from "../lib/utils";

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: number | null;
  positive?: boolean;
  icon?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
  onClick?: () => void;
  compact?: boolean;
  color?: string;
  trend?: 'up' | 'down';
  description?: string;
  businessImpact?: string;
  insight?: string;
}

export function EnhancedMetricCard({ 
  title, 
  value, 
  change, 
  positive = true, 
  icon,
  children,
  className = "",
  onClick,
  compact = false,
  color = 'blue',
  trend = 'up',
  description,
  businessImpact,
  insight
}: MetricCardProps) {
  const [showTooltip, setShowTooltip] = useState(false);
  const formatValue = (val: string | number) => {
    if (typeof val === "number") {
      return val.toLocaleString();
    }
    return val;
  };

  return (
    <Card 
      className={cn(
        "group cursor-pointer transition-all duration-300 hover:shadow-lg hover:scale-[1.02] relative",
        compact && "p-3",
        className
      )}
      onClick={onClick}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <CardHeader className={cn("flex flex-row items-center justify-between space-y-0", compact ? "pb-1" : "pb-2")}>
        <div className="flex items-center gap-3 flex-1">
          {icon && (
            <div className={cn("rounded-lg bg-brand-primary/10 text-brand-primary", compact ? "p-1" : "p-2")}>
              {icon}
            </div>
          )}
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h3 className={cn("font-medium text-muted-foreground uppercase tracking-wide", compact ? "text-xs" : "text-sm")}>
                {title}
              </h3>
              {(description || businessImpact || insight) && (
                <div className="relative">
                  <HelpCircle className="h-4 w-4 text-gray-400 hover:text-gray-600 cursor-help" />
                  {showTooltip && (description || businessImpact || insight) && (
                    <div className="absolute z-50 bottom-full left-0 mb-2 w-64 sm:w-72 md:w-80 max-w-[min(calc(100vw-2rem),20rem)] p-3 bg-gray-900 text-white text-xs rounded-lg shadow-xl whitespace-normal break-words">
                      <div className="space-y-1.5">
                        {description && (
                          <p className="font-semibold leading-relaxed">{description}</p>
                        )}
                        {businessImpact && (
                          <p className="text-green-300 leading-relaxed">💡 {businessImpact}</p>
                        )}
                        {insight && (
                          <p className="text-gray-300 italic leading-relaxed">{insight}</p>
                        )}
                      </div>
                      {/* Tooltip arrow */}
                      <div className="absolute top-full left-4 -mt-1">
                        <div className="w-2 h-2 bg-gray-900 transform rotate-45"></div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
        
        {change !== null && change !== undefined && (
          <Badge 
            variant={positive ? "default" : "destructive"}
            className={cn(
              "flex items-center gap-1 font-semibold",
              compact ? "text-xs" : "text-xs",
              positive 
                ? "bg-green-50 text-green-700 hover:bg-green-50 dark:bg-green-900/20 dark:text-green-300" 
                : "bg-red-50 text-red-700 hover:bg-red-50 dark:bg-red-900/20 dark:text-red-300"
            )}
          >
            {positive ? (
              <ArrowUp className="h-3 w-3" />
            ) : (
              <ArrowDown className="h-3 w-3" />
            )}
            {Math.abs(change)}%
          </Badge>
        )}
      </CardHeader>
      
      <CardContent className={cn("space-y-4", compact && "space-y-2 pb-2")}>
        {/* Main Value */}
        <div className={cn("font-bold text-foreground", compact ? "text-lg" : "text-3xl")}>
          {formatValue(value)}
        </div>
        
        {/* Business Impact Badge */}
        {businessImpact && !compact && (
          <div className="text-xs text-green-600 dark:text-green-400 font-medium bg-green-50 dark:bg-green-900/20 px-2 py-1 rounded">
            {businessImpact}
          </div>
        )}
        
        {/* Trend Visualization */}
        {children && (
          <div className={cn("", compact ? "h-8" : "h-12")}>
            {children}
          </div>
        )}
        
        {/* Optional Additional Info */}
        {!compact && (
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Last 7 days</span>
            <div className="flex items-center gap-1">
              <TrendingUp className="h-3 w-3" />
              <span>Trending</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
