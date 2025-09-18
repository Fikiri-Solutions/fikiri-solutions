/**
 * Frontend Polish Enhancements
 * Bundle optimization, image optimization, PWA features, and advanced animations
 */

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'
import { pwaConfig } from './src/config/pwa'

export default defineConfig({
  plugins: [react(), pwaConfig],
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
  build: {
    // Bundle optimization
    rollupOptions: {
      output: {
        manualChunks: {
          // Vendor chunks for better caching
          vendor: ['react', 'react-dom'],
          router: ['react-router-dom'],
          ui: ['@headlessui/react', '@heroicons/react'],
          animations: ['framer-motion'],
          charts: ['recharts'],
          query: ['@tanstack/react-query'],
          analytics: ['@vercel/analytics/react', '@vercel/speed-insights/react'],
        },
      },
    },
    // Optimize bundle size
    chunkSizeWarningLimit: 1000,
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
      },
    },
    // Enable source maps for production debugging
    sourcemap: true,
  },
  // Image optimization
  assetsInclude: ['**/*.webp', '**/*.avif'],
  // PWA configuration
  define: {
    __PWA_ENABLED__: true,
  },
})