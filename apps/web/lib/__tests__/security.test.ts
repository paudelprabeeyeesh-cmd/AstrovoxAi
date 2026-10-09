
import { signInSchema, signUpSchema, chatMessageSchema } from '@/lib/validations'

describe('Security Tests', () => {
  describe('Input sanitization', () => {
    it('rejects XSS in sign in email', () => {
      const result = signInSchema.safeParse({ email: '<script>alert(1)</script>', password: 'password123' })
      expect(result.success).toBe(false)
    })

    it('rejects XSS in sign up name', () => {
      const result = signUpSchema.safeParse({
        name: '<img src=x onerror=alert(1)>',
        email: 'test@example.com',
        password: 'password123',
        confirmPassword: 'password123',
      })
      expect(result.success).toBe(false)
    })

    it('rejects SQL injection patterns in password', () => {
      const result = signInSchema.safeParse({ email: 'test@example.com', password: "' OR '1'='1" })
      expect(result.success).toBe(false)
    })

    it('rejects command injection in chat message', () => {
      const result = chatMessageSchema.safeParse({ content: '$(rm -rf /)' })
      expect(result.success).toBe(true)
      expect(result.data?.content).not.toContain('rm -rf')
    })

    it('rejects null bytes in email', () => {
      const result = signInSchema.safeParse({ email: 'test\x00@example.com', password: 'password123' })
      expect(result.success).toBe(false)
    })
  })

  describe('Authentication edge cases', () => {
    it('rejects empty password', () => {
      const result = signInSchema.safeParse({ email: 'test@example.com', password: '' })
      expect(result.success).toBe(false)
    })

    it('rejects extremely long password', () => {
      const result = signInSchema.safeParse({ email: 'test@example.com', password: 'a'.repeat(10001) })
      expect(result.success).toBe(false)
    })

    it('rejects mismatched passwords on signup', () => {
      const result = signUpSchema.safeParse({
        name: 'John',
        email: 'john@example.com',
        password: 'password123',
        confirmPassword: 'different',
      })
      expect(result.success).toBe(false)
    })
  })

  describe('Authorization edge cases', () => {
    it('chat message schema rejects empty content', () => {
      const result = chatMessageSchema.safeParse({ content: '' })
      expect(result.success).toBe(false)
    })

    it('chat message schema rejects content over limit', () => {
      const result = chatMessageSchema.safeParse({ content: 'a'.repeat(4001) })
      expect(result.success).toBe(false)
    })
  })
})
