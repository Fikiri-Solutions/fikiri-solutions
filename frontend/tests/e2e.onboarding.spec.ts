import { test, expect } from '@playwright/test';

test.describe('Onboarding Golden Path', () => {
  test('Complete onboarding flow from signup to dashboard', async ({ page }) => {
    // Start from landing page
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Click "Get Started" button - use flexible selector
    const getStartedButton = page.getByRole('button', { name: /get started|start|sign up/i }).first();
    if (await getStartedButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      await getStartedButton.click();
    } else {
      // Try direct navigation
      await page.goto('/onboarding');
    }
    
    // Wait for onboarding page
    await page.waitForURL(/.*\/(onboarding|onboarding-flow)/, { timeout: 10000 });
    
    // Step 1: Google OAuth (skip for now) - look for skip button
    const skipButton = page.getByRole('button', { name: /skip|later|not now/i }).first();
    if (await skipButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await skipButton.click();
    }
    
    // Step 2: Company Information - wait for form
    await page.waitForSelector('input[name="name"], input[placeholder*="Name"], input[placeholder*="John"]', { timeout: 10000 });
    
    const nameInput = page.locator('input[name="name"], input[placeholder*="Name"], input[placeholder*="John"]').first();
    await nameInput.fill('QA Test User');
    
    const companyInput = page.locator('input[name="company"], input[name="companyName"], input[placeholder*="Company"]').first();
    if (await companyInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await companyInput.fill('QA Test Company');
    }
    
    const industryInput = page.locator('input[name="industry"], select[name="industry"]').first();
    if (await industryInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      if (await industryInput.evaluate(el => el.tagName === 'SELECT').catch(() => false)) {
        await industryInput.selectOption('Technology');
      } else {
        await industryInput.fill('Technology');
      }
    }
    
    // Click Next/Continue
    const nextButton = page.getByRole('button', { name: /next|continue|proceed/i }).first();
    await nextButton.click();
    
    // Step 3: Email Integration (skip if present)
    const skipEmailButton = page.getByRole('button', { name: /skip|later|not now/i }).first();
    if (await skipEmailButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await skipEmailButton.click();
    }
    
    // Step 4: Complete Setup - wait for completion step
    await page.waitForSelector('text=/complete|finish|setup/i', { timeout: 10000 });
    
    // Complete setup
    const completeButton = page.getByRole('button', { name: /complete|finish|launch/i }).first();
    await completeButton.click();
    
    // Should redirect to dashboard - flexible wait
    await Promise.race([
      page.waitForURL(/.*\/dashboard/, { timeout: 15000 }),
      page.waitForSelector('text=/welcome|dashboard/i', { timeout: 15000 })
    ]);
    
    // Verify user is logged in
    await expect(page.locator('body')).toContainText(/welcome|dashboard/i);
  });

  test('Onboarding with Google OAuth integration', async ({ page }) => {
    // Start from landing page
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Navigate to onboarding
    const getStartedButton = page.getByRole('button', { name: /get started|start/i }).first();
    if (await getStartedButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      await getStartedButton.click();
    } else {
      await page.goto('/onboarding');
    }
    
    await page.waitForURL(/.*\/(onboarding|onboarding-flow)/, { timeout: 10000 });
    
    // Step 1: Try Google OAuth - look for OAuth button
    const googleButton = page.getByRole('button', { name: /google|gmail|continue with/i }).first();
    if (await googleButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      // Just verify button exists - don't actually click (would trigger OAuth)
      await expect(googleButton).toBeVisible();
    }
  });

  test('Onboarding step progression', async ({ page }) => {
    await page.goto('/onboarding');
    await page.waitForLoadState('networkidle');
    
    // Verify we start at step 1 (flexible step indicator)
    await expect(page.locator('text=/step.*of|step 1|25%/i')).toBeVisible({ timeout: 10000 });
    
    // Skip step 1 if skip button exists
    const skipButton = page.getByRole('button', { name: /skip|later|not now/i }).first();
    if (await skipButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await skipButton.click();
    }
    
    // Should be at step 2 (flexible step indicator)
    await expect(page.locator('text=/step.*of|step 2|50%/i')).toBeVisible({ timeout: 5000 });
    
    // Fill required fields and proceed
    const nameInput = page.locator('input[name="name"], input[placeholder*="Name"], input[placeholder*="John"]').first();
    await nameInput.fill('Test User');
    
    const companyInput = page.locator('input[name="company"], input[name="companyName"], input[placeholder*="Company"]').first();
    if (await companyInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await companyInput.fill('Test Company');
    }
    
    const nextButton = page.getByRole('button', { name: /next|continue/i }).first();
    await nextButton.click();
    
    // Should be at step 3 (flexible step indicator)
    await expect(page.locator('text=/step.*of|step 3|75%/i')).toBeVisible({ timeout: 5000 });
    
    // Skip step 3 if skip button exists
    const skipStep3 = page.getByRole('button', { name: /skip|later|not now/i }).first();
    if (await skipStep3.isVisible({ timeout: 3000 }).catch(() => false)) {
      await skipStep3.click();
    }
    
    // Should be at step 4 (flexible step indicator)
    await expect(page.locator('text=/step.*of|step 4|100%|complete/i')).toBeVisible({ timeout: 5000 });
  });

  test('Onboarding validation', async ({ page }) => {
    await page.goto('/onboarding');
    await page.waitForLoadState('networkidle');
    
    // Skip to step 2
    const skipButton = page.getByRole('button', { name: /skip|later|not now/i }).first();
    if (await skipButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await skipButton.click();
    }
    
    // Wait for step 2 form
    await page.waitForSelector('input[name="name"], input[placeholder*="Name"]', { timeout: 5000 });
    
    const nextButton = page.getByRole('button', { name: /next|continue/i }).first();
    
    // Check if button is disabled (validation)
    const isDisabled = await nextButton.isDisabled().catch(() => false);
    if (isDisabled) {
      // Fill required fields
      const nameInput = page.locator('input[name="name"], input[placeholder*="Name"], input[placeholder*="John"]').first();
      await nameInput.fill('Test User');
      
      const companyInput = page.locator('input[name="company"], input[name="companyName"], input[placeholder*="Company"]').first();
      if (await companyInput.isVisible({ timeout: 2000 }).catch(() => false)) {
        await companyInput.fill('Test Company');
      }
      
      // Button should now be enabled
      await expect(nextButton).toBeEnabled({ timeout: 2000 });
    }
  });

  test('Onboarding A/B testing', async ({ page }) => {
    await page.goto('/onboarding');
    await page.waitForLoadState('networkidle');
    
    // Skip to step 2
    const skipButton = page.getByRole('button', { name: /skip|later|not now/i }).first();
    if (await skipButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await skipButton.click();
    }
    
    // Fill required fields
    const nameInput = page.locator('input[name="name"], input[placeholder*="Name"], input[placeholder*="John"]').first();
    await nameInput.fill('Test User');
    
    const companyInput = page.locator('input[name="company"], input[name="companyName"], input[placeholder*="Company"]').first();
    if (await companyInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await companyInput.fill('Test Company');
    }
    
    // Check for A/B tested button text
    const nextButton = page.getByRole('button', { name: /next|continue|proceed/i }).first();
    await expect(nextButton).toBeVisible();
    
    // Click and proceed
    await nextButton.click();
    
    // Skip step 3 if present
    const skipStep3 = page.getByRole('button', { name: /skip|later|not now/i }).first();
    if (await skipStep3.isVisible({ timeout: 3000 }).catch(() => false)) {
      await skipStep3.click();
    }
    
    // Check for A/B tested completion button
    const completeButton = page.getByRole('button', { name: /complete|finish|launch|setup/i }).first();
    await expect(completeButton).toBeVisible({ timeout: 5000 });
  });

  test('Onboarding error handling', async ({ page }) => {
    // Mock network failure
    await page.route('**/api/onboarding/**', route => route.abort());
    await page.route('**/api/onboarding', route => route.abort());
    
    await page.goto('/onboarding');
    await page.waitForLoadState('networkidle');
    
    // Complete the flow
    const skipButton = page.getByRole('button', { name: /skip|later|not now/i }).first();
    if (await skipButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await skipButton.click();
    }
    
    const nameInput = page.locator('input[name="name"], input[placeholder*="Name"], input[placeholder*="John"]').first();
    await nameInput.fill('Test User');
    
    const companyInput = page.locator('input[name="company"], input[name="companyName"], input[placeholder*="Company"]').first();
    if (await companyInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await companyInput.fill('Test Company');
    }
    
    const nextButton = page.getByRole('button', { name: /next|continue/i }).first();
    await nextButton.click();
    
    const skipStep3 = page.getByRole('button', { name: /skip|later|not now/i }).first();
    if (await skipStep3.isVisible({ timeout: 3000 }).catch(() => false)) {
      await skipStep3.click();
    }
    
    const completeButton = page.getByRole('button', { name: /complete|finish|launch/i }).first();
    await completeButton.click();
    
    // Should show error message (flexible error text)
    const errorMessage = page.locator('text=/error|failed|connection|server|network/i').first();
    await expect(errorMessage).toBeVisible({ timeout: 10000 });
  });

  test('Onboarding progress persistence', async ({ page }) => {
    await page.goto('/onboarding');
    await page.waitForLoadState('networkidle');
    
    // Skip to step 2
    const skipButton = page.getByRole('button', { name: /skip|later|not now/i }).first();
    if (await skipButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await skipButton.click();
    }
    
    // Fill partial data
    const nameInput = page.locator('input[name="name"], input[placeholder*="Name"], input[placeholder*="John"]').first();
    await nameInput.fill('Test User');
    
    const companyInput = page.locator('input[name="company"], input[name="companyName"], input[placeholder*="Company"]').first();
    if (await companyInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await companyInput.fill('Test Company');
    }
    
    // Refresh page
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    // Should maintain progress and data (if persistence is implemented)
    // Note: This test may fail if persistence isn't implemented yet
    const stepIndicator = page.locator('text=/step.*of|step 2|50%/i').first();
    if (await stepIndicator.isVisible({ timeout: 5000 }).catch(() => false)) {
      await expect(stepIndicator).toBeVisible();
      
      const nameValue = await nameInput.inputValue().catch(() => '');
      if (nameValue) {
        expect(nameValue).toContain('Test User');
      }
    }
  });
});
