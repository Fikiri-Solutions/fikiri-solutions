import { test, expect, type Page } from '@playwright/test';

/**
 * Run with project `onboarding-e2e` (uses playwright/.auth/new-user-state.json).
 * Default `e2e` storage completes onboarding in setup and redirects away from /onboarding.
 */
test.use({ storageState: 'playwright/.auth/new-user-state.json' });

async function stubEmailConnected(page: Page) {
  await page.route('**/api/auth/gmail/status**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true, connected: true, data: { connected: true } }),
    });
  });
  await page.route('**/api/auth/outlook/status**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true, data: { connected: true } }),
    });
  });
}

async function expectOnboardingStep(page: Page, step: 1 | 2 | 3 | 4) {
  await expect(page.getByText(`Step ${step} of 4`, { exact: true })).toBeVisible({ timeout: 15000 });
}

test.describe('Onboarding Golden Path', () => {
  test.describe('with email connection stubbed', () => {
    test.beforeEach(async ({ page }) => {
      await stubEmailConnected(page);
    });

    test('Complete onboarding flow from signup to dashboard', async ({ page }) => {
      await page.goto('/onboarding/1');
      await page.waitForLoadState('networkidle');

      await expectOnboardingStep(page, 1);

      await page.locator('input[name="name"]').fill('QA Test User');
      await page.locator('input[name="company"]').fill('QA Test Company');
      await page.getByRole('button', { name: /^Continue$/i }).click();

      await expect(page.getByRole('heading', { name: 'Connect Your Email' })).toBeVisible({ timeout: 15000 });

      await expect(page.getByRole('heading', { name: "You're Almost There!" })).toBeVisible({ timeout: 12000 });

      await page.getByRole('button', { name: /^Continue$/i }).click();

      await expect(page.getByRole('heading', { name: 'Complete Your Setup' })).toBeVisible({ timeout: 15000 });

      await page.getByRole('button', { name: /Launch Dashboard/i }).click();

      await page.waitForURL(/.*\/dashboard/, { timeout: 20000 });
      await expect(page.locator('body')).toBeVisible();
    });

    test('Onboarding step progression', async ({ page }) => {
      await page.goto('/onboarding/1');
      await page.waitForLoadState('networkidle');

      await expectOnboardingStep(page, 1);

      await page.locator('input[name="name"]').fill('Test User');
      await page.locator('input[name="company"]').fill('Test Company');
      await page.getByRole('button', { name: /^Continue$/i }).click();

      await expectOnboardingStep(page, 2);

      await expectOnboardingStep(page, 3);

      await page.getByRole('button', { name: /^Continue$/i }).click();

      await expectOnboardingStep(page, 4);
    });

    test('Onboarding validation', async ({ page }) => {
      await page.goto('/onboarding/1');
      await page.waitForLoadState('networkidle');

      const continueBtn = page.getByRole('button', { name: /^Continue$/i });
      await expect(continueBtn).toBeDisabled();

      await page.locator('input[name="name"]').fill('Test User');
      await page.locator('input[name="company"]').fill('Test Company');
      await expect(continueBtn).toBeEnabled();
    });

    test('Onboarding A/B testing', async ({ page }) => {
      await page.goto('/onboarding/1');
      await page.waitForLoadState('networkidle');

      await page.locator('input[name="name"]').fill('Test User');
      await page.locator('input[name="company"]').fill('Test Company');

      const nextButton = page.getByRole('button', { name: /^Continue$/i });
      await expect(nextButton).toBeVisible();
      await nextButton.click();

      await expect(page.getByRole('heading', { name: 'Connect Your Email' })).toBeVisible({ timeout: 15000 });

      await expectOnboardingStep(page, 3);
      await page.getByRole('button', { name: /^Continue$/i }).click();

      await expect(page.getByRole('button', { name: /Launch Dashboard/i })).toBeVisible({ timeout: 15000 });
    });

    test('Onboarding progress persistence', async ({ page }) => {
      const redirect = encodeURIComponent('/dashboard');
      await page.goto(`/onboarding/1?redirect=${redirect}`);
      await page.waitForLoadState('networkidle');

      await page.locator('input[name="name"]').fill('Test User');
      await page.locator('input[name="company"]').fill('Test Company');
      await page.getByRole('button', { name: /^Continue$/i }).click();

      await expect(page).toHaveURL(/\/onboarding\/2/, { timeout: 10000 });
      await expect(page.getByRole('heading', { name: 'Connect Your Email' })).toBeVisible({ timeout: 15000 });

      await page.reload();
      await page.waitForLoadState('networkidle');

      await expectOnboardingStep(page, 2);
    });
  });

  test('Onboarding with Google OAuth integration', async ({ page }) => {
    await page.goto('/onboarding/2');
    await page.waitForLoadState('networkidle');

    const googleButton = page.getByRole('button', { name: /Connect Gmail/i }).first();
    await expect(googleButton).toBeVisible({ timeout: 10000 });
  });

  test('Onboarding error handling', async ({ page }) => {
    await stubEmailConnected(page);
    await page.route('**/api/onboarding', async (route) => {
      if (route.request().method() === 'POST') {
        await route.abort();
        return;
      }
      await route.continue();
    });

    await page.goto('/onboarding/1');
    await page.waitForLoadState('networkidle');

    await page.locator('input[name="name"]').fill('Test User');
    await page.locator('input[name="company"]').fill('Test Company');
    await page.getByRole('button', { name: /^Continue$/i }).click();

    await expectOnboardingStep(page, 3);
    await page.getByRole('button', { name: /^Continue$/i }).click();

    await expectOnboardingStep(page, 4);
    await page.getByRole('button', { name: /Launch Dashboard/i }).click();

    const errorToast = page.locator('[data-sonner-toast], .react-hot-toast, [role="status"]').filter({
      hasText: /failed|error|network|save/i,
    });
    await expect(errorToast.first()).toBeVisible({ timeout: 15000 });
  });
});
