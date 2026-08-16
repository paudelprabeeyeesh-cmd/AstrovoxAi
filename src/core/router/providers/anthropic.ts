import type { ModelProvider, GenerateOptions, GenerateResponse } from '../types';

export const anthropicProvider: ModelProvider = {
  name: 'anthropic',
  supportsStreaming: false,

  async generate(_options: GenerateOptions): Promise<GenerateResponse> {
    throw new Error('Anthropic provider not implemented yet.');
  }
};
