import { test, expect } from '@playwright/test';

test.describe('Onboarding Golden Path', () => {
  test('Complete onboarding flow from signup to dashboard', async ({ page }) => {
    // Start from landing page
    await page.goto('/');
    
    // Click "Get Started" button
    await page.click('text=Get Started');
    await expect(page).toHaveURL(/.*onboarding-flow/);
    
    // Step 1: Google OAuth (skip for now)
    await page.click('text=Skip for now');
    
    // Step 2: Company Information
    await page.fill('[name="name"]', 'QA Test User');
    await page.fill('[name="company"]', 'QA Test Company');
    await page.fill('[name="industry"]', 'Technology');
    
    // Click Next/Continue (A/B tested)
    await page.click('button:has-text("Next"), button:has-text("Continue")');
    
    // Step 3: Email Integration (skip for now)
    await page.click('text=Skip for now');
    
    // Step 4: Complete Setup
    await expect(page.locator('text=Complete Your Setup')).toBeVisible();
    await expect(page.locator('text=QA Test User')).toBeVisible();
    await expect(page.locator('text=QA Test Company')).toBeVisible();
    
    // Complete setup (A/B tested button text)
    await page.click('button:has-text("Complete Setup"), button:has-text("Finish & Launch")');
    
    // Should redirect to dashboard
    await expect(page).toHaveURL(/.*dashboard/);
    
    // Verify user is logged in
    await expect(page.locator('text=Welcome')).toBeVisible();
  });

  test('Onboarding with Google OAuth integration', async ({ page }) => {
    // Start from landing page
    await page.goto('/');
    await page.click('text=Get Started');
    
    // Step 1: Try Google OAuth
    await page.click('text=Continue with Google');
    
    // Note: In a real test, you'd mock the OAuth flow
    // For now, we'll just verify the button works
    await expect(page.locator('text=Continue with Google')).toBeVisible();
  });

  test('Onboarding step progression', async ({ page }) => {
    await page.goto('/onboarding-flow');
    
    // Verify we start at step 1
    await expect(page.locator('text=Step 1 of 4')).toBeVisible();
    
    // Skip step 1
    await page.click('text=Skip for now');
    
    // Should be at step 2
    await expect(page.locator('text=Step 2 of 4')).toBeVisible();
    
    // Fill required fields and proceed
    await page.fill('[name="name"]', 'Test User');
    await page.fill('[name="company"]', 'Test Company');
    await page.click('button:has-text("Next"), button:has-text("Continue")');
    
    // Should be at step 3
    await expect(page.locator('text=Step 3 of 4')).toBeVisible();
    
    // Skip step 3
    await page.click('text=Skip for now');
    
    // Should be at step 4
    await expect(page.locator('text=Step 4 of 4')).toBeVisible();
  });

  test('Onboarding validation', async ({ page }) => {
    await page.goto('/onboarding-flow');
    
    // Skip to step 2
    await page.click('text=Skip for now');
    
    // Try to proceed without required fields
    await page.click('button:has-text("Next"), button:has-text("Continue")');
    
    // Button should be disabled
    await expect(page.locator('button:has-text("Next"), button:has-text("Continue")')).toBeDisabled();
    
    // Fill required fields
    await page.fill('[name="name"]', 'Test User');
    await page.fill('[name="company"]', 'Test Company');
    
    // Button should now be enabled
    await expect(page.locator('button:has-text("Next"), button:has-text("Continue")')).toBeEnabled();
  });

  test('Onboarding A/B testing', async ({ page }) => {
    await page.goto('/onboarding-flow');
    
    // Skip to step 2
    await page.click('text=Skip for now');
    
    // Fill required fields
    await page.fill('[name="name"]', 'Test User');
    await page.fill('[name="company"]', 'Test Company');
    
    // Check for A/B tested button text
    const nextButton = page.locator('button:has-text("Next"), button:has-text("Continue")');
    await expect(nextButton).toBeVisible();
    
    // Click and proceed to step 4
    await nextButton.click();
    await page.click('text=Skip for now');
    
    // Check for A/B tested completion button
    const completeButton = page.locator('button:has-text("Complete Setup"), button:has-text("Finish & Launch")');
    await expect(completeButton).toBeVisible();
  });

  test('Onboarding error handling', async ({ page }) => {
    // Mock network failure
    await page.route('**/api/onboarding', route => route.abort());
    
    await page.goto('/onboarding-flow');
    
    // Complete the flow
    await page.click('text=Skip for now');
    await page.fill('[name="name"]', 'Test User');
    await page.fill('[name="company"]', 'Test Company');
    await page.click('button:has-text("Next"), button:has-text("Continue")');
    await page.click('text=Skip for now');
    await page.click('button:has-text("Complete Setup"), button:has-text("Finish & Launch")');
    
    // Should show error message
    await expect(page.locator('text=Failed to connect to server')).toBeVisible();
  });

  test('Onboarding progress persistence', async ({ page }) => {
    await page.goto('/onboarding-flow');
    
    // Skip to step 2
    await page.click('text=Skip for now');
    
    // Fill partial data
    await page.fill('[name="name"]', 'Test User');
    await page.fill('[name="company"]', 'Test Company');
    
    // Refresh page
    await page.reload();
    
    // Should maintain progress and data
    await expect(page.locator('text=Step 2 of 4')).toBeVisible();
    await expect(page.locator('[name="name"]')).toHaveValue('Test User');
    await expect(page.locator('[name="company"]')).toHaveValue('Test Company');
  });
});
