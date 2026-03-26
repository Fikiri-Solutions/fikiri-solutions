/**
 * CRM "View trace" modal: lead CRM events → correlation IDs → stitched debug trace.
 * Mocks API responses so the suite does not depend on real crm_events / correlation data.
 */
import { test, expect, type Page, type Route } from '@playwright/test'

async function fulfillApi(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  })
}

const E2E_LEAD = {
  id: 9001,
  name: 'E2E Trace Lead',
  email: 'e2e-trace@example.test',
  company: 'Trace Co',
  stage: 'new',
  score: 7,
  last_contact: '2025-03-01T12:00:00Z',
  source: 'manual',
}

const CORR_ID = 'e2e-corr-trace-001'

/**
 * One handler for /api/crm/leads* so we never route.continue() /events to the real backend
 * (continue bypasses other registered mocks).
 */
async function setupCrmTraceApiMocks(page: Page) {
  await page.route('**/api/crm/leads**', async (route) => {
    if (route.request().method() !== 'GET') return route.continue()
    const path = new URL(route.request().url()).pathname
    if (/\/crm\/leads\/\d+\/events\/?$/.test(path)) {
      return fulfillApi(route, {
        success: true,
        message: 'CRM events retrieved successfully',
        data: {
          events: [
            {
              id: 1,
              created_at: '2025-03-02T10:00:00Z',
              event_type: 'lead.created',
              entity_type: 'lead',
              entity_id: E2E_LEAD.id,
              correlation_id: CORR_ID,
              status: 'success',
              source: 'e2e',
            },
          ],
          limit: 100,
          offset: 0,
        },
      })
    }
    if (path === '/api/crm/leads' || path.endsWith('/crm/leads')) {
      return fulfillApi(route, {
        success: true,
        message: 'Leads retrieved successfully',
        leads: [E2E_LEAD],
        pagination: {
          total_count: 1,
          returned_count: 1,
          limit: 100,
          offset: 0,
          has_more: false,
        },
        analytics: {},
      })
    }
    return route.continue()
  })

  await page.route('**/api/debug/correlation/**', async (route) => {
    if (route.request().method() !== 'GET') return route.continue()
    const url = route.request().url()
    if (!url.includes(encodeURIComponent(CORR_ID)) && !url.includes(CORR_ID)) {
      return route.continue()
    }
    return fulfillApi(route, {
      success: true,
      message: 'Correlation trace',
      data: {
        correlation_id: CORR_ID,
        user_id: 1,
        limits: { per_section: 50 },
        sections: {
          crm_events: [
            {
              created_at: '2025-03-02T10:00:00Z',
              event_type: 'lead.created',
              source: 'e2e',
              status: 'success',
            },
          ],
          email_events: [],
          ai_events: [],
          automation_run_events: [],
          automation_jobs: [],
          chatbot_content_events: [],
        },
        notes: [],
      },
    })
  })
}

test.describe('CRM View trace', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    if (!['e2e', 'admin-e2e'].includes(testInfo.project.name)) {
      test.skip()
    }
    await page.addInitScript(() => {
      const user = {
        id: 1,
        email: 'launch-test@example.com',
        name: 'E2E User',
        role: 'user',
        onboarding_completed: true,
        onboarding_step: 4,
      }
      localStorage.setItem('fikiri-user', JSON.stringify(user))
      localStorage.setItem('fikiri-user-id', String(user.id))
    })
  })

  test('opens modal, shows correlation from CRM events, loads stitched timeline', async ({ page }) => {
    await setupCrmTraceApiMocks(page)

    await page.goto('/crm')
    await page.waitForLoadState('networkidle')

    if (page.url().includes('/login')) {
      test.skip()
    }

    await expect(page.getByRole('heading', { name: /CRM - Lead Management/i })).toBeVisible({
      timeout: 15000,
    })

    // Draggable card can include "View trace" in a composite a11y name — require exact button name.
    await page.getByRole('button', { name: 'View trace', exact: true }).first().click()

    const traceModal = page.getByRole('dialog')
    await expect(page.getByRole('heading', { name: 'View trace', exact: true })).toBeVisible()
    await expect(traceModal.getByText(`E2E Trace Lead · ${E2E_LEAD.email}`)).toBeVisible()
    await expect(traceModal.getByText(CORR_ID)).toBeVisible()

    await traceModal.getByRole('button', { name: 'Load stitched trace' }).click()

    await expect(traceModal.getByText('Timeline', { exact: true })).toBeVisible({ timeout: 10000 })
    // JSON <pre> also contains "lead.created" — scope to timeline list
    await expect(traceModal.locator('ul').getByText('lead.created', { exact: true })).toBeVisible()
    await expect(traceModal.locator('ul').getByText('CRM', { exact: true }).first()).toBeVisible()
  })

  test('Escape closes the trace modal', async ({ page }) => {
    await setupCrmTraceApiMocks(page)
    await page.goto('/crm')
    await page.waitForLoadState('networkidle')
    if (page.url().includes('/login')) {
      test.skip()
    }

    await page.getByRole('button', { name: 'View trace', exact: true }).first().click()
    await expect(page.getByRole('heading', { name: 'View trace', exact: true })).toBeVisible()

    await page.keyboard.press('Escape')
    await expect(page.getByRole('heading', { name: 'View trace', exact: true })).not.toBeVisible()
  })
})
