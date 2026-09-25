import http from 'k6/http'
import { check, sleep, group } from 'k6'

export const options = {
  scenarios: {
    sustained: {
      executor: 'constant-vus',
      vus: 100,
      duration: '2m',
      exec: 'sustainedLoad'
    },
    stress: {
      executor: 'ramping-vus',
      startVUs: 10,
      stages: [
        { duration: '30s', target: 200 },
        { duration: '1m', target: 500 },
        { duration: '30s', target: 1000 },
        { duration: '30s', target: 0 }
      ],
      exec: 'stressRamp'
    }
  },
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

export function sustainedLoad(data) {
  const headers = { Authorization: `Bearer ${data.token}`, 'Content-Type': 'application/json' }
  group('sustained load', () => {
    const chatRes = http.post(`${BASE_URL}/api/chat/message`, JSON.stringify({
      conversation_id: `sustained-${__VU}`,
      message: 'Sustained load test',
      model: 'gpt-4'
    }), { headers })

    check(chatRes, {
      'status is 200 or 429': (r) => r.status === 200 || r.status === 429
    })

    if (chatRes.status === 429) sleep(5)
  })
  sleep(1)
}

export function stressRamp(data) {
  const headers = { Authorization: `Bearer ${data.token}`, 'Content-Type': 'application/json' }
  const messages = ['Short', 'A' + 'B'.repeat(100), 'What is AI?', 'Tell me a story', 'Help with code']
  const randomMessage = messages[Math.floor(Math.random() * messages.length)]

  group('stress ramp', () => {
    const chatRes = http.post(`${BASE_URL}/api/chat/message`, JSON.stringify({
      conversation_id: `stress-${__VU}`,
      message: randomMessage,
      model: 'gpt-4'
    }), { headers })

    check(chatRes, {
      'status is 200 or 429': (r) => r.status === 200 || r.status === 429,
      'response time < 2000ms': (r) => r.timings.duration < 2000
    })

    if (chatRes.status === 429) sleep(5) else sleep(Math.random() * 2)
  })
}

export function teardown(data) {}