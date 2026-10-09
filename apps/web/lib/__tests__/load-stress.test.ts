
describe('Load and Stress Tests', () => {
  it('validates schema under rapid iterations', () => {
    const { signInSchema } = require('@/lib/validations')
    for (let i = 0; i < 1000; i++) {
      const result = signInSchema.safeParse({ email: `user${i}@example.com`, password: 'password123' })
      expect(result.success).toBe(true)
    }
  })

  it('validates schema under stress with invalid data', () => {
    const { signInSchema } = require('@/lib/validations')
    for (let i = 0; i < 1000; i++) {
      const result = signInSchema.safeParse({ email: 'invalid', password: 'short' })
      expect(result.success).toBe(false)
    }
  })
})
