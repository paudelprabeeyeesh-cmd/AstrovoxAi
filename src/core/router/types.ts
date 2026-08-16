export type ModelTask = 'chat' | 'embed' | 'completion' | 'moderation' | string;

export interface GenerateOptions {
  model: string;
  prompt?: string;
  messages?: Array<{ role: string; content: string }>;
  maxTokens?: number;
  temperature?: number;
  stream?: boolean;
  signal?: AbortSignal;
  [key: string]: any;
}

export interface GenerateResponse {
  id?: string;
  text?: string;
  finishReason?: string | null;
  usage?: {
    promptTokens?: number;
    completionTokens?: number;
    totalTokens?: number;
    costUSD?: number;
  };
  [key: string]: any;
}

export interface ModelProvider {
  name: string;
  supportsStreaming: boolean;

  // For streaming providers return an AsyncIterable<string> when stream=true
  generate(options: GenerateOptions): Promise<GenerateResponse> | AsyncIterable<string> | AsyncGenerator<string, void, unknown>;

  // Optional: graceful shutdown / cancel
  cancel?(id: string): Promise<void>;
}
