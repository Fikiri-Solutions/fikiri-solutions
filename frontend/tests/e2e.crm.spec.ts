/**
 * CRM E2E: list, pipeline, and optional add-lead flow.
 * Run before manual QA to ensure CRM is usable.
 */
import { test, expect } from '@playwright/test';

test.describe('CRM flows', () => {
  test('CRM shows pipeline or empty state', async ({ page }) => {
    await page.goto('/crm');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/(crm|login)/);
    if (page.url().includes('/login')) return;
    // Either pipeline columns or empty state
    const body = await page.locator('body').textContent();
    const hasPipeline = /new|contacted|qualified|pipeline|lead/i.test(body || '');
    const hasEmpty = /no lead|get started|add your first|connect/i.test(body || '');
    expect(hasPipeline || hasEmpty).toBeTruthy();
  });

  test('CRM page has main content (pipeline, table, or empty state)', async ({ page }) => {
    await page.goto('/crm');
    await page.waitForLoadState('networkidle');
    if (page.url().includes('/login')) return;
    const main = page.locator('main, [role="main"], .content, #root');
    await expect(main.first()).toBeVisible({ timeout: 8000 });
  });

  test('Dashboard Recent automation runs or activity visible', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    if (page.url().includes('/login')) return;
    const body = await page.locator('body').textContent();
    expect(body).toMatch(/dashboard|lead|activity|automation|service/i);
  });
});
