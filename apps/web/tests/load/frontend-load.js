import http from 'k6/http'
import { check, sleep } from 'k6'

export const options = {
  stages: [
    { duration: '30s', target: 50 },
    { duration: '1m', target: 50 },
    { duration: '10s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
}

export default function () {
  const endpoints = [
    'http://localhost:3000/',
    'http://localhost:3000/api/health',
    'http://localhost:3000/api/usage-stats',
  ]
  for (const url of endpoints) {
    const res = http.get(url)
    check(res, {
      [`${url} status is 200 or 401/403`]: (r) => [200, 401, 403].includes(r.status),
      [`${url} latency < 500ms`]: (r) => r.timings.duration < 500,
    })
  }
  sleep(1)
}
