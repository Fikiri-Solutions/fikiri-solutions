/**
 * Lightweight browser smoke for the homepage Sector Fit Explorer.
 * Runs under the `public-e2e` Playwright project (no auth setup required).
 */
import { test, expect, type ConsoleMessage } from '@playwright/test'

/** Skip hero intro so Sector Fit assertions are not coupled to entrance timing. */
async function skipHeroIntro(page: import('@playwright/test').Page) {
  await page.addInitScript(() => {
    try {
      sessionStorage.setItem('fikiri-hero-seen', '1')
    } catch {
      /* ignore */
    }
  })
}

test.describe('Sector Fit Explorer — browser smoke', () => {
  test('desktop: explorer on home, not on about; CTAs and interactions hold', async ({ page }) => {
    test.setTimeout(90_000)
    const pageErrors: string[] = []
    const errorLogs: string[] = []

    page.on('pageerror', (err) => {
      pageErrors.push(String(err))
    })
    page.on('console', (msg: ConsoleMessage) => {
      if (msg.type() === 'error') errorLogs.push(msg.text())
    })

    await skipHeroIntro(page)
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')

    await expect(page.getByRole('heading', { name: /see how fikiri fits your sector/i })).toBeVisible({
      timeout: 15_000,
    })
    await expect(page.getByRole('textbox', { name: /tell us what your business does/i })).toBeVisible()
    await expect(page.getByRole('link', { name: /^get started$/i }).first()).toBeVisible()
    await expect(page.getByRole('link', { name: /start a workflow conversation/i }).first()).toBeVisible()
    await expect(page.getByRole('link', { name: /see plans/i }).first()).toBeVisible()

    const input = page.getByRole('textbox', { name: /tell us what your business does/i })

    // Invalid input should not break the hero
    await input.fill('asdfghjkl')
    await expect(page.getByText(/clearer business description/i).first()).toBeVisible()
    await expect(page.getByRole('link', { name: /^get started$/i }).first()).toBeVisible()

    // Unicode / accented paste
    await input.fill('We’re a café / bakery!!!')
    await expect(page.getByText(/restaurants, catering/i).first()).toBeVisible({ timeout: 5000 })

    // Clear resets explorer
    const clear = page.getByRole('button', { name: /clear business description/i })
    if (await clear.isVisible()) {
      await clear.click()
      await expect(input).toHaveValue('')
    }

    // Emoji-heavy paste stays invalid, page remains interactive
    await input.fill('🔥🔥🔥🔥🔥')
    await expect(page.getByText(/clearer business description/i).first()).toBeVisible()

    // Near max length should not freeze the page
    await input.fill(`HVAC ${'x'.repeat(480)}`)
    await expect(page.getByRole('link', { name: /see plans/i }).first()).toBeVisible()

    // Keyboard focus still reaches interactive chrome
    await page.keyboard.press('Tab')
    await expect(page.getByRole('link', { name: /^get started$/i }).first()).toBeVisible()

    // About must not host the explorer
    await page.goto('/about')
    await page.waitForLoadState('domcontentloaded')
    await expect(
      page.getByRole('heading', {
        name: /we build systems around how your business actually works/i,
      })
    ).toBeVisible()
    await expect(page.getByRole('heading', { name: /see how fikiri fits your sector/i })).toHaveCount(0)

    expect(pageErrors, `pageerrors: ${pageErrors.join(' | ')}`).toEqual([])
    const filteredLogs = errorLogs.filter(
      (line) =>
        !/Download the React DevTools/i.test(line) &&
        !/third-party/i.test(line) &&
        !/favicon/i.test(line)
    )
    expect(filteredLogs, `console errors: ${filteredLogs.join(' | ')}`).toEqual([])
  })

  test('mobile viewport: explorer remains usable', async ({ page }) => {
    test.setTimeout(60_000)
    await page.setViewportSize({ width: 390, height: 844 })
    await skipHeroIntro(page)
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')

    await expect(page.getByRole('heading', { name: /see how fikiri fits your sector/i })).toBeVisible({
      timeout: 15_000,
    })
    const input = page.getByRole('textbox', { name: /tell us what your business does/i })
    await expect(input).toBeVisible()
    await input.fill('HVAC')
    await expect(page.getByText(/strong match|trades & home services/i).first()).toBeVisible({
      timeout: 5000,
    })
    await expect(page.getByRole('link', { name: /^get started$/i }).first()).toBeVisible()
    await expect(page.getByRole('link', { name: /start a workflow conversation/i }).first()).toBeVisible()
  })
})
