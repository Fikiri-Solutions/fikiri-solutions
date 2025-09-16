import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
export let errorRate = new Rate('errors');

export let options = {
  stages: [
    { duration: '2m', target: 100 }, // Ramp up to 100 users
    { duration: '5m', target: 100 }, // Stay at 100 users
    { duration: '2m', target: 200 }, // Ramp up to 200 users
    { duration: '5m', target: 200 }, // Stay at 200 users
    { duration: '2m', target: 0 },   // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<200'], // 95% of requests must complete below 200ms
    http_req_failed: ['rate<0.1'],   // Error rate must be below 10%
    errors: ['rate<0.1'],            // Custom error rate must be below 10%
  },
};

const BASE_URL = 'https://fikirisolutions.onrender.com';
const FRONTEND_URL = 'https://www.fikirisolutions.com';

export default function () {
  // Test 1: Backend Health Check
  let healthResponse = http.get(`${BASE_URL}/api/health`);
  let healthCheck = check(healthResponse, {
    'health endpoint status is 200': (r) => r.status === 200,
    'health endpoint response time < 200ms': (r) => r.timings.duration < 200,
    'health endpoint returns healthy status': (r) => {
      try {
        let body = JSON.parse(r.body);
        return body.status === 'healthy';
      } catch (e) {
        return false;
      }
    },
  });
  errorRate.add(!healthCheck);

  // Test 2: Industry Prompts Endpoint
  let promptsResponse = http.get(`${BASE_URL}/api/industry/prompts`);
  let promptsCheck = check(promptsResponse, {
    'industry prompts status is 200': (r) => r.status === 200,
    'industry prompts response time < 300ms': (r) => r.timings.duration < 300,
    'industry prompts returns success': (r) => {
      try {
        let body = JSON.parse(r.body);
        return body.success === true;
      } catch (e) {
        return false;
      }
    },
    'industry prompts has expected industries': (r) => {
      try {
        let body = JSON.parse(r.body);
        return body.prompts && 
               body.prompts.landscaping && 
               body.prompts.restaurant && 
               body.prompts.medical_practice;
      } catch (e) {
        return false;
      }
    },
  });
  errorRate.add(!promptsCheck);

  // Test 3: Frontend Landing Page
  let landingResponse = http.get(`${FRONTEND_URL}/home`);
  let landingCheck = check(landingResponse, {
    'landing page status is 200': (r) => r.status === 200,
    'landing page response time < 2s': (r) => r.timings.duration < 2000,
    'landing page contains headline': (r) => r.body.includes('Automate emails, leads, and workflows'),
    'landing page contains CTA buttons': (r) => r.body.includes('Try for Free') && r.body.includes('Watch Demo'),
  });
  errorRate.add(!landingCheck);

  // Test 4: Industry Automation Page
  let industryResponse = http.get(`${FRONTEND_URL}/industry`);
  let industryCheck = check(industryResponse, {
    'industry page status is 200': (r) => r.status === 200,
    'industry page response time < 2s': (r) => r.timings.duration < 2000,
    'industry page loads successfully': (r) => r.body.includes('Industry Automation'),
  });
  errorRate.add(!industryCheck);

  // Test 5: Static Assets
  let assetsResponse = http.get(`${FRONTEND_URL}/static/js/main.js`);
  let assetsCheck = check(assetsResponse, {
    'static assets status is 200': (r) => r.status === 200,
    'static assets response time < 1s': (r) => r.timings.duration < 1000,
  });
  errorRate.add(!assetsCheck);

  // Test 6: API Load Test - Industry Chat
  let chatPayload = JSON.stringify({
    industry: 'landscaping',
    client_id: 'k6-test-client',
    message: 'I need help with my landscaping business automation'
  });
  
  let chatResponse = http.post(`${BASE_URL}/api/industry/chat`, chatPayload, {
    headers: { 'Content-Type': 'application/json' },
  });
  
  let chatCheck = check(chatResponse, {
    'industry chat status is 200': (r) => r.status === 200,
    'industry chat response time < 5s': (r) => r.timings.duration < 5000,
    'industry chat returns response': (r) => {
      try {
        let body = JSON.parse(r.body);
        return body.response && body.success === true;
      } catch (e) {
        return false;
      }
    },
  });
  errorRate.add(!chatCheck);

  // Test 7: Analytics Endpoint
  let analyticsResponse = http.get(`${BASE_URL}/api/industry/analytics/k6-test-client`);
  let analyticsCheck = check(analyticsResponse, {
    'analytics endpoint status is 200': (r) => r.status === 200,
    'analytics response time < 1s': (r) => r.timings.duration < 1000,
  });
  errorRate.add(!analyticsCheck);

  // Test 8: Pricing Tiers Endpoint
  let pricingResponse = http.get(`${BASE_URL}/api/industry/pricing-tiers`);
  let pricingCheck = check(pricingResponse, {
    'pricing tiers status is 200': (r) => r.status === 200,
    'pricing tiers response time < 500ms': (r) => r.timings.duration < 500,
    'pricing tiers returns tiers': (r) => {
      try {
        let body = JSON.parse(r.body);
        return body.tiers && body.tiers.starter && body.tiers.professional;
      } catch (e) {
        return false;
      }
    },
  });
  errorRate.add(!pricingCheck);

  // Test 9: ROI Calculator Endpoint
  let roiPayload = JSON.stringify({
    industry: 'landscaping',
    hours_wasted_per_month: 20,
    monthly_revenue: 10000
  });
  
  let roiResponse = http.post(`${BASE_URL}/api/analytics/roi-calculator`, roiPayload, {
    headers: { 'Content-Type': 'application/json' },
  });
  
  let roiCheck = check(roiResponse, {
    'ROI calculator status is 200': (r) => r.status === 200,
    'ROI calculator response time < 2s': (r) => r.timings.duration < 2000,
    'ROI calculator returns analysis': (r) => {
      try {
        let body = JSON.parse(r.body);
        return body.roi_analysis && body.success === true;
      } catch (e) {
        return false;
      }
    },
  });
  errorRate.add(!roiCheck);

  // Test 10: Industry Benchmarks Endpoint
  let benchmarksResponse = http.get(`${BASE_URL}/api/analytics/industry-benchmarks?industry=landscaping`);
  let benchmarksCheck = check(benchmarksResponse, {
    'benchmarks status is 200': (r) => r.status === 200,
    'benchmarks response time < 1s': (r) => r.timings.duration < 1000,
  });
  errorRate.add(!benchmarksCheck);

  // Wait between requests
  sleep(1);
}

export function handleSummary(data) {
  return {
    'performance-summary.json': JSON.stringify({
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
        performance_score: data.metrics.http_req_duration.values['p(95)'] < 200 ? 'EXCELLENT' : 
                          data.metrics.http_req_duration.values['p(95)'] < 500 ? 'GOOD' : 'NEEDS_IMPROVEMENT',
        recommendations: generateRecommendations(data)
      }
    }, null, 2),
  };
}

function generateRecommendations(data) {
  let recommendations = [];
  
  if (data.metrics.http_req_duration.values['p(95)'] > 500) {
    recommendations.push('Consider implementing caching for frequently accessed endpoints');
    recommendations.push('Optimize database queries for better response times');
  }
  
  if (data.metrics.errors.values.rate > 0.05) {
    recommendations.push('Investigate and fix API errors to improve reliability');
    recommendations.push('Add better error handling and retry mechanisms');
  }
  
  if (data.metrics.http_reqs.values.rate < 10) {
    recommendations.push('Consider implementing request batching for better throughput');
  }
  
  return recommendations;
}
