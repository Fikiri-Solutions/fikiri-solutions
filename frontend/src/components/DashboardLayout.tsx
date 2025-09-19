import React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

interface DashboardCardProps {
  title: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
  compact?: boolean;
  variant?: string;
  badge?: {
    text: string;
    variant?: "default" | "secondary" | "destructive" | "outline" | "success";
  };
}

export function DashboardCard({ 
  title, 
  description, 
  children, 
  className,
  compact = false,
  variant,
  badge 
}: DashboardCardProps) {
  return (
    <Card className={cn("transition-all duration-300 hover:shadow-md", compact && "p-3", className)}>
      <CardHeader className={cn("space-y-1", compact && "pb-2")}>
        <div className="flex items-center justify-between">
          <CardTitle className={cn("font-semibold", compact ? "text-base" : "text-lg")}>{title}</CardTitle>
          {badge && (
            <Badge variant={badge.variant || "secondary"}>
              {badge.text}
            </Badge>
          )}
        </div>
        {description && !compact && (
          <CardDescription className="text-sm text-muted-foreground">
            {description}
          </CardDescription>
        )}
      </CardHeader>
      {!compact && <Separator />}
      <CardContent className={cn("", compact ? "pt-0" : "pt-6")}>
        {children}
      </CardContent>
    </Card>
  );
}

interface StatsGridProps {
  children: React.ReactNode;
  className?: string;
}

export function StatsGrid({ children, className }: StatsGridProps) {
  return (
    <div className={cn(
      "grid gap-6",
      "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4",
      className
    )}>
      {children}
    </div>
  );
}

interface DashboardSectionProps {
  title: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
}

export function DashboardSection({ 
  title, 
  description, 
  children, 
  className 
}: DashboardSectionProps) {
  return (
    <div className={cn("space-y-6", className)}>
      <div className="space-y-1">
        <h2 className="text-2xl font-bold tracking-tight">{title}</h2>
        {description && (
          <p className="text-muted-foreground">{description}</p>
        )}
      </div>
      {children}
    </div>
  );
}
