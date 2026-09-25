import http from 'k6/http'
import { check, sleep, group } from 'k6'

export const options = {
  scenarios: {
    smoke: {
      executor: 'constant-vus',
      vus: 1,
      duration: '10s',
      exec: 'smokeTest'
    },
    ramp: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 50 },
        { duration: '1m', target: 100 },
        { duration: '30s', target: 0 }
      ],
      exec: 'rampTest'
    },
    spike: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '10s', target: 500 },
        { duration: '30s', target: 0 }
      ],
      exec: 'spikeTest'
    }
  },
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
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

export function smokeTest(data) {
  const headers = { Authorization: `Bearer ${data.token}`, 'Content-Type': 'application/json' }
  group('smoke checks', () => {
    const health = http.get(`${BASE_URL}/health`, { headers })
    check(health, { 'health is 200': (r) => r.status === 200 })

    const chat = http.post(`${BASE_URL}/api/chat/message`, JSON.stringify({
      conversation_id: 'smoke-conv',
      message: 'Load smoke test',
      model: 'gpt-4'
    }), { headers })
    check(chat, { 'chat status is 200': (r) => r.status === 200 })
  })
  sleep(1)
}

export function rampTest(data) {
  const headers = { Authorization: `Bearer ${data.token}`, 'Content-Type': 'application/json' }
  const messages = ['Short', 'A' + 'B'.repeat(100), 'What is AI?', 'Tell me a story', 'Help with code']
  const randomMessage = messages[Math.floor(Math.random() * messages.length)]

  const chatRes = http.post(`${BASE_URL}/api/chat/message`, JSON.stringify({
    conversation_id: `ramp-conv-${__VU}`,
    message: randomMessage,
    model: 'gpt-4'
  }), { headers })

  check(chatRes, {
    'status is 200': (r) => r.status === 200 || r.status === 429,
    'response time < 500ms': (r) => r.timings.duration < 500
  })

  if (chatRes.status === 429) sleep(5) else sleep(Math.random() * 2)
}

export function spikeTest(data) {
  const headers = { Authorization: `Bearer ${data.token}`, 'Content-Type': 'application/json' }
  const chatRes = http.post(`${BASE_URL}/api/chat/message`, JSON.stringify({
    conversation_id: `spike-conv-${__VU}`,
    message: 'Spike test message',
    model: 'gpt-4'
  }), { headers })

  check(chatRes, {
    'status is 200 or 429': (r) => r.status === 200 || r.status === 429,
    'response time < 2000ms': (r) => r.timings.duration < 2000
  })

  if (chatRes.status === 429) sleep(5) else sleep(Math.random())
}

export function teardown(data) {}
