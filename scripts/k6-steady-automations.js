import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// In steady-state, 429s should be rare; treat them as errors.
export const errorRate = new Rate('steady_errors');

const BASE_URL = __ENV.API_BASE_URL || 'http://localhost:5000';
const AUTOMATION_USER_ID = __ENV.AUTOMATION_USER_ID || '1';
const BEARER_TOKEN = __ENV.K6_BEARER_TOKEN || '';

const JSON_HEADERS = {
  'Content-Type': 'application/json',
  ...(BEARER_TOKEN ? { Authorization: `Bearer ${BEARER_TOKEN}` } : {}),
};

function readWithUser(path) {
  const separator = path.includes('?') ? '&' : '?';
  return http.get(`${BASE_URL}${path}${separator}user_id=${encodeURIComponent(AUTOMATION_USER_ID)}`, {
    headers: BEARER_TOKEN ? { Authorization: `Bearer ${BEARER_TOKEN}` } : {},
  });
}

export const options = {
  stages: [
    // Gentle ramp to simulate a handful of concurrent dashboards open
    { duration: '30s', target: 3 },
    { duration: '2m', target: 5 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<1000'], // p95 under 1s under normal load
    http_req_failed: ['rate<0.05'], // <5% failures is acceptable in steady state
    steady_errors: ['rate<0.05'],
  },
};

export default function () {
  const checks = [];

  // Health check: should be reliably 200 under normal load
  const health = http.get(`${BASE_URL}/api/health`);
  checks.push(
    check(health, {
      'health 200': (r) => r.status === 200,
    })
  );

  // Automations dashboard reads – typical polling pattern when a user has the page open.
  const rules = readWithUser('/api/automation/rules');
  checks.push(
    check(rules, {
      'rules 200': (r) => r.status === 200,
    })
  );

  const metrics = readWithUser('/api/automation/metrics?hours=24');
  checks.push(
    check(metrics, {
      'metrics 200': (r) => r.status === 200,
    })
  );

  const logs = readWithUser('/api/automation/logs?limit=20');
  checks.push(
    check(logs, {
      'logs 200': (r) => r.status === 200,
    })
  );

  const suggestions = readWithUser('/api/automation/suggestions');
  checks.push(
    check(suggestions, {
      'suggestions 200': (r) => r.status === 200,
    })
  );

  // Occasionally a user runs a preset test (low frequency write).
  if (Math.random() < 0.1) {
    const preset = http.post(
      `${BASE_URL}/api/automation/test/preset`,
      JSON.stringify({
        preset_id: 'inbound_crm_sync',
        user_id: Number(AUTOMATION_USER_ID),
      }),
      { headers: JSON_HEADERS }
    );
    checks.push(
      check(preset, {
        'preset acceptable (steady)': (r) => [200, 400, 401, 403].includes(r.status),
      })
    );
  }

  const ok = checks.every(Boolean);
  errorRate.add(!ok);

  // Think time: simulate a human reading/interacting, not a tight loop.
  sleep(3);
}

export function handleSummary(data) {
  return {
    'k6-results/steady-automations-summary.json': JSON.stringify(
      {
        timestamp: new Date().toISOString(),
        http_reqs: data.metrics.http_reqs?.values?.count ?? 0,
        http_req_failed: data.metrics.http_req_failed?.values?.rate ?? 0,
        steady_errors: data.metrics.steady_errors?.values?.rate ?? 0,
        p95_duration_ms: data.metrics.http_req_duration?.values?.['p(95)'] ?? null,
      },
      null,
      2
    ),
  };
}

