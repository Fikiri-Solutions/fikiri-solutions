module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      transitionProperty: {
        'colors': 'background-color, border-color, color, fill, stroke',
      },
      transitionDuration: {
        '300': '300ms',
      },
      transitionTimingFunction: {
        'ease': 'ease',
      },
      colors: {
        // Custom Radix Colors for Fikiri Solutions
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        // Fikiri Brand Colors (refined from logo)
        brand: {
          primary: "#B33B1E",    // Primary red-orange
          secondary: "#E7641C",  // Bright orange
          accent: "#F39C12",     // Golden yellow
          warning: "#992D1E",    // Deep red
          error: "#C0392B",      // Deep red-orange
          text: "#4B1E0C",       // Tree brown
          background: "#F7F3E9", // Cream background
          tan: "#8B4513",        // Darker tan/brown
        },
        // Fikiri Color Scale
        fikiri: {
          50: "#F7F3E9",   // Cream background
          100: "#F39C12",  // Golden yellow
          200: "#E7641C",  // Bright orange
          300: "#B33B1E",  // Primary red-orange
          400: "#992D1E",  // Deep red
          500: "#C0392B",  // Deep red-orange
          600: "#B33B1E",  // Primary brand color
          700: "#8B4513",  // Muted brown
          800: "#4B1E0C",  // Tree brown text
          900: "#3E2723",  // Dark brown
          950: "#2C1810",  // Darkest brown
        },
        // Extended Radix color scales
        blue: {
          50: "#eff6ff",
          100: "#dbeafe", 
          200: "#bfdbfe",
          300: "#93c5fd",
          400: "#60a5fa",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
          800: "#1e40af",
          900: "#1e3a8a",
          950: "#172554",
        },
        purple: {
          50: "#faf5ff",
          100: "#f3e8ff",
          200: "#e9d5ff",
          300: "#ddd6fe",
          400: "#c4b5fd",
          500: "#8b5cf6",
          600: "#7c3aed",
          700: "#6d28d9",
          800: "#5b21b6",
          900: "#4c1d95",
          950: "#2e1065",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [],
}

