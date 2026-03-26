/**
 * Critical path E2E: smoke tests for main app pages.
 * Run before manual QA to ensure core routes load without 500 or blank screen.
 */
import { test, expect } from '@playwright/test';

test.describe('Critical paths (smoke)', () => {
  test('dashboard loads after auth', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    // Either dashboard content or redirect to onboarding/login
    await expect(page).toHaveURL(/\/(dashboard|onboarding|login)/);
    await expect(page.locator('body')).not.toContainText(/500|internal server error/i);
    const body = await page.locator('body').textContent();
    expect(body).toMatch(/dashboard|welcome|leads|onboarding|sign in/i);
  });

  test('CRM page loads', async ({ page }) => {
    await page.goto('/crm');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/(crm|login)/);
    await expect(page.locator('body')).not.toContainText(/500|internal server error/i);
    await expect(page.locator('body')).toContainText(/crm|lead|pipeline|contact/i);
  });

  test('Automations page loads', async ({ page }) => {
    await page.goto('/automations');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/(automations|login)/);
    await expect(page.locator('body')).not.toContainText(/500|internal server error/i);
    await expect(page.locator('body')).toContainText(/automation|workflow|preset/i);
  });

  test('Billing or pricing page loads', async ({ page }) => {
    await page.goto('/billing');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/(billing|login|pricing)/);
    await expect(page.locator('body')).not.toContainText(/500|internal server error/i);
  });
});

test.describe('Public pages (no auth required)', () => {
  test('Pricing page loads', async ({ page }) => {
    await page.goto('/pricing');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/pricing/);
    await expect(page.locator('body')).toContainText(/price|plan|subscription|free/i);
  });

  test('Terms page loads', async ({ page }) => {
    await page.goto('/terms');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/terms/);
    await expect(page.locator('body')).not.toHaveCount(0);
  });

  test('Privacy page loads', async ({ page }) => {
    await page.goto('/privacy');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/privacy/);
    await expect(page.locator('body')).not.toHaveCount(0);
  });

  test('Contact page loads', async ({ page }) => {
    await page.goto('/contact');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/contact/);
    await expect(page.locator('body')).not.toHaveCount(0);
  });
});
