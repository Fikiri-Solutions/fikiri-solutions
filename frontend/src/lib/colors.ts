// Fikiri Solutions Brand Colors
// Extracted from the official logo design

export const fikiriColors = {
  // Primary Brand Colors (refined from logo)
  primary: {
    1: '#F7F3E9', // Cream background
    2: '#F39C12', // Golden yellow accent
    3: '#E7641C', // Bright orange
    4: '#B33B1E', // Primary red-orange
    5: '#992D1E', // Deep red
    6: '#C0392B', // Deep red-orange
    7: '#B33B1E', // Primary brand color
    8: '#8B4513', // Muted brown
    9: '#4B1E0C', // Tree brown text
    10: '#3E2723', // Dark brown
    11: '#2C1810', // Darker brown
    12: '#1B0A0A', // Darkest brown
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
  
  // Brand-specific colors for Fikiri (refined from logo)
  brand: {
    primary: '#B33B1E',    // Primary red-orange - buttons, strong CTAs
    secondary: '#E7641C', // Bright orange - hovers, icons, accents
    accent: '#F39C12',    // Golden yellow - highlights, graphs, stats
    warning: '#992D1E',   // Deep red - alerts, section headers
    error: '#C0392B',     // Deep red-orange
    text: '#4B1E0C',      // Tree brown - text, footer background
    background: '#F7F3E9', // Cream - page background, cards
    tan: '#8B4513',       // Darker tan/brown - signup backgrounds
    gradient: 'linear-gradient(135deg, #F39C12 0%, #E7641C 50%, #B33B1E 100%)',
  }
}

// CSS Custom Properties for Fikiri Brand Colors
export const fikiriCSSVariables = `
:root {
  /* Fikiri Brand Colors (refined from logo) */
  --fikiri-primary: #B33B1E;        /* Primary red-orange */
  --fikiri-secondary: #E7641C;      /* Bright orange */
  --fikiri-accent: #F39C12;         /* Golden yellow */
  --fikiri-warning: #992D1E;        /* Deep red */
  --fikiri-error: #C0392B;          /* Deep red-orange */
  --fikiri-text: #4B1E0C;           /* Tree brown */
  --fikiri-bg: #F7F3E9;            /* Cream background */
  --fikiri-tan: #8B4513;           /* Darker tan/brown */
  
  /* Primary Colors */
  --primary: 12 65% 40%; /* #B33B1E */
  --primary-foreground: 0 0% 98%;
  
  /* Secondary Colors */
  --secondary: 25 75% 50%; /* #E7641C */
  --secondary-foreground: 0 0% 98%;
  
  /* Background Colors */
  --background: 45 30% 95%; /* #F7F3E9 */
  --foreground: 25 60% 15%; /* #4B1E0C */
  
  /* Card Colors */
  --card: 45 30% 95%;
  --card-foreground: 25 60% 15%;
  
  /* Popover Colors */
  --popover: 45 30% 95%;
  --popover-foreground: 25 60% 15%;
  
  /* Muted Colors */
  --muted: 45 20% 90%;
  --muted-foreground: 25 40% 30%;
  
  /* Accent Colors */
  --accent: 45 85% 50%; /* #F39C12 */
  --accent-foreground: 25 60% 15%;
  
  /* Destructive Colors */
  --destructive: 0 60% 50%; /* #C0392B */
  --destructive-foreground: 0 0% 98%;
  
  /* Border Colors */
  --border: 25 30% 80%;
  --input: 25 30% 80%;
  --ring: 12 65% 40%;
  
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
