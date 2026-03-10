import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

export let errorRate = new Rate('errors');

const BASE_URL = __ENV.API_BASE_URL || 'https://fikirisolutions.com';

export let options = {
  stages: [
    { duration: '30s', target: 10 },
    { duration: '1m', target: 20 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<5000'],
    http_req_failed: ['rate<0.2'],
    errors: ['rate<0.2'],
  },
};

export default function () {
  const res = http.get(`${BASE_URL}/api/health`);
  const ok = check(res, { 'health status 200': (r) => r.status === 200 });
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
