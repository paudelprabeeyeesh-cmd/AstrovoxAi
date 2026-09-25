export interface TestEnvOptions {
  apiKey?: string
  baseUrl?: string
  databaseUrl?: string
  mockMode?: boolean
  seed?: number
}

export class TestEnvironmentBootstrap {
  private env: Record<string, string> = {}
  private initialized = false

  async setup(options: TestEnvOptions = {}): Promise<void> {
    this.env = {
      VITE_API_URL: options.baseUrl ?? 'http://localhost:8000',
      VITE_SUPABASE_URL: 'http://localhost:54321',
      VITE_SUPABASE_ANON_KEY: 'test-anon-key',
      VITE_APP_ENV: options.mockMode ? 'mock' : 'test',
      VITE_SEED: String(options.seed ?? 12345),
      ...Object.fromEntries(Object.entries(options).filter(([, v]) => typeof v === 'string'))
    }
    for (const [key, value] of Object.entries(this.env)) {
      if (!process.env[key]) process.env[key] = value
    }
    this.initialized = true
  }

  isInitialized(): boolean {
    return this.initialized
  }

  get(key: string): string | undefined {
    return this.env[key] ?? process.env[key]
  }

  reset() {
    this.env = {}
    this.initialized = false
  }
}

export const testEnv = new TestEnvironmentBootstrap()
