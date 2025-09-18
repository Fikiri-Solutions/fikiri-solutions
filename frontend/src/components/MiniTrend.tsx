import React from "react";

interface MiniTrendProps {
  data: Array<{
    day: string;
    leads?: number;
    emails?: number;
    revenue?: number;
  }>;
  dataKey: "leads" | "emails" | "revenue";
  color?: string;
  height?: number;
}

export function MiniTrend({ 
  data, 
  dataKey, 
  color = "#3B82F6", 
  height = 40 
}: MiniTrendProps) {
  if (!data || data.length === 0) {
    return (
      <div 
        className="w-full bg-gray-100 dark:bg-gray-800 rounded"
        style={{ height: `${height}px` }}
      />
    );
  }

  const values = data.map(d => d[dataKey] || 0);
  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = max - min || 1;

  const points = values.map((value, index) => {
    const x = (index / (values.length - 1)) * 100;
    const y = 100 - ((value - min) / range) * 100;
    return `${x},${y}`;
  }).join(" ");

  const pathData = `M ${points}`;

  return (
    <div className="w-full" style={{ height: `${height}px` }}>
      <svg
        width="100%"
        height={height}
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        className="overflow-visible"
      >
        {/* Grid lines */}
        <defs>
          <pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse">
            <path d="M 10 0 L 0 0 0 10" fill="none" stroke="currentColor" strokeWidth="0.5" opacity="0.1" />
          </pattern>
        </defs>
        <rect width="100" height="100" fill="url(#grid)" />
        
        {/* Area fill */}
        <path
          d={`M 0,100 L ${pathData} L 100,100 Z`}
          fill={color}
          fillOpacity="0.1"
        />
        
        {/* Line */}
        <path
          d={pathData}
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        
        {/* Data points */}
        {values.map((value, index) => {
          const x = (index / (values.length - 1)) * 100;
          const y = 100 - ((value - min) / range) * 100;
          return (
            <circle
              key={index}
              cx={x}
              cy={y}
              r="2"
              fill={color}
              className="hover:r-3 transition-all duration-200"
            />
          );
        })}
      </svg>
    </div>
  );
}
