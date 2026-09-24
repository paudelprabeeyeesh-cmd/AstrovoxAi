
import { signInSchema, signUpSchema, chatMessageSchema } from '@/lib/validations'

describe('Property-Based Security Tests', () => {
  it('rejects all XSS payloads in email', () => {
    const xssPayloads = [
      '<script>alert(1)</script>',
      '<img src=x onerror=alert(1)>',
      'javascript:alert(1)',
      '<svg onload=alert(1)>',
    ]
    for (const payload of xssPayloads) {
      const result = signInSchema.safeParse({ email: payload, password: 'password123' })
      expect(result.success).toBe(false)
    }
  })

  it('rejects all SQL injection payloads in password', () => {
    const sqlPayloads = [
      "' OR '1'='1",
      "'; DROP TABLE users; --",
      "' UNION SELECT NULL--",
      "admin'--",
    ]
    for (const payload of sqlPayloads) {
      const result = signInSchema.safeParse({ email: 'test@example.com', password: payload })
      expect(result.success).toBe(false)
    }
  })

  it('validates all safe emails', () => {
    const safeEmails = [
      'user@example.com',
      'test.user@domain.co.uk',
      'admin+tag@test.org',
    ]
    for (const email of safeEmails) {
      const result = signInSchema.safeParse({ email, password: 'password123' })
      expect(result.success).toBe(true)
    }
  })
})
