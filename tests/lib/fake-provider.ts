export type AIProviderOptions = {
  latencyMs?: number
  failRate?: number
  responses?: string[]
  stream?: boolean
  tokensPerResponse?: number
}

export class FakeAIProvider {
  private options: Required<AIProviderOptions>
  private callCount = 0

  constructor(options: AIProviderOptions = {}) {
    this.options = {
      latencyMs: options.latencyMs ?? 50,
      failRate: options.failRate ?? 0,
      responses: options.responses ?? ['Hello!', 'I am a test AI.', 'Mock response.'],
      stream: options.stream ?? false,
      tokensPerResponse: options.tokensPerResponse ?? 10
    }
  }

  async chat(prompt: string, _context?: unknown): Promise<string> {
    this.callCount++
    if (Math.random() < this.options.failRate) {
      throw new Error('Simulated AI provider failure')
    }
    if (this.options.latencyMs > 0) {
      await new Promise(r => setTimeout(r, this.options.latencyMs))
    }
    const response = this.options.responses[this.callCount % this.options.responses.length]
    if (this.options.stream) {
      return this.streamResponse(response)
    }
    return response
  }

  async *streamResponse(text: string): AsyncGenerator<string> {
    const tokens = text.split(' ')
    for (const token of tokens) {
      await new Promise(r => setTimeout(r, 20))
      yield token + ' '
    }
  }

  embed(text: string): number[] {
    return Array.from({ length: 384 }, () => Math.random())
  }

  reset() {
    this.callCount = 0
  }

  getCallCount() {
    return this.callCount
  }
}
