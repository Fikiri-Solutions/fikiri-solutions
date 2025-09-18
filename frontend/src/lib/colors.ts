// Custom Radix Colors Palette for Fikiri Solutions
// Based on the provided colors and brand identity

export const fikiriColors = {
  // Primary Blue Palette (based on your blue selection)
  blue: {
    1: '#f8fafc', // Lightest background
    2: '#f1f5f9', // Subtle background
    3: '#e2e8f0', // Border/subtle
    4: '#cbd5e1', // Border
    5: '#94a3b8', // Muted text
    6: '#64748b', // Text
    7: '#475569', // Text
    8: '#334155', // Text
    9: '#1e293b', // Text
    10: '#0f172a', // Darkest text
    11: '#0c1426', // Darkest
    12: '#020617', // Darkest background
  },
  
  // Accent Purple (for AI/automation features)
  purple: {
    1: '#faf5ff',
    2: '#f3e8ff',
    3: '#e9d5ff',
    4: '#ddd6fe',
    5: '#c4b5fd',
    6: '#a78bfa',
    7: '#8b5cf6',
    8: '#7c3aed',
    9: '#6d28d9',
    10: '#5b21b6',
    11: '#4c1d95',
    12: '#2e1065',
  },
  
  // Success Green (for positive metrics)
  green: {
    1: '#f0fdf4',
    2: '#dcfce7',
    3: '#bbf7d0',
    4: '#86efac',
    5: '#4ade80',
    6: '#22c55e',
    7: '#16a34a',
    8: '#15803d',
    9: '#166534',
    10: '#14532d',
    11: '#052e16',
    12: '#031a0b',
  },
  
  // Warning Orange (for alerts)
  orange: {
    1: '#fff7ed',
    2: '#ffedd5',
    3: '#fed7aa',
    4: '#fdba74',
    5: '#fb923c',
    6: '#f97316',
    7: '#ea580c',
    8: '#c2410c',
    9: '#9a3412',
    10: '#7c2d12',
    11: '#431407',
    12: '#1c0a03',
  },
  
  // Error Red (for critical alerts)
  red: {
    1: '#fef2f2',
    2: '#fee2e2',
    3: '#fecaca',
    4: '#fca5a5',
    5: '#f87171',
    6: '#ef4444',
    7: '#dc2626',
    8: '#b91c1c',
    9: '#991b1b',
    10: '#7f1d1d',
    11: '#450a0a',
    12: '#1f0a0a',
  },
  
  // Neutral Gray (based on your gray selection)
  gray: {
    1: '#f8fafc',
    2: '#f1f5f9',
    3: '#e2e8f0',
    4: '#cbd5e1',
    5: '#94a3b8',
    6: '#64748b',
    7: '#475569',
    8: '#334155',
    9: '#1e293b',
    10: '#0f172a',
    11: '#0c1426',
    12: '#020617',
  },
  
  // Brand-specific colors for Fikiri
  brand: {
    primary: '#3b82f6',    // Main brand blue
    secondary: '#8b5cf6',  // AI/automation purple
    accent: '#22c55e',     // Success green
    warning: '#f97316',    // Warning orange
    error: '#ef4444',      // Error red
  }
}

// CSS Custom Properties for the color system
export const fikiriCSSVariables = `
:root {
  /* Primary Colors */
  --primary: 214 100% 50%; /* #3b82f6 */
  --primary-foreground: 0 0% 98%;
  
  /* Secondary Colors */
  --secondary: 262 83% 58%; /* #8b5cf6 */
  --secondary-foreground: 0 0% 98%;
  
  /* Background Colors */
  --background: 0 0% 100%;
  --foreground: 222 84% 5%;
  
  /* Card Colors */
  --card: 0 0% 100%;
  --card-foreground: 222 84% 5%;
  
  /* Popover Colors */
  --popover: 0 0% 100%;
  --popover-foreground: 222 84% 5%;
  
  /* Muted Colors */
  --muted: 210 40% 98%;
  --muted-foreground: 215 16% 47%;
  
  /* Accent Colors */
  --accent: 210 40% 98%;
  --accent-foreground: 222 84% 5%;
  
  /* Destructive Colors */
  --destructive: 0 84% 60%;
  --destructive-foreground: 0 0% 98%;
  
  /* Border Colors */
  --border: 214 32% 91%;
  --input: 214 32% 91%;
  --ring: 214 100% 50%;
  
  /* Radius */
  --radius: 0.5rem;
}

.dark {
  /* Primary Colors */
  --primary: 214 100% 50%;
  --primary-foreground: 222 84% 5%;
  
  /* Secondary Colors */
  --secondary: 262 83% 58%;
  --secondary-foreground: 222 84% 5%;
  
  /* Background Colors */
  --background: 222 84% 5%;
  --foreground: 210 40% 98%;
  
  /* Card Colors */
  --card: 222 84% 5%;
  --card-foreground: 210 40% 98%;
  
  /* Popover Colors */
  --popover: 222 84% 5%;
  --popover-foreground: 210 40% 98%;
  
  /* Muted Colors */
  --muted: 217 33% 17%;
  --muted-foreground: 215 20% 65%;
  
  /* Accent Colors */
  --accent: 217 33% 17%;
  --accent-foreground: 210 40% 98%;
  
  /* Destructive Colors */
  --destructive: 0 63% 31%;
  --destructive-foreground: 210 40% 98%;
  
  /* Border Colors */
  --border: 217 33% 17%;
  --input: 217 33% 17%;
  --ring: 214 100% 50%;
}
`
