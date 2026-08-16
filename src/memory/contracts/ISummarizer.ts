export interface ISummarizer {
  /** Summarize an array of texts into a single summary string. */
  summarize(texts: string[], options?: { model?: string; maxTokens?: number; context?: Record<string, any>; signal?: AbortSignal }): Promise<string>;
  init?(): Promise<void>;
  shutdown?(): Promise<void>;
}
