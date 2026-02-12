/**
 * Frontend Polish Enhancements
 * Bundle optimization, image optimization, PWA features, and advanced animations
 */

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'
import { pwaConfig } from './src/config/pwa'
import { removeInvalidPrefetch } from './vite-plugin-remove-invalid-prefetch'

export default defineConfig(({ mode }) => ({
  test: {
    // Exclude e2e tests (they use Playwright, not Vitest)
    exclude: ['**/node_modules/**', '**/dist/**', '**/tests/e2e.*.spec.ts', '**/tests/**/*.spec.ts'],
    // Include only unit tests
    include: ['**/__tests__/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
    // Use jsdom environment for DOM APIs
    environment: 'jsdom',
    // Setup files
    setupFiles: ['./src/__tests__/setup.ts'],
    // Globals
    globals: true,
  },
  // Ensure absolute paths for Vercel custom domain deployment
  base: '/',
  // Server configuration - use fixed port 5174
  server: {
    port: 5174,
    strictPort: true, // Exit if port is already in use instead of trying next port
    host: true, // Listen on all addresses
  },
  plugins: [
    react(),
    // Remove invalid prefetch links with wildcards
    removeInvalidPrefetch(),
    // Only enable PWA plugin in production builds
    ...(mode === 'production' ? [pwaConfig] : [])
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
    extensions: ['.ts', '.tsx', '.js', '.jsx'],
  },
  build: {
    // Bundle optimization
    outDir: 'dist',
    assetsDir: 'assets', // ensure chunk files live in /assets
    manifest: true,
    rollupOptions: {
      output: {
        manualChunks: {
          // Vendor chunks for better caching
          vendor: ['react', 'react-dom'],
          router: ['react-router-dom'],
          ui: ['@headlessui/react', '@heroicons/react', 'lucide-react'],
          animations: ['framer-motion'],
          charts: ['recharts'],
          query: ['@tanstack/react-query'],
          analytics: ['@vercel/analytics/react', '@vercel/speed-insights/react'],
        },
        // Optimize chunk names for better caching
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
      },
    },
    // Optimize bundle size
    chunkSizeWarningLimit: 1000,
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
        pure_funcs: ['console.log', 'console.info'],
      },
      mangle: {
        safari10: true,
      },
    },
    // Enable source maps for production debugging (only for errors)
    sourcemap: 'hidden',
    // Target modern browsers for better performance
    target: 'esnext',
    // Optimize CSS
    cssCodeSplit: true,
    cssMinify: true,
  },
  // Image optimization
  assetsInclude: ['**/*.webp', '**/*.avif'],
  // PWA configuration
  define: {
    __PWA_ENABLED__: mode === 'production',
  },
}))