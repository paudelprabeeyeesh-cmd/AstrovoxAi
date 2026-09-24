import { signInSchema, signUpSchema, forgotPasswordSchema, resetPasswordSchema, chatMessageSchema, conversationSchema } from '@/lib/validations'

describe('Validation Schemas', () => {
  describe('signInSchema', () => {
    it('validates correct sign in data', () => {
      const result = signInSchema.safeParse({ email: 'test@example.com', password: 'password123' })
      expect(result.success).toBe(true)
    })

    it('rejects invalid email', () => {
      const result = signInSchema.safeParse({ email: 'invalid-email', password: 'password123' })
      expect(result.success).toBe(false)
      if (!result.success) {
        expect(result.error.issues[0].message).toBe('Invalid email address')
      }
    })

    it('rejects short password', () => {
      const result = signInSchema.safeParse({ email: 'test@example.com', password: 'short' })
      expect(result.success).toBe(false)
      if (!result.success) {
        expect(result.error.issues[0].message).toBe('Password must be at least 8 characters')
      }
    })
  })

  describe('signUpSchema', () => {
    it('validates correct sign up data', () => {
      const result = signUpSchema.safeParse({
        name: 'John Doe',
        email: 'john@example.com',
        password: 'password123',
        confirmPassword: 'password123',
      })
      expect(result.success).toBe(true)
    })

    it('rejects mismatched passwords', () => {
      const result = signUpSchema.safeParse({
        name: 'John Doe',
        email: 'john@example.com',
        password: 'password123',
        confirmPassword: 'different',
      })
      expect(result.success).toBe(false)
      if (!result.success) {
        expect(result.error.issues[0].message).toBe("Passwords don't match")
      }
    })
  })

  describe('forgotPasswordSchema', () => {
    it('validates correct email', () => {
      const result = forgotPasswordSchema.safeParse({ email: 'test@example.com' })
      expect(result.success).toBe(true)
    })

    it('rejects invalid email', () => {
      const result = forgotPasswordSchema.safeParse({ email: 'invalid' })
      expect(result.success).toBe(false)
    })
  })

  describe('resetPasswordSchema', () => {
    it('validates correct reset data', () => {
      const result = resetPasswordSchema.safeParse({
        password: 'newpassword123',
        confirmPassword: 'newpassword123',
      })
      expect(result.success).toBe(true)
    })

    it('rejects mismatched passwords', () => {
      const result = resetPasswordSchema.safeParse({
        password: 'newpassword123',
        confirmPassword: 'different',
      })
      expect(result.success).toBe(false)
    })
  })

  describe('chatMessageSchema', () => {
    it('validates correct message', () => {
      const result = chatMessageSchema.safeParse({ content: 'Hello!' })
      expect(result.success).toBe(true)
    })

    it('rejects empty message', () => {
      const result = chatMessageSchema.safeParse({ content: '' })
      expect(result.success).toBe(false)
    })

    it('rejects too long message', () => {
      const result = chatMessageSchema.safeParse({ content: 'a'.repeat(4001) })
      expect(result.success).toBe(false)
    })
  })

  describe('conversationSchema', () => {
    it('validates correct conversation', () => {
      const result = conversationSchema.safeParse({ title: 'New Chat' })
      expect(result.success).toBe(true)
    })

    it('rejects empty title', () => {
      const result = conversationSchema.safeParse({ title: '' })
      expect(result.success).toBe(false)
    })
  })
})
