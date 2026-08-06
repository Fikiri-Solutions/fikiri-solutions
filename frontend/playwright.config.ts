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
    baseURL: process.env.APP_URL || 'http://localhost:5174',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  
  // Load environment variables from .env.test if it exists
  // You can also set these via command line: BACKEND_PORT=8081 npm run test:e2e

  projects: [
    // Setup project for authentication (longer timeout for signup/navigation)
    {
      name: 'setup',
      testMatch: /auth\.setup\.ts/,
      timeout: 60000,
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

  // Start API + Vite so E2E has /api/auth/* (login, signup). Without Flask on :5000, setup fails with
  // "Network Error" / stuck on /login. reuseExistingServer: reuse if you already have servers running.
  webServer: [
    {
      command: 'python3 app.py',
      cwd: '..',
      url: 'http://localhost:5000/api/health',
      reuseExistingServer: !process.env.CI,
      timeout: 180 * 1000,
      env: {
        ...process.env,
        PORT: process.env.PORT || process.env.BACKEND_PORT || '5000',
        FLASK_ENV: process.env.FLASK_ENV || 'development',
        // Prefer ADMIN_E2E_USER_IDS so a production-like ADMIN_USER_IDS in .env does not break local E2E.
        ADMIN_USER_IDS: process.env.ADMIN_E2E_USER_IDS || '110',
        ADMIN_SECURITY_STORE: process.env.ADMIN_SECURITY_STORE || 'memory',
        ADMIN_MFA_REQUIRED: process.env.ADMIN_MFA_REQUIRED || 'false',
        ADMIN_MFA_VERIFIER_ENABLED: process.env.ADMIN_MFA_VERIFIER_ENABLED || 'false',
        ADMIN_DESTRUCTIVE_ENABLED: 'false',
        IMPERSONATION_ENABLED: process.env.IMPERSONATION_ENABLED || 'false',
        // Keep E2E on local SQLite even when .env has a Postgres DATABASE_URL.
        FIKIRI_FORCE_SQLITE: '1',
        FIKIRI_TEST_MODE: process.env.FIKIRI_TEST_MODE || '1',
      },
      stdout: 'pipe',
      stderr: 'pipe',
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:5174',
      reuseExistingServer: !process.env.CI,
      timeout: 120 * 1000,
    },
  ],
});
