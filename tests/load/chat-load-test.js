import http from 'k6/http'
import { check, sleep } from 'k6'

export const options = {
  stages: [
    { duration: '30s', target: 50 },
    { duration: '1m', target: 100 },
    { duration: '30s', target: 0 }
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01']
  }
}

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000'
const AUTH_TOKEN = __ENV.AUTH_TOKEN || ''

export function setup() {
  const loginRes = http.post(`${BASE_URL}/api/auth/login`, {
    email: 'load-test@example.com',
    password: 'test-password'
  })
  check(loginRes, { 'login successful': (r) => r.status === 200 })
  return { token: loginRes.json('access_token') }
}

export default function (data) {
  const headers = { Authorization: `Bearer ${data.token}`, 'Content-Type': 'application/json' }

  const chatRes = http.post(`${BASE_URL}/api/chat/message`, JSON.stringify({
    conversation_id: 'load-test-conv',
    message: 'Load test message',
    model: 'gpt-4'
  }), { headers })

  check(chatRes, {
    'chat status is 200': (r) => r.status === 200,
    'chat response time < 500ms': (r) => r.timings.duration < 500
  })

  sleep(1)
}

export function teardown(data) {}
