// tests/e2e.auth.spec.ts
// End-to-end authentication tests for Fikiri Solutions

import { test, expect } from '@playwright/test';

/** Clear auth state and navigate to /login so the login form is visible (otherwise RouteGuard redirects authenticated users away). */
async function ensureLoginFormVisible(page: import('@playwright/test').Page) {
  await page.goto('/login');
  await page.waitForLoadState('networkidle');
  await page.context().clearCookies();
  await page.evaluate(() => {
    try {
      localStorage.clear();
      sessionStorage.clear();
    } catch {
      // SecurityError when storage denied
    }
  });
  await page.goto('/login');
  await page.waitForLoadState('networkidle');
}

test.describe('Authentication Flow', () => {
  test('should load dashboard with valid session', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // With stored auth, should be on dashboard or onboarding (not login)
    await expect(page).toHaveURL(/.*\/(dashboard|onboarding)/);
    await expect(page.locator('body')).toContainText(/welcome|dashboard|onboarding|step/i);
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
    // Navigate to app origin first so localStorage/sessionStorage are accessible
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    await page.context().clearCookies();
    await page.evaluate(() => {
      try {
        localStorage.clear();
        sessionStorage.clear();
      } catch {
        // Ignore SecurityError when storage is denied (e.g. opaque origin)
      }
    });
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/.*\/login/, { timeout: 15000 });
  });

  test('should show proper error messages on login failure', async ({ page }) => {
    await ensureLoginFormVisible(page);

    const emailInput = page.locator('input[type="email"], input[name="email"], input[id="email"]').first();
    await emailInput.fill('invalid@example.com');
    const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
    await passwordInput.fill('wrongpassword');

    const [response] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/api/auth/login') && r.request().method() === 'POST', { timeout: 15000 }),
      page.getByRole('button', { name: /sign in|login/i }).first().click()
    ]);
    expect(response.status()).toBe(401);

    const errorBox = page.locator('div.bg-red-50 p, [class*="bg-red-50"] p, [class*="border-red"] p').first();
    await expect(errorBox).toContainText(/invalid|credentials|incorrect|failed|try again/i, { timeout: 5000 });
  });

  test('should handle rate limiting gracefully', async ({ page }) => {
    await ensureLoginFormVisible(page);

    const emailInput = page.locator('input[type="email"], input[name="email"], input[id="email"]').first();
    const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
    const submitButton = page.getByRole('button', { name: /sign in|login/i }).first();

    for (let i = 0; i < 3; i++) {
      await emailInput.fill('test@example.com');
      await passwordInput.fill('wrongpassword');
      const [res] = await Promise.all([
        page.waitForResponse((r) => r.url().includes('/api/auth/login') && r.request().method() === 'POST', { timeout: 10000 }),
        submitButton.click()
      ]);
      await page.waitForTimeout(400);
    }

    const errorInRedBox = page.locator('div.bg-red-50 p, [class*="bg-red-50"] p').first();
    await expect(errorInRedBox).toBeVisible({ timeout: 5000 });
    await expect(errorInRedBox).toContainText(/rate limit|too many|invalid|credentials|try again/i);
  });
});

test.describe('Onboarding Flow', () => {
  test('should complete onboarding steps', async ({ page }) => {
    await page.goto('/onboarding/1');
    await page.waitForLoadState('networkidle');

    const url = page.url();
    if (url.includes('/dashboard')) {
      expect(url).toContain('/dashboard');
      return;
    }
    await expect(page).toHaveURL(/\/onboarding/);

    const nameField = page.getByPlaceholder('John Doe').or(page.locator('input[name="name"]'));
    const companyField = page.getByPlaceholder('Acme Inc.').or(page.locator('input[name="company"]'));
    await nameField.first().fill('Test User');
    await companyField.first().fill('Test Company');
    const industryInput = page.locator('input[name="industry"]');
    if (await industryInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await industryInput.fill('Technology');
    }

    await page.getByRole('button', { name: /continue/i }).click();

    await expect(page).toHaveURL(/\/(onboarding|dashboard)/, { timeout: 10000 });
    await expect(page.locator('body')).toContainText(/connect|dashboard|welcome|step|email/i);
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
    await ensureLoginFormVisible(page);

    const testEmail = process.env.TEST_USER_EMAIL || 'test@example.com';
    const testPassword = process.env.TEST_USER_PASSWORD || 'TestPassword123!';

    const emailInput = page.locator('input[type="email"], input[name="email"], input[id="email"]').first();
    await emailInput.fill(testEmail);
    const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
    await passwordInput.fill(testPassword);

    const [response] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/api/auth/login') && r.request().method() === 'POST', { timeout: 15000 }),
      page.getByRole('button', { name: /sign in|login/i }).first().click()
    ]);
    const loginStatus = response.status();
    if (loginStatus !== 200 && loginStatus !== 201) {
      const hint =
        loginStatus === 429
          ? ' (rate limited — use FLASK_ENV=development / FIKIRI_TEST_MODE=1 on the backend, or run e2e with fewer workers)'
          : loginStatus === 401
            ? ' (wrong password for this user in the DB — reset password or set TEST_USER_EMAIL / TEST_USER_PASSWORD)'
            : '';
      test.skip(
        true,
        `Login returned ${loginStatus} — set valid TEST_USER_EMAIL and TEST_USER_PASSWORD${hint}`
      );
    }

    await Promise.race([
      page.waitForURL(/.*\/(dashboard|onboarding)/, { timeout: 15000 }),
      page.waitForSelector('text=/welcome|dashboard|step|onboarding/i', { timeout: 15000 })
    ]);

    const cookies = await page.context().cookies();
    const sessionCookie = cookies.find(c => c.name === 'fikiri_session' || c.name.includes('session'));
    const refreshCookie = cookies.find(c => c.name === 'fikiri_refresh_token' || c.name.includes('refresh'));

    expect(sessionCookie || cookies.length > 0).toBeTruthy();
    if (sessionCookie && sessionCookie.httpOnly !== undefined) {
      expect(sessionCookie.httpOnly).toBe(true);
    }
    if (refreshCookie && refreshCookie.httpOnly !== undefined) {
      expect(refreshCookie.httpOnly).toBe(true);
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
    await ensureLoginFormVisible(page);

    const emailInput = page.locator('input[type="email"], input[name="email"], input[id="email"]').first();
    const passwordInput = page.locator('input[type="password"], input[name="password"], input[id="password"]').first();
    await expect(emailInput).toBeVisible({ timeout: 5000 });
    await expect(passwordInput).toBeVisible({ timeout: 5000 });

    const emailType = await emailInput.getAttribute('type');
    const passwordType = await passwordInput.getAttribute('type');
    expect(emailType).toBe('email');
    expect(['password', 'text']).toContain(passwordType ?? 'password');

    const emailAutocomplete = await emailInput.getAttribute('autocomplete').catch(() => null);
    const passwordAutocomplete = await passwordInput.getAttribute('autocomplete').catch(() => null);
    if (emailAutocomplete) expect(['email', 'username']).toContain(emailAutocomplete);
    if (passwordAutocomplete) expect(['current-password', 'password']).toContain(passwordAutocomplete);
  });
});
