// tests/auth.setup.ts
// Playwright authentication setup for Fikiri Solutions

import { test as setup, expect } from '@playwright/test';
import type { APIRequestContext, Page } from '@playwright/test';

const authFile = 'playwright/.auth/state.json';

const DEFAULT_TEST_EMAIL = 'test@example.com';
const DEFAULT_TEST_PASSWORD = 'TestPassword123!';
const DEFAULT_TEST_NAME = 'E2E Test User';
const DEFAULT_TEST_BUSINESS = 'E2E Test';

function isPlaceholderCredential(email: string, password: string): boolean {
  const placeholderEmails = /your@test|your@example|placeholder@|test\.user/i;
  const placeholderPasswords = /^yourpass$|^password$|^your_password$|^changeme$/i;
  return placeholderEmails.test(email) || placeholderPasswords.test(password);
}

function isDefaultCredentials(email: string, password: string): boolean {
  return email === DEFAULT_TEST_EMAIL && password === DEFAULT_TEST_PASSWORD;
}

async function ensureTestUserViaSignup(
  backendUrl: string,
  req: { post: (url: string, options?: { data?: object }) => Promise<{ status: () => number; json: () => Promise<{ error?: string; error_code?: string }> }> }
): Promise<boolean> {
  const signupRes = await req.post(`${backendUrl}/api/auth/signup`, {
    data: {
      email: DEFAULT_TEST_EMAIL,
      password: DEFAULT_TEST_PASSWORD,
      name: DEFAULT_TEST_NAME,
      business_name: DEFAULT_TEST_BUSINESS,
    },
  });
  const status = signupRes.status();
  const body = await signupRes.json().catch(() => ({}));
  if (status === 200 || status === 201) return true;
  if (status === 400) {
    const err = (body.error || '').toLowerCase();
    const code = (body.error_code || '').toLowerCase();
    if (err.includes('already') || code.includes('email') || code.includes('exist')) return true;
  }
  return false;
}

async function createFreshTestUserViaSignup(
  backendUrl: string,
  req: { post: (url: string, options?: { data?: object }) => Promise<{ status: () => number; json: () => Promise<{ error?: string; error_code?: string }> }> }
): Promise<{ email: string; password: string }> {
  const password = DEFAULT_TEST_PASSWORD;
  for (let i = 0; i < 3; i += 1) {
    const email = `test-${Date.now()}-${Math.floor(Math.random() * 10000)}@example.test`;
    const signupRes = await req.post(`${backendUrl}/api/auth/signup`, {
      data: {
        email,
        password,
        name: DEFAULT_TEST_NAME,
        business_name: DEFAULT_TEST_BUSINESS,
      },
    });
    const status = signupRes.status();
    if (status === 200 || status === 201) {
      return { email, password };
    }
  }
  throw new Error('Unable to create a fresh E2E test user via signup.');
}

/**
 * Default E2E user often has onboarding incomplete; protected routes (/crm, /automations)
 * redirect to /onboarding. Mark step 4 on the server and sync localStorage so saved state
 * matches what smoke tests expect.
 */
async function markOnboardingCompletedForE2EUser(
  page: Page,
  request: APIRequestContext,
  backendUrl: string,
  appUrl: string
): Promise<void> {
  const token = await page.evaluate(() => localStorage.getItem('fikiri-token'));
  if (!token) {
    console.warn('E2E auth: no fikiri-token; cannot complete onboarding via API');
    return;
  }
  const res = await request.put(`${backendUrl}/api/user/onboarding-step`, {
    data: { step: 4 },
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
  });
  if (!res.ok()) {
    const txt = await res.text().catch(() => '');
    console.warn(`E2E auth: PUT /api/user/onboarding-step failed ${res.status()}: ${txt}`);
  }
  await page.evaluate(() => {
    try {
      const raw = localStorage.getItem('fikiri-user');
      if (raw) {
        const u = JSON.parse(raw) as Record<string, unknown>;
        u.onboarding_completed = true;
        u.onboarding_step = 4;
        localStorage.setItem('fikiri-user', JSON.stringify(u));
      }
      const za = localStorage.getItem('fikiri-auth');
      if (za) {
        const parsed = JSON.parse(za) as { state?: { user?: Record<string, unknown> } };
        if (parsed.state?.user) {
          parsed.state.user.onboarding_completed = true;
          parsed.state.user.onboarding_step = 4;
          localStorage.setItem('fikiri-auth', JSON.stringify(parsed));
        }
      }
    } catch {
      /* ignore */
    }
  });
  await page.goto(`${appUrl}/dashboard`);
  await page.waitForLoadState('networkidle');
  const finalUrl = page.url();
  if (finalUrl.includes('/onboarding')) {
    throw new Error(
      `E2E auth: still on onboarding after completion (${finalUrl}). Check backend and RouteGuard.`
    );
  }
}

setup('authenticate', async ({ page, request }) => {
  const appUrl = process.env.APP_URL || 'http://localhost:5174';
  const backendPort = process.env.PORT || process.env.BACKEND_PORT || '5000';
  const backendUrl = process.env.BACKEND_URL || `http://localhost:${backendPort}`;
  const testEmail = process.env.TEST_USER_EMAIL || DEFAULT_TEST_EMAIL;
  const testPassword = process.env.TEST_USER_PASSWORD || DEFAULT_TEST_PASSWORD;

  if (isPlaceholderCredential(testEmail, testPassword)) {
    throw new Error(
      'E2E auth uses placeholder credentials. Set TEST_USER_EMAIL and TEST_USER_PASSWORD to a valid user, ' +
      'or unset them to use defaults (test@example.com / TestPassword123!). See docs/E2E_TEST_PLAN.md'
    );
  }

  try {
    const healthCheck = await page.request.get(`${backendUrl}/api/health`, { timeout: 5000 });
    if (!healthCheck.ok()) console.warn('⚠️ Backend health check failed. Tests may fail.');
  } catch {
    console.warn('⚠️ Backend not reachable. Make sure backend is running on', backendUrl);
  }

  // Avoid stale auth state from previous runs.
  await page.context().clearCookies();
  await page.goto(appUrl);
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  await page.goto(appUrl + '/login');
  await page.waitForLoadState('networkidle');

  const emailInput = page.locator('input[type="email"], input[name="email"], input[id="email"]').first();
  await expect(emailInput).toBeVisible({ timeout: 10000 });
  let loginEmail = testEmail;
  let loginPassword = testPassword;
  await emailInput.fill(loginEmail);

  const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
  await passwordInput.fill(loginPassword);

  const [response] = await Promise.all([
    page.waitForResponse(
      (r) => r.url().includes('/api/auth/login') || r.url().includes('/login'),
      { timeout: 10000 }
    ).catch(() => null),
    page.getByRole('button', { name: /sign in|login|submit/i }).first().click()
  ]);

  if (response) {
    const status = response.status();
    const body = await response.json().catch(() => ({}));

    if (status === 401 && isDefaultCredentials(testEmail, testPassword)) {
      const created = await ensureTestUserViaSignup(backendUrl, request);
      if (created) {
        await page.goto(appUrl + '/login');
        await page.waitForLoadState('networkidle');
        await page.locator('input[type="email"], input[name="email"], input[id="email"]').first().fill(loginEmail);
        await page.locator('input[type="password"], input[name="password"]').first().fill(loginPassword);
        const [retryResponse] = await Promise.all([
          page.waitForResponse((r) => r.url().includes('/api/auth/login') || r.url().includes('/login'), { timeout: 10000 }).catch(() => null),
          page.getByRole('button', { name: /sign in|login|submit/i }).first().click()
        ]);
        if (retryResponse && (retryResponse.status() === 200 || retryResponse.status() === 201)) {
          // Success on retry.
        } else {
          // Existing default user may have unknown password; use fresh dedicated user.
          const freshUser = await createFreshTestUserViaSignup(backendUrl, request);
          loginEmail = freshUser.email;
          loginPassword = freshUser.password;

          await page.goto(appUrl + '/login');
          await page.waitForLoadState('networkidle');
          await page.locator('input[type="email"], input[name="email"], input[id="email"]').first().fill(loginEmail);
          await page.locator('input[type="password"], input[name="password"]').first().fill(loginPassword);

          const [freshRetryResponse] = await Promise.all([
            page.waitForResponse((r) => r.url().includes('/api/auth/login') || r.url().includes('/login'), { timeout: 10000 }).catch(() => null),
            page.getByRole('button', { name: /sign in|login|submit/i }).first().click()
          ]);
          if (freshRetryResponse && freshRetryResponse.status() !== 200 && freshRetryResponse.status() !== 201) {
            const retryBody = await freshRetryResponse.json().catch(() => ({}));
            throw new Error(`Login failed for fresh E2E user: ${freshRetryResponse.status()} ${JSON.stringify(retryBody)}`);
          }
        }
      } else {
        const freshUser = await createFreshTestUserViaSignup(backendUrl, request);
        loginEmail = freshUser.email;
        loginPassword = freshUser.password;
        await page.goto(appUrl + '/login');
        await page.waitForLoadState('networkidle');
        await page.locator('input[type="email"], input[name="email"], input[id="email"]').first().fill(loginEmail);
        await page.locator('input[type="password"], input[name="password"]').first().fill(loginPassword);
        const [freshRetryResponse] = await Promise.all([
          page.waitForResponse((r) => r.url().includes('/api/auth/login') || r.url().includes('/login'), { timeout: 10000 }).catch(() => null),
          page.getByRole('button', { name: /sign in|login|submit/i }).first().click()
        ]);
        if (freshRetryResponse && freshRetryResponse.status() !== 200 && freshRetryResponse.status() !== 201) {
          const retryBody = await freshRetryResponse.json().catch(() => ({}));
          throw new Error(`Login failed for fresh E2E user: ${freshRetryResponse.status()} ${JSON.stringify(retryBody)}`);
        }
      }
    } else if (status !== 200 && status !== 201) {
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
  
  const currentUrl = page.url();
  if (!currentUrl.includes('/dashboard') && !currentUrl.includes('/onboarding')) {
    throw new Error(`Authentication may have failed: expected dashboard or onboarding URL, got ${currentUrl}`);
  }

  const userIncomplete = await page.evaluate(() => {
    try {
      const raw = localStorage.getItem('fikiri-user');
      if (!raw) return false;
      const u = JSON.parse(raw) as { id?: number; onboarding_completed?: boolean };
      return !!(u?.id && u.onboarding_completed !== true);
    } catch {
      return false;
    }
  });
  if (currentUrl.includes('/onboarding') || userIncomplete) {
    await markOnboardingCompletedForE2EUser(page, request, backendUrl, appUrl);
  }

  // Optional: wait for any main content (dashboard shows "Total Leads" / "Email Trends" or skeletons; onboarding shows "Step" or "Welcome")
  const hasContent = await page
    .locator('text=/step|welcome|dashboard|total leads|email trends|active services|loading|skeleton/i')
    .first()
    .isVisible({ timeout: 8000 })
    .catch(() => false);
  if (!hasContent) {
    await page.waitForLoadState('domcontentloaded');
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
  // example.com has Null MX (RFC 7505) — Gmail bounces to the sender. Use reserved .test (RFC 2606).
  const testEmail = `test-${Date.now()}@example.test`;
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
  
  // Check terms checkbox (required) — use id so we don't check SMS consent first
  const termsCheckbox = page.locator('#agreeToTerms, input[name="agreeToTerms"]').first();
  if (await termsCheckbox.isVisible({ timeout: 2000 }).catch(() => false)) {
    await termsCheckbox.check();
  }

  const isSignupRequest = (url: string) =>
    (url.includes('/api/auth/signup') || url.includes('/signup') || url.includes('/register')) &&
    !url.includes('/login');

  // Wait for signup request to be sent and for response (match proxy or direct backend URL)
  let signupRequestSent = false;
  page.on('request', (req) => {
    const u = req.url();
    if (req.method() === 'POST' && isSignupRequest(u)) {
      signupRequestSent = true;
      if (process.env.CI || process.env.PW_DEBUG) {
        console.log(`Signup request: ${req.method()} ${u}`);
      }
    }
  });

  const [signupResponse] = await Promise.all([
    page.waitForResponse(
      (res) => {
        const u = res.url();
        return res.request().method() === 'POST' && isSignupRequest(u);
      },
      { timeout: 15000 }
    ).catch(() => null),
    page.getByRole('button', { name: /sign up|register|create account/i }).first().click()
  ]);

  if (signupResponse) {
    const status = signupResponse.status();
    const body = await signupResponse.json().catch(() => ({}));

    if (status !== 200 && status !== 201) {
      if (status === 400) {
        const errorMsg = body.error || body.message || 'Validation error';
        throw new Error(`Signup validation failed: ${errorMsg}`);
      }
      if (status === 429) {
        const retryAfter = body.retry_after ?? 3600;
        console.warn(
          `⚠️ Signup rate limit exceeded (429). Fallback: logging in as default test user for new-user state. ` +
          `Retry after ${retryAfter}s or run backend with FIKIRI_TEST_MODE=1 to bypass signup limit.`
        );
        await page.goto(appUrl + '/login');
        await page.waitForLoadState('networkidle');
        await page.locator('input[type="email"], input[name="email"], input[id="email"]').first().fill(DEFAULT_TEST_EMAIL);
        await page.locator('input[type="password"], input[name="password"]').first().fill(DEFAULT_TEST_PASSWORD);
        const [loginResponse] = await Promise.all([
          page.waitForResponse((r) => r.url().includes('/api/auth/login') || r.url().includes('/login'), { timeout: 10000 }).catch(() => null),
          page.getByRole('button', { name: /sign in|login|submit/i }).first().click()
        ]);
        if (loginResponse && loginResponse.status() === 200) {
          try {
            await Promise.race([
              page.waitForURL(/.*\/(dashboard|onboarding)/, { timeout: 15000 }),
              page.waitForSelector('text=/welcome|dashboard|step.*of|onboarding/i', { timeout: 15000 })
            ]);
          } catch {
            if (!page.url().includes('/dashboard') && !page.url().includes('/onboarding')) {
              throw new Error('Rate limit fallback: default user login did not redirect to dashboard/onboarding.');
            }
          }
          await page.context().storageState({ path: 'playwright/.auth/new-user-state.json' });
          console.log('✅ New-user state saved (using default test user due to signup rate limit).');
          return;
        }
        throw new Error(
          `Signup rate limit exceeded (429, retry after ${retryAfter}s). Default user login fallback failed. ` +
          'Run backend with FIKIRI_TEST_MODE=1 to bypass signup limit, or wait and retry.'
        );
      }
      if (status === 500) {
        console.error('❌ Signup backend error (500):', body);
        const errorMsg = body.error || body.message || 'Backend error during registration';
        throw new Error(`Signup failed: ${errorMsg}. Check backend logs for details.`);
      }
      throw new Error(`Signup API returned ${status}: ${JSON.stringify(body)}`);
    }
  } else {
    await page.waitForTimeout(1500);
    const validationError = page.locator('p.text-red-300, p.text-red-200').first();
    if (await validationError.isVisible({ timeout: 2000 }).catch(() => false)) {
      const text = (await validationError.textContent())?.trim() || '';
      if (text && !/consent|SMS|message and data rates|verification codes/i.test(text) && text.length < 300) {
        throw new Error(`Signup form validation: ${text}`);
      }
    }
    const hint = signupRequestSent
      ? ` Request was sent but no response in 15s. Is the backend running at ${backendUrl}?`
      : ` Signup request was never sent — ensure the app uses ${backendUrl} (do not set VITE_API_URL to production for e2e).`;
    throw new Error(`No signup API response received.${hint}`);
  }

  // Wait for navigation after successful signup (redirect to onboarding or dashboard)
  const navTimeout = 20000;
  try {
    await Promise.race([
      page.waitForURL(/.*\/(dashboard|onboarding)/, { timeout: navTimeout }),
      page.waitForSelector('text=/welcome|dashboard|step.*of|onboarding/i', { timeout: navTimeout })
    ]);
  } catch {
    const currentUrl = page.url();
    if (currentUrl.includes('/signup')) {
      const submitError = await page.locator('[class*="bg-red-500"] p, p.text-red-200').first().textContent().catch(() => '');
      const hint = signupResponse?.status() === 200
        ? ' API returned 200 but navigation did not complete — check redirect/onboarding.'
        : '';
      throw new Error(`Signup failed: ${(submitError?.trim() || 'User creation error')}${hint}`);
    }
    throw new Error(`Signup completed but landed on unexpected page: ${currentUrl}`);
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
