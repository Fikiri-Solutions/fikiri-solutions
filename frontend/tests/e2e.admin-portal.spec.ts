/**
 * Platform admin portal smoke / regression (Playwright).
 *
 * Requires backend ADMIN_USER_IDS to include the admin-e2e user
 * (local default: admin@example.com → id 110; override via ADMIN_E2E_USER_IDS).
 * MFA is left off for local smoke (ADMIN_MFA_REQUIRED=false in playwright webServer).
 */
import { test, expect, type Page, type APIResponse } from '@playwright/test'

async function bearerHeaders(page: Page): Promise<Record<string, string>> {
  await page.goto('/dashboard')
  const token = await page.evaluate(() => localStorage.getItem('fikiri-token') || '')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function platformMe(page: Page): Promise<APIResponse> {
  const headers = await bearerHeaders(page)
  return page.request.get('/api/admin/platform/me', { headers })
}

test.describe('Admin portal access control', () => {
  test('non-operator is redirected away from /admin', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'admin-e2e', 'Uses regular user storage state')
    await page.goto('/admin')
    await page.waitForURL(/\/(dashboard|login|onboarding)/, { timeout: 20000 })
    await expect(page).not.toHaveURL(/\/admin(\/|$)/)
  })
})

test.describe('Admin portal operator surfaces', () => {
  test.beforeEach(({}, testInfo) => {
    test.skip(testInfo.project.name !== 'admin-e2e', 'Requires admin-e2e auth storage')
  })

  test('operator can open overview, tenants, security, and audit', async ({ page }) => {
    const meRes = await platformMe(page)
    if (meRes.status() === 403) {
      test.skip(
        true,
        'Backend ADMIN_USER_IDS does not include this admin user — set ADMIN_E2E_USER_IDS for local E2E',
      )
    }
    expect(meRes.status(), await meRes.text()).toBe(200)

    await page.goto('/admin')
    await expect(page).toHaveURL(/\/admin\/?$/, { timeout: 15000 })
    await expect(page.getByRole('heading', { name: /platform admin/i })).toBeVisible({
      timeout: 15000,
    })
    await expect(page.getByText(/master access for fikiri platform operators/i)).toBeVisible()

    await page.getByRole('link', { name: /^tenants$/i }).click()
    await expect(page).toHaveURL(/\/admin\/tenants/)
    await expect(page.getByText(/tenant/i).first()).toBeVisible({ timeout: 15000 })

    await page.getByRole('link', { name: /mfa security/i }).click()
    await expect(page).toHaveURL(/\/admin\/security/)
    await expect(page.getByText(/mfa|authenticator|totp|security|enroll/i).first()).toBeVisible({
      timeout: 15000,
    })

    await page.getByRole('link', { name: /audit log/i }).click()
    await expect(page).toHaveURL(/\/admin\/audit/)
    await expect(page.getByText(/audit|immutable record|operator actions/i).first()).toBeVisible({
      timeout: 15000,
    })
  })

  test('tenant directory loads and can open a tenant detail when rows exist', async ({ page }) => {
    const headers = await bearerHeaders(page)
    const meRes = await page.request.get('/api/admin/platform/me', { headers })
    if (meRes.status() === 403) {
      test.skip(true, 'ADMIN_USER_IDS does not include this admin user')
    }
    expect(meRes.status(), await meRes.text()).toBe(200)

    await page.goto('/admin/tenants')
    await expect(page).toHaveURL(/\/admin\/tenants/)

    const listRes = await page.request.get('/api/admin/platform/tenants?limit=20', { headers })
    expect(listRes.status()).toBe(200)
    const body = await listRes.json().catch(() => ({}))
    const items = body?.data?.items || body?.items || []
    if (!Array.isArray(items) || items.length === 0) {
      await expect(page.locator('body')).toContainText(/tenant|no |empty|search/i)
      return
    }

    const firstId = items[0].id ?? items[0].user_id
    await page.goto(`/admin/tenants/${firstId}`)
    await expect(page).toHaveURL(new RegExp(`/admin/tenants/${firstId}`))
    await expect(page.locator('body')).toContainText(new RegExp(`${firstId}|tenant|email|sync`, 'i'))
  })

  test('platform me succeeds for operator and response stays sanitized', async ({ page }) => {
    const me = await platformMe(page)
    if (me.status() === 403) {
      test.skip(true, 'ADMIN_USER_IDS does not include this admin user')
    }
    expect(me.status(), await me.text()).toBe(200)
    const payload = await me.json()
    const raw = JSON.stringify(payload).toLowerCase()
    expect(raw).not.toContain('access_token')
    expect(raw).not.toContain('refresh_token')
    expect(raw).not.toContain('totp_secret')
    expect(raw).not.toContain('recovery_code')
  })
})
