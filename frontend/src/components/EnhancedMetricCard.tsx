import React from "react";
import { ArrowUp, ArrowDown, TrendingUp, TrendingDown } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: number | null;
  positive?: boolean;
  icon?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

export function EnhancedMetricCard({ 
  title, 
  value, 
  change, 
  positive = true, 
  icon,
  children,
  className = "",
  onClick
}: MetricCardProps) {
  const formatValue = (val: string | number) => {
    if (typeof val === "number") {
      return val.toLocaleString();
    }
    return val;
  };

  return (
    <Card 
      className={cn(
        "group cursor-pointer transition-all duration-300 hover:shadow-lg hover:scale-[1.02]",
        className
      )}
      onClick={onClick}
    >
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex items-center gap-3">
          {icon && (
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              {icon}
            </div>
          )}
          <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
            {title}
          </h3>
        </div>
        
        {change !== null && change !== undefined && (
          <Badge 
            variant={positive ? "default" : "destructive"}
            className={cn(
              "flex items-center gap-1 text-xs font-semibold",
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
      
      <CardContent className="space-y-4">
        {/* Main Value */}
        <div className="text-3xl font-bold text-foreground">
          {formatValue(value)}
        </div>
        
        {/* Trend Visualization */}
        {children && (
          <div className="h-12">
            {children}
          </div>
        )}
        
        {/* Optional Additional Info */}
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Last 7 days</span>
          <div className="flex items-center gap-1">
            <TrendingUp className="h-3 w-3" />
            <span>Trending</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
