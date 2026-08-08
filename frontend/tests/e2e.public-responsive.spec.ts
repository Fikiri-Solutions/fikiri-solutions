/**
 * Public marketing responsive smoke — no auth setup.
 * One test per viewport (loops routes) to keep CI cheap while catching overflow.
 */
import { expect, test } from '@playwright/test'

const ROUTES = ['/', '/about', '/pricing', '/login', '/signup', '/forgot-password'] as const

const VIEWPORTS = [
  { width: 375, height: 667, label: '375x667' },
  { width: 390, height: 844, label: '390x844' },
  { width: 768, height: 1024, label: '768x1024' },
  { width: 1280, height: 720, label: '1280x720' },
] as const

async function assertNoHorizontalOverflow(page: import('@playwright/test').Page, route: string, label: string) {
  const overflow = await page.evaluate(() => {
    const de = document.documentElement
    return {
      overflow: de.scrollWidth > de.clientWidth + 1,
      scrollWidth: de.scrollWidth,
      clientWidth: de.clientWidth,
    }
  })
  expect(
    overflow.overflow,
    `overflow at ${route} ${label}: ${overflow.scrollWidth}>${overflow.clientWidth}`
  ).toBe(false)
}

async function assertRouteChrome(page: import('@playwright/test').Page, route: (typeof ROUTES)[number]) {
  await expect(page.locator('header')).toBeVisible({ timeout: 10_000 })

  switch (route) {
    case '/':
      await expect(page.getByRole('link', { name: /get started/i }).first()).toBeVisible({
        timeout: 10_000,
      })
      // Carousel sits lower on the page — attached is enough for smoke
      await expect(page.locator('#client-partnerships')).toBeAttached({ timeout: 10_000 })
      break
    case '/about':
      await expect(
        page.getByRole('heading', {
          name: /we build systems around how your business actually works/i,
        })
      ).toBeVisible({
        timeout: 10_000,
      })
      break
    case '/pricing':
      await expect(page.getByRole('heading', { name: /plans for businesses/i })).toBeVisible({
        timeout: 10_000,
      })
      await expect(page.getByRole('heading', { name: /starter/i }).first()).toBeVisible({
        timeout: 10_000,
      })
      break
    case '/login':
      await expect(page.locator('#login-form')).toBeVisible({ timeout: 10_000 })
      break
    case '/signup':
      await expect(page.getByRole('heading', { name: /join fikiri/i })).toBeVisible({
        timeout: 10_000,
      })
      break
    case '/forgot-password':
      await expect(page.getByRole('heading', { name: /forgot password/i })).toBeVisible({
        timeout: 10_000,
      })
      break
  }
}

for (const vp of VIEWPORTS) {
  test.describe(`public responsive ${vp.label}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } })

    test(`core public routes render without horizontal overflow`, async ({ page }) => {
      test.setTimeout(90_000)

      for (const route of ROUTES) {
        await page.goto(route, { waitUntil: 'domcontentloaded' })
        await assertRouteChrome(page, route)
        await assertNoHorizontalOverflow(page, route, vp.label)
      }
    })
  })
}
