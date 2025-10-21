// tests/auth.setup.ts
// Playwright authentication setup for Fikiri Solutions

import { test as setup, expect } from '@playwright/test';

const authFile = 'playwright/.auth/state.json';

setup('authenticate', async ({ page }) => {
  // Navigate to login page
  await page.goto(process.env.APP_URL + '/login');
  
  // Wait for login form to be visible
  await expect(page.getByLabel('Email Address')).toBeVisible();
  
  // Fill in test credentials
  await page.getByLabel('Email Address').fill(process.env.TEST_USER_EMAIL!);
  await page.getByLabel('Password').fill(process.env.TEST_USER_PASSWORD!);
  
  // Submit login form
  await page.getByRole('button', { name: /sign in/i }).click();
  
  // Wait for successful login (either dashboard or onboarding)
  await page.waitForURL('**/(dashboard|onboarding)', { timeout: 15000 });
  
  // Verify we're authenticated by checking for user-specific content
  await expect(page.locator('body')).toContainText(/welcome|dashboard|onboarding/i);
  
  // Save authentication state
  await page.context().storageState({ path: authFile });
  
  console.log('✅ Authentication setup completed');
});

// Additional setup for different user types
setup('authenticate-admin', async ({ page }) => {
  await page.goto(process.env.APP_URL + '/login');
  await expect(page.getByLabel('Email Address')).toBeVisible();
  
  await page.getByLabel('Email Address').fill(process.env.TEST_ADMIN_EMAIL!);
  await page.getByLabel('Password').fill(process.env.TEST_ADMIN_PASSWORD!);
  await page.getByRole('button', { name: /sign in/i }).click();
  
  await page.waitForURL('**/dashboard', { timeout: 15000 });
  await expect(page.locator('body')).toContainText(/dashboard/i);
  
  await page.context().storageState({ path: 'playwright/.auth/admin-state.json' });
});

setup('authenticate-new-user', async ({ page }) => {
  // Create a new user account for testing
  await page.goto(process.env.APP_URL + '/signup');
  await expect(page.getByLabel('Email Address')).toBeVisible();
  
  const testEmail = `test-${Date.now()}@example.com`;
  const testPassword = 'TestPassword123!';
  
  await page.getByLabel('Email Address').fill(testEmail);
  await page.getByLabel('Password').fill(testPassword);
  await page.getByLabel('Full Name').fill('Test User');
  
  await page.getByRole('button', { name: /sign up/i }).click();
  
  // Wait for onboarding or dashboard
  await page.waitForURL('**/(dashboard|onboarding)', { timeout: 15000 });
  
  // Save state for new user
  await page.context().storageState({ path: 'playwright/.auth/new-user-state.json' });
  
  // Store credentials for cleanup
  await page.evaluate(({ email, password }) => {
    localStorage.setItem('test-user-email', email);
    localStorage.setItem('test-user-password', password);
  }, { email: testEmail, password: testPassword });
});
