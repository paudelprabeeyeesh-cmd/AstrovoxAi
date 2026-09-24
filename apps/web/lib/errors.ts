export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public details?: Record<string, unknown>,
  ) {
    super(message)
    this.name = "ApiError"
  }
}

export class ValidationError extends ApiError {
  constructor(message: string, details?: Record<string, unknown>) {
    super(message, 400, details)
    this.name = "ValidationError"
  }
}

export class AuthenticationError extends ApiError {
  constructor(message: string = "Authentication required") {
    super(message, 401)
    this.name = "AuthenticationError"
  }
}

export class AuthorizationError extends ApiError {
  constructor(message: string = "Insufficient permissions") {
    super(message, 403)
    this.name = "AuthorizationError"
  }
}

export class NotFoundError extends ApiError {
  constructor(message: string = "Resource not found") {
    super(message, 404)
    this.name = "NotFoundError"
  }
}

export class ServerError extends ApiError {
  constructor(message: string = "Internal server error") {
    super(message, 500)
    this.name = "ServerError"
  }
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message
  }
  if (error instanceof Error) {
    return error.message
  }
  if (typeof error === "string") {
    return error
  }
  return "An unexpected error occurred"
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}
