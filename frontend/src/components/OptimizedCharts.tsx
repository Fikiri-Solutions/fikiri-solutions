import React, { Suspense, lazy, memo } from 'react';
import { Skeleton } from './Skeleton';

// Lazy load chart components
const LazyRecharts = lazy(() => import('recharts').then(module => ({
  default: module.ResponsiveContainer
})));

const LazyLineChart = lazy(() => import('recharts').then(module => ({
  default: module.LineChart
})));

const LazyBarChart = lazy(() => import('recharts').then(module => ({
  default: module.BarChart
})));

const LazyPieChart = lazy(() => import('recharts').then(module => ({
  default: module.PieChart
})));

const LazyLine = lazy(() => import('recharts').then(module => ({
  default: module.Line
})));

const LazyBar = lazy(() => import('recharts').then(module => ({
  default: module.Bar
})));

const LazyPie = lazy(() => import('recharts').then(module => ({
  default: module.Pie
})));

const LazyCell = lazy(() => import('recharts').then(module => ({
  default: module.Cell
})));

const LazyXAxis = lazy(() => import('recharts').then(module => ({
  default: module.XAxis
})));

const LazyYAxis = lazy(() => import('recharts').then(module => ({
  default: module.YAxis
})));

const LazyCartesianGrid = lazy(() => import('recharts').then(module => ({
  default: module.CartesianGrid
})));

const LazyTooltip = lazy(() => import('recharts').then(module => ({
  default: module.Tooltip
})));

const LazyLegend = lazy(() => import('recharts').then(module => ({
  default: module.Legend
})));

// Memoized chart data processor
export const processChartData = (data: any[], dataKey: string) => {
  if (!data || data.length === 0) return [];
  
  return data.map(item => ({
    ...item,
    [dataKey]: item[dataKey] || 0,
    // Add calculated fields for better performance
    formattedValue: typeof item[dataKey] === 'number' ? item[dataKey].toLocaleString() : item[dataKey]
  }));
};

// Optimized Line Chart Component
export const OptimizedLineChart: React.FC<{
  data: any[];
  dataKey: string;
  color?: string;
  height?: number;
  className?: string;
}> = memo(({ data, dataKey, color = "#3B82F6", height = 300, className = "" }) => {
  const processedData = React.useMemo(() => processChartData(data, dataKey), [data, dataKey]);

  return (
    <div className={`w-full ${className}`} style={{ height: `${height}px` }}>
      <Suspense fallback={<Skeleton className="w-full h-full" />}>
        <LazyRecharts width="100%" height={height}>
          <LazyLineChart data={processedData}>
            <LazyCartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <LazyXAxis 
              dataKey="name" 
              stroke="#666"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <LazyYAxis 
              stroke="#666"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <LazyTooltip 
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
              }}
            />
            <LazyLine 
              type="monotone" 
              dataKey={dataKey} 
              stroke={color} 
              strokeWidth={2}
              dot={{ fill: color, strokeWidth: 2, r: 4 }}
              activeDot={{ r: 6, stroke: color, strokeWidth: 2 }}
            />
          </LazyLineChart>
        </LazyRecharts>
      </Suspense>
    </div>
  );
});

// Optimized Bar Chart Component
export const OptimizedBarChart: React.FC<{
  data: any[];
  dataKey: string;
  color?: string;
  height?: number;
  className?: string;
}> = memo(({ data, dataKey, color = "#10B981", height = 300, className = "" }) => {
  const processedData = React.useMemo(() => processChartData(data, dataKey), [data, dataKey]);

  return (
    <div className={`w-full ${className}`} style={{ height: `${height}px` }}>
      <Suspense fallback={<Skeleton className="w-full h-full" />}>
        <LazyRecharts width="100%" height={height}>
          <LazyBarChart data={processedData}>
            <LazyCartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <LazyXAxis 
              dataKey="name" 
              stroke="#666"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <LazyYAxis 
              stroke="#666"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <LazyTooltip 
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
              }}
            />
            <LazyBar dataKey={dataKey} fill={color} radius={[4, 4, 0, 0]} />
          </LazyBarChart>
        </LazyRecharts>
      </Suspense>
    </div>
  );
});

// Optimized Pie Chart Component
export const OptimizedPieChart: React.FC<{
  data: any[];
  dataKey: string;
  nameKey: string;
  colors?: string[];
  height?: number;
  className?: string;
}> = memo(({ 
  data, 
  dataKey, 
  nameKey, 
  colors = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"], 
  height = 300, 
  className = "" 
}) => {
  const processedData = React.useMemo(() => processChartData(data, dataKey), [data, dataKey]);

  return (
    <div className={`w-full ${className}`} style={{ height: `${height}px` }}>
      <Suspense fallback={<Skeleton className="w-full h-full" />}>
        <LazyRecharts width="100%" height={height}>
          <LazyPieChart>
            <LazyPie
              data={processedData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }: any) => `${name} ${(percent * 100).toFixed(0)}%`}
              outerRadius={80}
              fill="#8884d8"
              dataKey={dataKey}
            >
              {processedData.map((entry: any, index: number) => (
                <LazyCell key={`cell-${index}`} fill={colors[index % colors.length]} />
              ))}
            </LazyPie>
            <LazyTooltip />
            <LazyLegend />
          </LazyPieChart>
        </LazyRecharts>
      </Suspense>
    </div>
  );
});

// Chart loading wrapper with error boundary
export const ChartWrapper: React.FC<{
  children: React.ReactNode;
  fallback?: React.ReactNode;
}> = ({ children, fallback = <Skeleton className="w-full h-64" /> }) => {
  return (
    <Suspense fallback={fallback}>
      {children}
    </Suspense>
  );
};

