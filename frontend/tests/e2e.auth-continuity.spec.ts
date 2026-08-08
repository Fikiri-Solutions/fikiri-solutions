/**
 * Mobile auth / onboarding continuity smokes — no auth setup required.
 */
import { expect, test } from '@playwright/test'

const VIEWPORTS = [
  { width: 390, height: 844, label: '390x844' },
  { width: 844, height: 390, label: '844x390-L' },
  { width: 768, height: 1024, label: '768x1024' },
] as const

async function noHorizontalOverflow(page: import('@playwright/test').Page) {
  const overflow = await page.evaluate(() => {
    const de = document.documentElement
    return de.scrollWidth > de.clientWidth + 1
  })
  expect(overflow).toBe(false)
}

for (const vp of VIEWPORTS) {
  test.describe(`auth continuity ${vp.label}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } })

    test('login, signup, verify-email, and public entry points stay usable', async ({ page }) => {
      test.setTimeout(90_000)

      await page.goto('/', { waitUntil: 'domcontentloaded' })
      await expect(page.locator('header')).toBeVisible({ timeout: 10_000 })
      await expect(page.getByRole('link', { name: /get started/i }).first()).toBeVisible({
        timeout: 10_000,
      })
      await expect(page.getByRole('button', { name: /open main menu/i })).toBeVisible()
      await page.getByRole('button', { name: /open main menu/i }).click()
      await expect(page.getByRole('link', { name: /^pricing$/i }).first()).toBeVisible({
        timeout: 5_000,
      })
      await noHorizontalOverflow(page)

      await page.goto('/', { waitUntil: 'domcontentloaded' })
      await expect(page.getByRole('button', { name: /pause carousel/i })).toBeVisible({
        timeout: 10_000,
      })
      await noHorizontalOverflow(page)

      await page.goto('/signup', { waitUntil: 'domcontentloaded' })
      await expect(page.getByRole('heading', { name: /join fikiri/i })).toBeVisible({
        timeout: 10_000,
      })
      await expect(page.getByLabel(/email address/i).first()).toBeVisible()
      await noHorizontalOverflow(page)

      await page.goto('/login', { waitUntil: 'domcontentloaded' })
      await expect(page.locator('#login-form')).toBeVisible({ timeout: 10_000 })
      await expect(page.getByLabel(/email address/i)).toBeVisible()
      await expect(page.getByLabel(/^password$/i)).toBeVisible()
      await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible()
      await noHorizontalOverflow(page)

      await page.goto('/verify-email?token=invalid-token-for-smoke', {
        waitUntil: 'domcontentloaded',
      })
      await expect(
        page.getByRole('heading', { name: /verification link expired|verifying your email/i })
      ).toBeVisible({ timeout: 15_000 })
      await expect(page.getByRole('heading', { name: /verification link expired/i })).toBeVisible({
        timeout: 15_000,
      })
      await expect(page.getByRole('link', { name: /^sign in$/i })).toBeVisible()
      await noHorizontalOverflow(page)

      await page.goto('/onboarding', { waitUntil: 'domcontentloaded' })
      await expect(page).toHaveURL(/\/login/, { timeout: 15_000 })
      await expect(page.locator('#login-form')).toBeVisible({ timeout: 10_000 })
    })
  })
}
