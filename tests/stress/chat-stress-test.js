import http from 'k6/http'
import { check, sleep } from 'k6'

export const options = {
  stages: [
    { duration: '10s', target: 200 },
    { duration: '30s', target: 500 },
    { duration: '1m', target: 1000 },
    { duration: '30s', target: 0 }
  ],
  thresholds: {
    http_req_duration: ['p(99)<2000'],
    http_req_failed: ['rate<0.05']
  }
}

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000'
const AUTH_TOKEN = __ENV.AUTH_TOKEN || ''

export function setup() {
  const loginRes = http.post(`${BASE_URL}/api/auth/login`, {
    email: 'stress-test@example.com',
    password: 'test-password'
  })
  check(loginRes, { 'login successful': (r) => r.status === 200 })
  return { token: loginRes.json('access_token') }
}

export default function (data) {
  const headers = { Authorization: `Bearer ${data.token}`, 'Content-Type': 'application/json' }

  const messages = ['Short', 'A' + 'B'.repeat(100), 'What is AI?', 'Tell me a story', 'Help with code']
  const randomMessage = messages[Math.floor(Math.random() * messages.length)]

  const chatRes = http.post(`${BASE_URL}/api/chat/message`, JSON.stringify({
    conversation_id: `stress-conv-${__VU}`,
    message: randomMessage,
    model: 'gpt-4'
  }), { headers })

  check(chatRes, {
    'status is 200': (r) => r.status === 200 || r.status === 429,
    'response time < 2000ms': (r) => r.timings.duration < 2000
  })

  if (chatRes.status === 429) {
    sleep(5)
  } else {
    sleep(Math.random() * 2)
  }
}

export function teardown(data) {}
