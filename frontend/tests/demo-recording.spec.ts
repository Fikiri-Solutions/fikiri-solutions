/**
 * Scripted flow for **product / verification videos** (e.g. fikiridemo account).
 * Relies on Playwright auth setup (`tests/auth.setup.ts`). Point credentials at your
 * demo user via TEST_USER_EMAIL / TEST_USER_PASSWORD (or defaults in auth.setup).
 *
 * Run from `frontend/`: npm run record:demo
 * Videos: test-results/ or playwright-report/ (see Playwright docs).
 */

import { test, expect } from '@playwright/test';

test.describe('Demo recording (verification video)', () => {
  test('dashboard then CRM — visual smoke for recording', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/(dashboard|onboarding|login)/);

    await page.goto('/crm');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('body')).not.toContainText(/500|internal server error/i);
    await expect(page.locator('body')).toContainText(/crm|lead|pipeline|contact/i);
  });
});
