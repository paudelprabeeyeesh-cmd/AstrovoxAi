import type { ModelProvider, GenerateOptions, GenerateResponse } from '../types';

export const geminiProvider: ModelProvider = {
  name: 'gemini',
  supportsStreaming: false,

  async generate(_options: GenerateOptions): Promise<GenerateResponse> {
    throw new Error('Gemini provider not implemented yet.');
  }
};
