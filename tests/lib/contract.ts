export interface ApiContractOptions {
  baseUrl: string
  headers?: Record<string, string>
}

export class ApiContractHelper {
  private baseUrl: string
  private headers: Record<string, string>

  constructor(options: ApiContractOptions) {
    this.baseUrl = options.baseUrl
    this.headers = { 'Content-Type': 'application/json', ...options.headers }
  }

  async get(path: string) {
    const res = await fetch(`${this.baseUrl}${path}`, { headers: this.headers })
    return res.json()
  }

  async post(path: string, body: unknown) {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify(body)
    })
    return res.json()
  }

  async put(path: string, body: unknown) {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'PUT',
      headers: this.headers,
      body: JSON.stringify(body)
    })
    return res.json()
  }

  async delete(path: string) {
    const res = await fetch(`${this.baseUrl}${path}`, { method: 'DELETE', headers: this.headers })
    return res.status
  }

  assertSchema(schema: Record<string, unknown>, data: unknown): void {
    expect(data).toBeDefined()
    for (const [key, type] of Object.entries(schema)) {
      expect(data).toHaveProperty(key)
      if (type === 'array') expect(Array.isArray((data as Record<string, unknown>)[key])).toBe(true)
      else if (type === 'object') expect(typeof (data as Record<string, unknown>)[key]).toBe('object')
      else expect(typeof (data as Record<string, unknown>)[key]).toBe(type)
    }
  }
}
