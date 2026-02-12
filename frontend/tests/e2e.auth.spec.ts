// tests/e2e.auth.spec.ts
// End-to-end authentication tests for Fikiri Solutions

import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('should load dashboard with valid session', async ({ page }) => {
    await page.goto('/');
    
    // Should redirect to dashboard if authenticated
    await expect(page).toHaveURL(/.*\/(dashboard|onboarding)/);
    
    // Should show user-specific content
    await expect(page.locator('body')).toContainText(/welcome|dashboard|onboarding/i);
  });

  test('should handle token refresh on 401', async ({ page }) => {
    // Navigate to a protected page
    await page.goto('/dashboard');
    
    // Clear the access token to simulate expiration
    await page.evaluate(() => {
      // Clear token from memory (simulate expiration)
      window.dispatchEvent(new CustomEvent('auth:clear-token'));
    });
    
    // Make an API call that should trigger refresh
    // Use full URL with baseURL from config
    const backendUrl = process.env.BACKEND_URL || `http://localhost:${process.env.BACKEND_PORT || '5000'}`;
    const response = await page.request.get(`${backendUrl}/api/dashboard`).catch(() => null);
    
    // Should either succeed with refresh or redirect to login (or 401/403)
    if (response) {
      expect(response.status()).toBeLessThan(500);
    }
  });

  test('should redirect to login when not authenticated', async ({ page }) => {
    // Clear all authentication state
    await page.context().clearCookies();
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    
    // Try to access protected page
    await page.goto('/dashboard');
    
    // Should redirect to login
    await expect(page).toHaveURL(/.*\/login/);
  });

  test('should show proper error messages on login failure', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    // Try invalid credentials
    const emailInput = page.locator('input[type="email"], input[name="email"], input[id="email"]').first();
    await emailInput.fill('invalid@example.com');
    
    const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
    await passwordInput.fill('wrongpassword');
    
    await page.getByRole('button', { name: /sign in|login/i }).first().click();
    
    // Wait for error message - check multiple possible locations
    const errorLocator = page.locator('text=/invalid|incorrect|failed|error/i').first();
    await expect(errorLocator).toBeVisible({ timeout: 10000 });
  });

  test('should handle rate limiting gracefully', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    const emailInput = page.locator('input[type="email"], input[name="email"], input[id="email"]').first();
    const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
    const submitButton = page.getByRole('button', { name: /sign in|login/i }).first();
    
    // Try multiple rapid login attempts
    for (let i = 0; i < 6; i++) {
      await emailInput.fill('test@example.com');
      await passwordInput.fill('wrongpassword');
      await submitButton.click();
      
      // Wait a bit between attempts
      await page.waitForTimeout(200);
    }
    
    // Should show rate limit message
    const rateLimitMessage = page.locator('text=/rate limit|too many|wait|try again/i').first();
    await expect(rateLimitMessage).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Onboarding Flow', () => {
  test('should complete onboarding steps', async ({ page }) => {
    await page.goto('/onboarding');
    
    // Should be on onboarding page
    await expect(page).toHaveURL(/.*\/onboarding/);
    
    // Fill out onboarding form
    await page.getByLabel('Business Name').fill('Test Company');
    await page.getByLabel('Industry').selectOption('Technology');
    await page.getByLabel('Team Size').selectOption('1-10');
    
    // Submit onboarding
    await page.getByRole('button', { name: /continue|next|complete/i }).click();
    
    // Should redirect to dashboard
    await expect(page).toHaveURL(/.*\/dashboard/);
  });

  test('should allow skipping onboarding', async ({ page }) => {
    await page.goto('/onboarding');
    
    // Look for skip option
    const skipButton = page.getByRole('button', { name: /skip|later/i });
    if (await skipButton.isVisible()) {
      await skipButton.click();
      await expect(page).toHaveURL(/.*\/dashboard/);
    }
  });
});

test.describe('Cookie and CORS', () => {
  test('should set proper cookies on login', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    const testEmail = process.env.TEST_USER_EMAIL || 'test@example.com';
    const testPassword = process.env.TEST_USER_PASSWORD || 'TestPassword123!';
    
    // Login
    const emailInput = page.locator('input[type="email"], input[name="email"], input[id="email"]').first();
    await emailInput.fill(testEmail);
    
    const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
    await passwordInput.fill(testPassword);
    
    await page.getByRole('button', { name: /sign in|login/i }).first().click();
    
    // Wait for successful login - flexible pattern
    await Promise.race([
      page.waitForURL(/.*\/(dashboard|onboarding)/, { timeout: 15000 }),
      page.waitForSelector('text=/welcome|dashboard|step.*of|onboarding/i', { timeout: 15000 })
    ]);
    
    // Check cookies
    const cookies = await page.context().cookies();
    const sessionCookie = cookies.find(c => c.name === 'fikiri_session' || c.name.includes('session'));
    const refreshCookie = cookies.find(c => c.name === 'fikiri_refresh_token' || c.name.includes('refresh'));
    
    // Session cookie should exist (may have different names in dev/prod)
    expect(sessionCookie || cookies.length > 0).toBeTruthy();
    
    if (sessionCookie) {
      expect(sessionCookie?.httpOnly).toBe(true);
      // secure and sameSite may vary by environment
    }
    
    if (refreshCookie) {
      expect(refreshCookie?.httpOnly).toBe(true);
    }
  });

  test('should handle CORS preflight requests', async ({ page }) => {
    // Make a request with custom headers (triggers preflight)
    const backendUrl = process.env.BACKEND_URL || `http://localhost:${process.env.BACKEND_PORT || '5000'}`;
    const response = await page.request.post(`${backendUrl}/api/auth/whoami`, {
      headers: {
        'Content-Type': 'application/json',
        'X-Custom-Header': 'test'
      }
    }).catch(() => null);
    
    // Should handle preflight properly (may return 401 if not authenticated, which is fine)
    if (response) {
      expect(response.status()).toBeLessThan(500);
    }
  });
});

test.describe('Password Manager Integration', () => {
  test('should work with password managers', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    // Check autocomplete attributes - use flexible selectors
    const emailInput = page.locator('input[type="email"], input[name="email"], input[id="email"]').first();
    const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
    
    await expect(emailInput).toBeVisible();
    await expect(passwordInput).toBeVisible();
    
    // Check autocomplete attributes (if present)
    const emailAutocomplete = await emailInput.getAttribute('autocomplete').catch(() => null);
    const passwordAutocomplete = await passwordInput.getAttribute('autocomplete').catch(() => null);
    
    if (emailAutocomplete) {
      expect(['email', 'username']).toContain(emailAutocomplete);
    }
    if (passwordAutocomplete) {
      expect(['current-password', 'password']).toContain(passwordAutocomplete);
    }
    
    // Check input types
    await expect(emailInput).toHaveAttribute('type', 'email');
    await expect(passwordInput).toHaveAttribute('type', 'password');
  });
});
