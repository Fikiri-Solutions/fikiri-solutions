/**
 * Playwright config for **demo / verification video** recordings.
 * Always-on video + trace; single worker. Uses same webServer + auth setup as main E2E.
 *
 * Run: npm run record:demo
 *
 * For a dedicated demo account (e.g. fikiridemo), set in `.env.test` or the shell:
 *   TEST_USER_EMAIL=... TEST_USER_PASSWORD=...
 * (see tests/auth.setup.ts — same as normal E2E.)
 */

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testMatch: /demo-recording\.spec\.ts/,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: [['html', { open: 'never' }], ['list']],

  use: {
    baseURL: process.env.APP_URL || 'http://localhost:5174',
    trace: 'on',
    video: 'on',
    screenshot: 'on',
    viewport: { width: 1280, height: 720 },
  },

  projects: [
    {
      name: 'setup',
      testMatch: /auth\.setup\.ts/,
      timeout: 120000,
    },
    {
      name: 'e2e',
      dependencies: ['setup'],
      use: {
        storageState: 'playwright/.auth/state.json',
        ...devices['Desktop Chrome'],
      },
    },
  ],

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
