import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

/**
 * Load profile against the live Fikiri API contract.
 *
 * Env (optional):
 *   API_BASE_URL / PERF_API_BASE_URL — backend root, e.g. https://fikirisolutions.onrender.com
 *   FRONTEND_URL — marketing site, e.g. https://www.fikirisolutions.com
 *
 * Dashboard industry routes live under /api/dashboard/industry/* (not /api/industry/*).
 */

export const errorRate = new Rate('errors');

export const options = {
  stages: [
    { duration: '2m', target: 100 },
    { duration: '5m', target: 100 },
    { duration: '2m', target: 200 },
    { duration: '5m', target: 200 },
    { duration: '2m', target: 0 },
  ],
  thresholds: {
    // Mixed API + HTML; DB-backed routes need more headroom than health-only.
    http_req_duration: ['p(95)<5000'],
    http_req_failed: ['rate<0.1'],
    errors: ['rate<0.1'],
  },
};

const BASE_URL = __ENV.API_BASE_URL || __ENV.PERF_API_BASE_URL || 'https://fikirisolutions.onrender.com';
const FRONTEND_URL = __ENV.FRONTEND_URL || 'https://www.fikirisolutions.com';

function parseJson(r) {
  try {
    return JSON.parse(r.body);
  } catch (e) {
    return null;
  }
}

export default function () {
  // 1) Health
  const healthResponse = http.get(`${BASE_URL}/api/health`);
  const healthCheck = check(healthResponse, {
    'health status 200': (r) => r.status === 200,
    'health response time < 2s': (r) => r.timings.duration < 2000,
    'health has status field': (r) => {
      const body = parseJson(r);
      return (
        body &&
        ['healthy', 'degraded', 'unhealthy'].includes(body.status)
      );
    },
  });
  errorRate.add(!healthCheck);

  // 2) Industry prompts (public GET)
  const promptsResponse = http.get(`${BASE_URL}/api/dashboard/industry/prompts`);
  const promptsCheck = check(promptsResponse, {
    'prompts status 200': (r) => r.status === 200,
    'prompts response time < 5s': (r) => r.timings.duration < 5000,
    'prompts envelope success': (r) => {
      const body = parseJson(r);
      return body && body.success === true && body.data && body.data.prompts;
    },
    'prompts has known industries': (r) => {
      const body = parseJson(r);
      const p = body && body.data && body.data.prompts;
      return !!(p && p.restaurant && p.medical_practice && p.real_estate);
    },
  });
  errorRate.add(!promptsCheck);

  // 3) Industry pricing tiers (public GET)
  const pricingResponse = http.get(`${BASE_URL}/api/dashboard/industry/pricing`);
  const pricingCheck = check(pricingResponse, {
    'pricing status 200': (r) => r.status === 200,
    'pricing response time < 5s': (r) => r.timings.duration < 5000,
    'pricing envelope success': (r) => {
      const body = parseJson(r);
      return body && body.success === true && body.data && body.data.pricing_tiers;
    },
    'pricing has tier keys': (r) => {
      const body = parseJson(r);
      const tiers = body && body.data && body.data.pricing_tiers;
      return !!(tiers && typeof tiers === 'object' && Object.keys(tiers).length > 0);
    },
  });
  errorRate.add(!pricingCheck);

  // 4) Industry usage (defaults user_id=1 when unauthenticated — matches dashboard UI probes)
  const usageResponse = http.get(`${BASE_URL}/api/dashboard/industry/usage?user_id=1`);
  const usageCheck = check(usageResponse, {
    'usage status 200': (r) => r.status === 200,
    'usage response time < 8s': (r) => r.timings.duration < 8000,
    'usage envelope success': (r) => {
      const body = parseJson(r);
      return body && body.success === true && body.data && body.data.usage;
    },
    'usage has tier': (r) => {
      const body = parseJson(r);
      const u = body && body.data && body.data.usage;
      return !!(u && u.tier !== undefined);
    },
  });
  errorRate.add(!usageCheck);

  // 5) Frontend marketing (SPA — typically 200 HTML)
  const landingResponse = http.get(`${FRONTEND_URL}/home`);
  const landingCheck = check(landingResponse, {
    'landing status 200': (r) => r.status === 200,
    'landing response time < 5s': (r) => r.timings.duration < 5000,
    'landing is HTML': (r) =>
      (r.headers['Content-Type'] && String(r.headers['Content-Type']).includes('text/html')) ||
      (r.body && r.body.length > 100),
  });
  errorRate.add(!landingCheck);

  const industryPageResponse = http.get(`${FRONTEND_URL}/industry`);
  const industryPageCheck = check(industryPageResponse, {
    'industry page status 200': (r) => r.status === 200,
    'industry page response time < 5s': (r) => r.timings.duration < 5000,
  });
  errorRate.add(!industryPageCheck);

  // 6) Root document (avoids brittle hashed /assets/* paths from Vite builds)
  const rootResponse = http.get(`${FRONTEND_URL}/`);
  const rootCheck = check(rootResponse, {
    'frontend root 200': (r) => r.status === 200,
    'frontend root time < 5s': (r) => r.timings.duration < 5000,
  });
  errorRate.add(!rootCheck);

  sleep(1);
}

export function handleSummary(data) {
  return {
    'k6-results/performance-summary.json': JSON.stringify(
      {
        timestamp: new Date().toISOString(),
        test_duration: data.metrics.test_duration.values.avg,
        total_requests: data.metrics.http_reqs.values.count,
        failed_requests: data.metrics.http_req_failed.values.count,
        error_rate: data.metrics.errors.values.rate,
        avg_response_time: data.metrics.http_req_duration.values.avg,
        p95_response_time: data.metrics.http_req_duration.values['p(95)'],
        p99_response_time: data.metrics.http_req_duration.values['p(99)'],
        requests_per_second: data.metrics.http_reqs.values.rate,
        summary: {
          status: data.metrics.errors.values.rate < 0.1 ? 'PASS' : 'FAIL',
          performance_score:
            data.metrics.http_req_duration.values['p(95)'] < 2000
              ? 'EXCELLENT'
              : data.metrics.http_req_duration.values['p(95)'] < 5000
                ? 'GOOD'
                : 'NEEDS_IMPROVEMENT',
          recommendations: generateRecommendations(data),
        },
      },
      null,
      2
    ),
  };
}

function generateRecommendations(data) {
  const recommendations = [];
  const p95 = data.metrics.http_req_duration.values['p(95)'];
  if (p95 > 5000) {
    recommendations.push('Consider caching or DB read replicas for hot dashboard paths');
    recommendations.push('Review slow queries and indexes on billing_usage / analytics_events');
  }
  if (data.metrics.errors.values.rate > 0.05) {
    recommendations.push('Investigate failed checks (non-2xx or assertion failures)');
  }
  if (data.metrics.http_reqs.values.rate < 10) {
    recommendations.push('Increase VUs or reduce sleep() if throughput is the goal');
  }
  return recommendations;
}
