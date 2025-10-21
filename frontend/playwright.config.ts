// playwright.config.ts
// Playwright configuration for Fikiri Solutions E2E tests

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  
  use: {
    baseURL: process.env.APP_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    // Setup project for authentication
    {
      name: 'setup',
      testMatch: /auth\.setup\.ts/,
    },
    
    // Main E2E tests with authentication
    {
      name: 'e2e',
      dependencies: ['setup'],
      use: { 
        storageState: 'playwright/.auth/state.json',
        ...devices['Desktop Chrome'],
      },
    },
    
    // Admin tests
    {
      name: 'admin-e2e',
      dependencies: ['setup'],
      use: { 
        storageState: 'playwright/.auth/admin-state.json',
        ...devices['Desktop Chrome'],
      },
    },
    
    // New user onboarding tests
    {
      name: 'onboarding-e2e',
      dependencies: ['setup'],
      use: { 
        storageState: 'playwright/.auth/new-user-state.json',
        ...devices['Desktop Chrome'],
      },
    },
    
    // Mobile tests
    {
      name: 'mobile-e2e',
      dependencies: ['setup'],
      use: { 
        storageState: 'playwright/.auth/state.json',
        ...devices['iPhone 12'],
      },
    },
    
    // Cross-browser tests
    {
      name: 'firefox',
      dependencies: ['setup'],
      use: { 
        storageState: 'playwright/.auth/state.json',
        ...devices['Desktop Firefox'],
      },
    },
    
    {
      name: 'safari',
      dependencies: ['setup'],
      use: { 
        storageState: 'playwright/.auth/state.json',
        ...devices['Desktop Safari'],
      },
    },
  ],

  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});
