import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

export let errorRate = new Rate('errors');

const BASE_URL = __ENV.API_BASE_URL || __ENV.PERF_API_BASE_URL || 'http://localhost:5000';
const AUTOMATION_USER_ID = __ENV.AUTOMATION_USER_ID || '1';
const AUTOMATION_PRESET_ID = __ENV.AUTOMATION_PRESET_ID || 'inbound_crm_sync';
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

function checkReadResponse(name, res) {
  // 200 is expected when auth/user context is valid. 401/403/429 are acceptable guardrails.
  return check(res, {
    [`${name} status acceptable`]: (r) => [200, 401, 403, 429].includes(r.status),
  });
}

export let options = {
  stages: [
    { duration: '30s', target: 10 },
    { duration: '1m', target: 30 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<5000'],
    http_req_failed: ['rate<0.2'],
    errors: ['rate<0.2'],
  },
};

export default function () {
  const checks = [];

  const health = http.get(`${BASE_URL}/api/health`);
  checks.push(check(health, { 'health status 200': (r) => r.status === 200 }));

  const rules = readWithUser('/api/automation/rules');
  checks.push(checkReadResponse('automation rules', rules));

  const metrics = readWithUser('/api/automation/metrics?hours=24');
  checks.push(checkReadResponse('automation metrics', metrics));

  const logs = readWithUser('/api/automation/logs?limit=20');
  checks.push(checkReadResponse('automation logs', logs));

  const suggestions = readWithUser('/api/automation/suggestions');
  checks.push(checkReadResponse('automation suggestions', suggestions));

  const preset = http.post(
    `${BASE_URL}/api/automation/test/preset`,
    JSON.stringify({
      preset_id: AUTOMATION_PRESET_ID,
      user_id: Number(AUTOMATION_USER_ID),
    }),
    { headers: JSON_HEADERS }
  );
  checks.push(
    check(preset, {
      'automation preset status acceptable': (r) => [200, 400, 401, 403, 429, 501].includes(r.status),
    })
  );

  const ok = checks.every(Boolean);
  errorRate.add(!ok);
  sleep(0.5);
}

export function handleSummary(data) {
  return {
    'k6-results/stress-summary.json': JSON.stringify({
      timestamp: new Date().toISOString(),
      http_reqs: data.metrics.http_reqs && data.metrics.http_reqs.values ? data.metrics.http_reqs.values.count : 0,
      http_req_failed: data.metrics.http_req_failed && data.metrics.http_req_failed.values ? data.metrics.http_req_failed.values.rate : 0,
    }, null, 2),
  };
}
