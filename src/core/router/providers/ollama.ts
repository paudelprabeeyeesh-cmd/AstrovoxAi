import type { ModelProvider, GenerateOptions, GenerateResponse } from '../types';

export const ollamaProvider: ModelProvider = {
  name: 'ollama',
  supportsStreaming: false,

  async generate(_options: GenerateOptions): Promise<GenerateResponse> {
    throw new Error('Ollama provider not implemented yet. Add HTTP/SDK calls here.');
  }
};
