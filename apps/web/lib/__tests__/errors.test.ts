import { ApiError, ValidationError, AuthenticationError, AuthorizationError, NotFoundError, ServerError, getErrorMessage, isApiError } from '@/lib/errors'

describe('Error Classes', () => {
  describe('ApiError', () => {
    it('creates error with message and status', () => {
      const error = new ApiError('Test error', 400)
      expect(error.message).toBe('Test error')
      expect(error.statusCode).toBe(400)
      expect(error.name).toBe('ApiError')
    })

    it('creates error with details', () => {
      const details = { field: 'email' }
      const error = new ApiError('Validation failed', 400, details)
      expect(error.details).toBe(details)
    })
  })

  describe('ValidationError', () => {
    it('creates with default 400 status', () => {
      const error = new ValidationError('Invalid input')
      expect(error.statusCode).toBe(400)
      expect(error.name).toBe('ValidationError')
    })
  })

  describe('AuthenticationError', () => {
    it('creates with default 401 status', () => {
      const error = new AuthenticationError()
      expect(error.statusCode).toBe(401)
      expect(error.name).toBe('AuthenticationError')
    })
  })

  describe('AuthorizationError', () => {
    it('creates with default 403 status', () => {
      const error = new AuthorizationError()
      expect(error.statusCode).toBe(403)
      expect(error.name).toBe('AuthorizationError')
    })
  })

  describe('NotFoundError', () => {
    it('creates with default 404 status', () => {
      const error = new NotFoundError()
      expect(error.statusCode).toBe(404)
      expect(error.name).toBe('NotFoundError')
    })
  })

  describe('ServerError', () => {
    it('creates with default 500 status', () => {
      const error = new ServerError()
      expect(error.statusCode).toBe(500)
      expect(error.name).toBe('ServerError')
    })
  })
})

describe('getErrorMessage', () => {
  it('returns message from ApiError', () => {
    const error = new ApiError('API error', 500)
    expect(getErrorMessage(error)).toBe('API error')
  })

  it('returns message from Error', () => {
    const error = new Error('Generic error')
    expect(getErrorMessage(error)).toBe('Generic error')
  })

  it('returns string error', () => {
    expect(getErrorMessage('String error')).toBe('String error')
  })

  it('returns default message for unknown error', () => {
    expect(getErrorMessage(null)).toBe('An unexpected error occurred')
    expect(getErrorMessage(undefined)).toBe('An unexpected error occurred')
    expect(getErrorMessage({})).toBe('An unexpected error occurred')
  })
})

describe('isApiError', () => {
  it('returns true for ApiError instances', () => {
    const error = new ApiError('test')
    expect(isApiError(error)).toBe(true)
  })

  it('returns false for non-ApiError', () => {
    expect(isApiError(new Error('test'))).toBe(false)
    expect(isApiError('string')).toBe(false)
    expect(isApiError(null)).toBe(false)
  })
})
