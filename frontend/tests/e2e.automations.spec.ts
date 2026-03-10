import { test, expect, type Page, type Route } from '@playwright/test'

const nowIso = new Date().toISOString()

async function fulfillApi(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  })
}

async function setupAutomationApiMocks(page: Page) {
  await page.route('**/api/automation/rules**', async (route) => {
    const method = route.request().method()
    if (method === 'GET') {
      return fulfillApi(route, {
        success: true,
        data: {
          rules: [
            {
              id: 41,
              name: 'Send Leads to Your Tools',
              description: 'Webhook sync',
              trigger_type: 'email_received',
              action_type: 'trigger_webhook',
              action_parameters: {
                slug: 'email_sheets',
                webhook_url: 'https://example.com/webhook',
                payload: { source: 'test' },
              },
              status: 'active',
            },
          ],
        },
      })
    }

    if (method === 'POST') {
      return fulfillApi(route, {
        success: true,
        data: { rule: { id: 99 } },
      })
    }

    return route.continue()
  })

  await page.route('**/api/automation/rules/*', async (route) => {
    if (route.request().method() === 'PUT') {
      return fulfillApi(route, { success: true, data: { rule: { id: 41 } } })
    }
    return route.continue()
  })

  await page.route('**/api/automation/safety-status**', async (route) => {
    return fulfillApi(route, {
      success: true,
      data: {
        automation_enabled: true,
        safety_level: 'normal',
        restrictions: [],
      },
    })
  })

  await page.route('**/api/automation/suggestions**', async (route) => {
    return fulfillApi(route, {
      success: true,
      data: {
        suggestions: [
          { name: 'Auto-qualify urgent leads', description: 'Use keyword-based prioritization' },
        ],
      },
    })
  })

  await page.route('**/api/automation/capabilities**', async (route) => {
    return fulfillApi(route, {
      success: true,
      data: {
        capabilities: [
          { action_type: 'update_crm_field', capability: 'implemented' },
          { action_type: 'send_notification', capability: 'partial' },
          { action_type: 'trigger_webhook', capability: 'implemented' },
          { action_type: 'schedule_follow_up', capability: 'implemented' },
        ],
      },
    })
  })

  await page.route('**/api/automation/metrics**', async (route) => {
    return fulfillApi(route, {
      success: true,
      data: {
        queued: 2,
        running: 1,
        success: 12,
        failed: 1,
        dead: 0,
        success_rate_24h: 0.92,
        p95_duration_seconds: 4,
      },
    })
  })

  await page.route('**/api/automation/logs**', async (route) => {
    return fulfillApi(route, {
      success: true,
      data: {
        logs: [
          {
            execution_id: 501,
            rule_id: 41,
            rule_name: 'Send Leads to Your Tools',
            slug: 'email_sheets',
            status: 'success',
            action_result: { message: 'Webhook delivered', summary: 'Delivered' },
            executed_at: nowIso,
            error_message: null,
          },
        ],
      },
    })
  })

  await page.route('**/api/automation/test/preset', async (route) => {
    return fulfillApi(route, { success: true, data: { total_executed: 1 } })
  })
}

test.describe('Automations Launch Flows', () => {
  test('renders automations dashboard with preset cards and safety status', async ({ page }) => {
    await setupAutomationApiMocks(page)

    await page.goto('/automations')

    await expect(page.getByRole('heading', { name: 'Workflow Automations' })).toBeVisible()
    await expect(page.getByText('Gmail → CRM')).toBeVisible()
    await expect(page.getByText('Lead Scoring')).toBeVisible()
    await expect(page.locator('[data-preset-id="email_sheets"]')).toBeVisible()
    await expect(page.getByText('Calendar follow-ups')).toBeVisible()
    await expect(page.getByText('Enabled · normal')).toBeVisible()
  })

  test('can run preset tests and activate a preset from UI', async ({ page }) => {
    let testPresetCalls = 0
    let writeRuleCalls = 0

    await page.route('**/automation/rules*', async (route) => {
      const method = route.request().method()
      if (method === 'GET') {
        return fulfillApi(route, { success: true, data: { rules: [] } })
      }
      if (method === 'POST' || method === 'PUT') {
        writeRuleCalls += 1
        return fulfillApi(route, { success: true, data: { rule: { id: 111 } } })
      }
      return route.continue()
    })

    await page.route('**/api/automation/test/preset', async (route) => {
      testPresetCalls += 1
      await fulfillApi(route, { success: true, data: { total_executed: 1 } })
    })

    await page.route('**/api/automation/safety-status**', async (route) => {
      return fulfillApi(route, { success: true, data: { automation_enabled: true, safety_level: 'normal' } })
    })

    await page.route('**/api/automation/suggestions**', async (route) => {
      return fulfillApi(route, { success: true, data: { suggestions: [] } })
    })

    await page.route('**/api/automation/logs**', async (route) => {
      return fulfillApi(route, { success: true, data: { logs: [] } })
    })

    await page.goto('/automations')

    const gmailCard = page.locator('[data-preset-id="gmail_crm"]')
    await expect(gmailCard).toBeVisible()

    await gmailCard.getByRole('button', { name: 'Run Test' }).click()
    await expect.poll(() => testPresetCalls).toBe(1)

    await gmailCard.getByRole('button', { name: 'Save & Activate' }).click()
    await expect.poll(() => writeRuleCalls).toBeGreaterThanOrEqual(1)
  })
})
