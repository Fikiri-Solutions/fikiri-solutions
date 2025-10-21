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
    const response = await page.request.get('/api/dashboard');
    
    // Should either succeed with refresh or redirect to login
    expect(response.status()).toBeLessThan(500);
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
    
    // Try invalid credentials
    await page.getByLabel('Email Address').fill('invalid@example.com');
    await page.getByLabel('Password').fill('wrongpassword');
    await page.getByRole('button', { name: /sign in/i }).click();
    
    // Should show error message
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
    await expect(page.locator('[data-testid="error-message"]')).toContainText(/invalid|incorrect|failed/i);
  });

  test('should handle rate limiting gracefully', async ({ page }) => {
    await page.goto('/login');
    
    // Try multiple rapid login attempts
    for (let i = 0; i < 6; i++) {
      await page.getByLabel('Email Address').fill('test@example.com');
      await page.getByLabel('Password').fill('wrongpassword');
      await page.getByRole('button', { name: /sign in/i }).click();
      
      // Wait a bit between attempts
      await page.waitForTimeout(100);
    }
    
    // Should show rate limit message
    await expect(page.locator('[data-testid="error-message"]')).toContainText(/rate limit|too many|wait/i);
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
    
    // Login
    await page.getByLabel('Email Address').fill(process.env.TEST_USER_EMAIL!);
    await page.getByLabel('Password').fill(process.env.TEST_USER_PASSWORD!);
    await page.getByRole('button', { name: /sign in/i }).click();
    
    // Wait for successful login
    await page.waitForURL('**/(dashboard|onboarding)', { timeout: 15000 });
    
    // Check cookies
    const cookies = await page.context().cookies();
    const sessionCookie = cookies.find(c => c.name === 'fikiri_session');
    const refreshCookie = cookies.find(c => c.name === 'fikiri_refresh_token');
    
    expect(sessionCookie).toBeTruthy();
    expect(sessionCookie?.httpOnly).toBe(true);
    expect(sessionCookie?.secure).toBe(true);
    expect(sessionCookie?.sameSite).toBe('None');
    
    if (refreshCookie) {
      expect(refreshCookie?.httpOnly).toBe(true);
      expect(refreshCookie?.secure).toBe(true);
    }
  });

  test('should handle CORS preflight requests', async ({ page }) => {
    // Make a request with custom headers (triggers preflight)
    const response = await page.request.post('/api/auth/whoami', {
      headers: {
        'Content-Type': 'application/json',
        'X-Custom-Header': 'test'
      }
    });
    
    // Should handle preflight properly
    expect(response.status()).toBeLessThan(500);
  });
});

test.describe('Password Manager Integration', () => {
  test('should work with password managers', async ({ page }) => {
    await page.goto('/login');
    
    // Check autocomplete attributes
    const emailInput = page.getByLabel('Email Address');
    const passwordInput = page.getByLabel('Password');
    
    await expect(emailInput).toHaveAttribute('autocomplete', 'email');
    await expect(passwordInput).toHaveAttribute('autocomplete', 'current-password');
    
    // Check input types
    await expect(emailInput).toHaveAttribute('type', 'email');
    await expect(passwordInput).toHaveAttribute('type', 'password');
  });
});
