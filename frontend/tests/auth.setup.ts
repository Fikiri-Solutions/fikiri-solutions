// tests/auth.setup.ts
// Playwright authentication setup for Fikiri Solutions

import { test as setup, expect } from '@playwright/test';

const authFile = 'playwright/.auth/state.json';

setup('authenticate', async ({ page }) => {
  const appUrl = process.env.APP_URL || 'http://localhost:5174';
  // Backend port can be set via PORT env var (defaults to 5000)
  const backendPort = process.env.PORT || process.env.BACKEND_PORT || '5000';
  const backendUrl = process.env.BACKEND_URL || `http://localhost:${backendPort}`;
  const testEmail = process.env.TEST_USER_EMAIL || 'test@example.com';
  const testPassword = process.env.TEST_USER_PASSWORD || 'TestPassword123!';
  
  // Check if backend is running
  try {
    const healthCheck = await page.request.get(`${backendUrl}/api/health`, { timeout: 5000 });
    if (!healthCheck.ok()) {
      console.warn('⚠️ Backend health check failed. Tests may fail.');
    }
  } catch (error) {
    console.warn('⚠️ Backend not reachable. Make sure backend is running on', backendUrl);
  }
  
  await page.goto(appUrl + '/login');
  await page.waitForLoadState('networkidle');
  
  const emailInput = page.locator('input[type="email"], input[name="email"], input[id="email"]').first();
  await expect(emailInput).toBeVisible({ timeout: 10000 });
  
  await emailInput.fill(testEmail);
  
  const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
  await passwordInput.fill(testPassword);
  
  // Wait for API response to see what happens
  const [response] = await Promise.all([
    page.waitForResponse(
      response => response.url().includes('/api/auth/login') || response.url().includes('/login'),
      { timeout: 10000 }
    ).catch(() => null),
    page.getByRole('button', { name: /sign in|login|submit/i }).first().click()
  ]);
  
  // Check response status
  if (response) {
    const status = response.status();
    const body = await response.json().catch(() => ({}));
    
    if (status !== 200 && status !== 201) {
      console.error(`❌ Login failed with status ${status}:`, body);
      throw new Error(`Login API returned ${status}: ${JSON.stringify(body)}`);
    }
  }
  
  // Wait for navigation - use more flexible pattern and content-based detection
  try {
    // Wait for either URL change OR onboarding/dashboard content to appear
    await Promise.race([
      page.waitForURL(/.*\/(dashboard|onboarding)/, { timeout: 15000 }),
      page.waitForSelector('text=/welcome|dashboard|step.*of|onboarding/i', { timeout: 15000 })
    ]);
  } catch (error) {
    // Check current URL and page content
    const currentUrl = page.url();
    
    // If we're on onboarding or dashboard, that's success
    if (currentUrl.includes('/onboarding') || currentUrl.includes('/dashboard')) {
      // Success - we're on the right page
    } else if (currentUrl.includes('/login')) {
      // Still on login - check for errors
      const errorElement = page.locator('text=/invalid|error|incorrect|failed/i').first();
      const errorText = await errorElement.textContent().catch(() => '');
      
      if (errorText) {
        throw new Error(`Login failed: ${errorText}. Check if user exists or backend is running.`);
      }
      
      throw new Error(`Login failed: Still on login page at ${currentUrl}`);
    } else {
      // Unknown page
      throw new Error(`Login redirected to unexpected page: ${currentUrl}`);
    }
  }
  
  // Verify authentication by checking for onboarding or dashboard content
  const hasOnboardingContent = await page.locator('text=/step.*of|welcome to fikiri|set up your account/i').first().isVisible({ timeout: 5000 }).catch(() => false);
  const hasDashboardContent = await page.locator('text=/dashboard|welcome/i').first().isVisible({ timeout: 5000 }).catch(() => false);
  
  if (!hasOnboardingContent && !hasDashboardContent) {
    throw new Error('Authentication succeeded but page content not found');
  }
  
  await page.context().storageState({ path: authFile });
  console.log('✅ Authentication setup completed');
});

// Additional setup for different user types
setup('authenticate-admin', async ({ page }) => {
  const appUrl = process.env.APP_URL || 'http://localhost:5174';
  const backendPort = process.env.PORT || process.env.BACKEND_PORT || '5000';
  const backendUrl = process.env.BACKEND_URL || `http://localhost:${backendPort}`;
  const testEmail = process.env.TEST_ADMIN_EMAIL || 'admin@example.com';
  const testPassword = process.env.TEST_ADMIN_PASSWORD || 'AdminPassword123!';
  
  await page.goto(appUrl + '/login');
  await page.waitForLoadState('networkidle');
  
  const emailInput = page.locator('input[type="email"], input[name="email"], input[id="email"]').first();
  await expect(emailInput).toBeVisible({ timeout: 10000 });
  
  await emailInput.fill(testEmail);
  
  const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
  await passwordInput.fill(testPassword);
  
  const [response] = await Promise.all([
    page.waitForResponse(
      response => response.url().includes('/api/auth/login') || response.url().includes('/login'),
      { timeout: 10000 }
    ).catch(() => null),
    page.getByRole('button', { name: /sign in|login|submit/i }).first().click()
  ]);
  
  if (response && response.status() !== 200 && response.status() !== 201) {
    const body = await response.json().catch(() => ({}));
    throw new Error(`Admin login failed: ${response.status()} - ${JSON.stringify(body)}`);
  }
  
  // Admin users may also be redirected to onboarding if not completed
  try {
    await Promise.race([
      page.waitForURL(/.*\/(dashboard|onboarding)/, { timeout: 15000 }),
      page.waitForSelector('text=/welcome|dashboard|step.*of|onboarding/i', { timeout: 15000 })
    ]);
  } catch (error) {
    const currentUrl = page.url();
    if (currentUrl.includes('/login')) {
      const errorText = await page.locator('text=/invalid|error/i').first().textContent().catch(() => '');
      throw new Error(`Admin login failed: ${errorText || 'Authentication error'}`);
    }
    throw error;
  }
  
  // Verify we're on dashboard or onboarding
  const currentUrl = page.url();
  if (currentUrl.includes('/dashboard')) {
    await expect(page.locator('body')).toContainText(/dashboard/i);
  } else if (currentUrl.includes('/onboarding')) {
    // Admin is on onboarding - that's acceptable
    await expect(page.locator('body')).toContainText(/welcome|onboarding|step/i);
  }
  await page.context().storageState({ path: 'playwright/.auth/admin-state.json' });
});

setup('authenticate-new-user', async ({ page }) => {
  const appUrl = process.env.APP_URL || 'http://localhost:5174';
  const backendPort = process.env.PORT || process.env.BACKEND_PORT || '5000';
  const backendUrl = process.env.BACKEND_URL || `http://localhost:${backendPort}`;
  const testEmail = `test-${Date.now()}@example.com`;
  const testPassword = 'TestPassword123!';
  
  await page.goto(appUrl + '/signup');
  await page.waitForLoadState('networkidle');
  
  const emailInput = page.locator('input[type="email"], input[name="email"], input[id="email"]').first();
  await expect(emailInput).toBeVisible({ timeout: 10000 });
  await emailInput.fill(testEmail);
  
  const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
  await passwordInput.fill(testPassword);
  
  // Fill all required fields
  const firstNameInput = page.locator('input[name="firstName"], input[name="first_name"], input[placeholder*="John"]').first();
  if (await firstNameInput.isVisible({ timeout: 2000 }).catch(() => false)) {
    await firstNameInput.fill('Test');
  }
  
  const lastNameInput = page.locator('input[name="lastName"], input[name="last_name"], input[placeholder*="Doe"]').first();
  if (await lastNameInput.isVisible({ timeout: 2000 }).catch(() => false)) {
    await lastNameInput.fill('User');
  }
  
  // Fill company name (required field)
  const companyInput = page.locator('input[name="company"], input[name="companyName"], input[placeholder*="Company"]').first();
  if (await companyInput.isVisible({ timeout: 2000 }).catch(() => false)) {
    await companyInput.fill('Test Company');
  }
  
  // Fill confirm password (required field)
  const confirmPasswordInput = page.locator('input[name="confirmPassword"], input[name="confirm_password"], input[type="password"]').nth(1);
  if (await confirmPasswordInput.isVisible({ timeout: 2000 }).catch(() => false)) {
    await confirmPasswordInput.fill(testPassword);
  }
  
  // Check terms checkbox (required)
  const termsCheckbox = page.locator('input[type="checkbox"]').first();
  if (await termsCheckbox.isVisible({ timeout: 2000 }).catch(() => false)) {
    await termsCheckbox.check();
  }
  
  // Wait for signup API response
  const [response] = await Promise.all([
    page.waitForResponse(
      response => response.url().includes('/api/auth/signup') || response.url().includes('/signup') || response.url().includes('/register'),
      { timeout: 10000 }
    ).catch(() => null),
    page.getByRole('button', { name: /sign up|register|create account/i }).first().click()
  ]);
  
  if (response) {
    const status = response.status();
    const body = await response.json().catch(() => ({}));
    
    if (status !== 200 && status !== 201) {
      // Check if it's a validation error (400) vs server error (500)
      if (status === 400) {
        const errorMsg = body.error || body.message || 'Validation error';
        throw new Error(`Signup validation failed: ${errorMsg}`);
      } else if (status === 500) {
        // 500 errors might be backend issues - log details but provide helpful message
        console.error(`❌ Signup backend error (500):`, body);
        const errorMsg = body.error || 'Backend error during registration';
        throw new Error(`Signup failed: ${errorMsg}. Check backend logs for details.`);
      } else {
        throw new Error(`Signup API returned ${status}: ${JSON.stringify(body)}`);
      }
    }
  } else {
    // No response received - check if form validation prevented submission
    await page.waitForTimeout(1000); // Wait a bit for any error messages
    const errorElement = page.locator('text=/error|failed|invalid|required/i').first();
    if (await errorElement.isVisible({ timeout: 2000 }).catch(() => false)) {
      const errorText = await errorElement.textContent();
      throw new Error(`Signup form validation error: ${errorText}`);
    }
  }
  
  // Wait for navigation - use flexible pattern like other tests
  try {
    await Promise.race([
      page.waitForURL(/.*\/(dashboard|onboarding)/, { timeout: 15000 }),
      page.waitForSelector('text=/welcome|dashboard|step.*of|onboarding/i', { timeout: 15000 })
    ]);
  } catch (error) {
    const currentUrl = page.url();
    if (currentUrl.includes('/signup')) {
      const errorText = await page.locator('text=/error|failed|invalid/i').first().textContent().catch(() => '');
      throw new Error(`Signup failed: ${errorText || 'User creation error'}`);
    }
    throw error;
  }
  
  // Verify we're on onboarding or dashboard
  const hasOnboardingContent = await page.locator('text=/step.*of|welcome to fikiri|set up your account/i').first().isVisible({ timeout: 5000 }).catch(() => false);
  const hasDashboardContent = await page.locator('text=/dashboard|welcome/i').first().isVisible({ timeout: 5000 }).catch(() => false);
  
  if (!hasOnboardingContent && !hasDashboardContent) {
    throw new Error('Signup succeeded but page content not found');
  }
  
  await page.context().storageState({ path: 'playwright/.auth/new-user-state.json' });
  
  await page.evaluate(({ email, password }) => {
    localStorage.setItem('test-user-email', email);
    localStorage.setItem('test-user-password', password);
  }, { email: testEmail, password: testPassword });
  
  console.log(`✅ New user created: ${testEmail}`);
});
